// Unit tests for src/services/telemetry.ts with Node's built-in runner (no extra dependencies).
import assert from 'node:assert/strict';
import { afterEach, beforeEach, mock, test } from 'node:test';

type Track = typeof import('../src/services/telemetry.ts').track;
type Batch = { events: Array<Record<string, unknown> & { eventId: string; properties: Record<string, unknown> }> };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const props = { app: 'backoffice', route_template: '/', viewport_class: 'desktop' } as const;

let fetchCalls: Batch[];
let fetchStatus: Array<number | 'network'>;
let beacons: Blob[];
let beaconAccepts: boolean;
let storage: Map<string, string>;
let windowTarget: EventTarget;
let documentTarget: EventTarget & { visibilityState: string };
let loads = 0;

function define(name: string, value: unknown) {
  Object.defineProperty(globalThis, name, { value, configurable: true, writable: true });
}

async function load(): Promise<Track> {
  // A fresh module instance per test keeps queue/timer state isolated.
  return (await import(`../src/services/telemetry.ts?test=${++loads}`)).track;
}

const settle = () => new Promise((resolve) => setImmediate(resolve));
const ids = (batch: Batch) => batch.events.map((e) => e.eventId);

beforeEach(() => {
  fetchCalls = [];
  fetchStatus = [];
  beacons = [];
  beaconAccepts = true;
  storage = new Map();
  windowTarget = new EventTarget();
  documentTarget = Object.assign(new EventTarget(), { visibilityState: 'visible' });
  mock.timers.enable({ apis: ['setTimeout', 'setInterval', 'Date'], now: Date.parse('2026-10-26T09:00:00.000Z') });
  define('window', windowTarget);
  define('document', documentTarget);
  define('navigator', { sendBeacon: (_url: string, body: Blob) => (beacons.push(body), beaconAccepts) });
  define('sessionStorage', { getItem: (k: string) => storage.get(k) ?? null, setItem: (k: string, v: string) => storage.set(k, v) });
  define('fetch', async (_url: string, init: { body: string }) => {
    fetchCalls.push(JSON.parse(init.body));
    const status = fetchStatus.shift() ?? 200;
    if (status === 'network') throw new TypeError('Failed to fetch');
    return { status };
  });
});

afterEach(() => mock.timers.reset());

test('builds the contract envelope and flushes at 20 events', async () => {
  const track = await load();
  for (let i = 0; i < 19; i++) track('page_viewed', props);
  assert.equal(fetchCalls.length, 0);
  track('page_viewed', props, { requestId: '3d2c1b0a-9f8e-4d7c-a6b5-4c3d2e1f0a9b' });
  assert.equal(fetchCalls.length, 1);
  const { events } = fetchCalls[0];
  assert.equal(events.length, 20);
  assert.equal(new Set(ids(fetchCalls[0])).size, 20);
  for (const event of events) {
    assert.deepEqual(Object.keys(event).sort(), ['eventId', 'event_type', 'properties', 'requestId', 'schemaVersion', 'sessionId', 'timestamp', 'userId']);
    assert.match(event.eventId, UUID);
    assert.match(String(event.sessionId), UUID);
    assert.equal(event.sessionId, events[0].sessionId);
    assert.equal(event.timestamp, '2026-10-26T09:00:00.000Z');
    assert.equal(event.userId, null);
    assert.equal(event.schemaVersion, '1.0.0');
    assert.deepEqual(event.properties, props);
  }
  assert.equal(events[0].requestId, null);
  assert.equal(events[19].requestId, '3d2c1b0a-9f8e-4d7c-a6b5-4c3d2e1f0a9b');
});

test('flushes every 30 seconds', async () => {
  const track = await load();
  track('page_viewed', props);
  mock.timers.tick(29_999);
  assert.equal(fetchCalls.length, 0);
  mock.timers.tick(1);
  assert.equal(fetchCalls.length, 1);
  mock.timers.tick(30_000);
  assert.equal(fetchCalls.length, 1, 'empty queue sends nothing');
});

test('retries with exponential backoff, at most 3 times, keeping eventIds', async () => {
  const track = await load();
  fetchStatus = ['network', 503, 'network', 'network'];
  track('page_viewed', props);
  mock.timers.tick(30_000);
  await settle();
  for (const delay of [1_000, 2_000, 4_000]) {
    mock.timers.tick(delay - 1);
    await settle();
    const before = fetchCalls.length;
    mock.timers.tick(1);
    await settle();
    assert.equal(fetchCalls.length, before + 1, `retry after ${delay} ms`);
  }
  mock.timers.tick(60_000);
  await settle();
  assert.equal(fetchCalls.length, 4, '1 attempt + 3 retries');
  assert.ok(fetchCalls.every((batch) => ids(batch)[0] === ids(fetchCalls[0])[0]));
});

test('stops after success and never retries contract errors', async () => {
  const track = await load();
  fetchStatus = [500, 200];
  track('page_viewed', props);
  mock.timers.tick(30_000);
  await settle();
  mock.timers.tick(1_000);
  await settle();
  mock.timers.tick(60_000);
  await settle();
  assert.equal(fetchCalls.length, 2);
  assert.deepEqual(ids(fetchCalls[1]), ids(fetchCalls[0]));

  fetchCalls = [];
  fetchStatus = [422];
  track('page_viewed', props);
  mock.timers.tick(30_000);
  await settle();
  mock.timers.tick(60_000);
  await settle();
  assert.equal(fetchCalls.length, 1);
});

test('hands queued and retry-pending events to sendBeacon once on hide', async () => {
  const track = await load();
  fetchStatus = ['network'];
  track('page_viewed', props);
  mock.timers.tick(30_000);
  await settle();
  const failedId = ids(fetchCalls[0])[0];
  track('page_viewed', props);

  documentTarget.visibilityState = 'hidden';
  documentTarget.dispatchEvent(new Event('visibilitychange'));
  assert.equal(beacons.length, 1);
  assert.equal(beacons[0].type, 'application/json');
  const sent: Batch = JSON.parse(await beacons[0].text());
  assert.equal(sent.events.length, 2);
  assert.equal(ids(sent)[0], failedId, 'retry batch keeps its eventId');

  windowTarget.dispatchEvent(new Event('pagehide'));
  mock.timers.tick(120_000);
  await settle();
  assert.equal(beacons.length, 1, 'nothing left to resend');
  assert.equal(fetchCalls.length, 1, 'cancelled retry is not sent again');
});

test('falls back to fetch when sendBeacon refuses the payload', async () => {
  const track = await load();
  beaconAccepts = false;
  track('page_viewed', props);
  windowTarget.dispatchEvent(new Event('pagehide'));
  assert.equal(beacons.length, 1);
  assert.equal(fetchCalls.length, 1);
});

test('rotates the session after 30 minutes of inactivity', async () => {
  const track = await load();
  track('page_viewed', props);
  mock.timers.tick(29 * 60_000);
  track('page_viewed', props);
  mock.timers.tick(31 * 60_000);
  track('page_viewed', props);
  mock.timers.tick(30_000);
  const sessions = fetchCalls.flatMap((batch) => batch.events.map((e) => e.sessionId));
  assert.equal(sessions[0], sessions[1]);
  assert.notEqual(sessions[1], sessions[2]);
});
