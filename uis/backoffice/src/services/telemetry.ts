// Client-side capture for the TrackFlow telemetry contract
// (docs/telemetry/event-schemas.json). Public API: `track` only.

type RouteTemplate = '/' | '<unmatched>';
type App = 'backoffice';
type ViewportClass = 'mobile' | 'tablet' | 'desktop';

// Allowlists copied from the contract for the events this app can emit.
export type EventProperties = {
  page_viewed: {
    app: App;
    route_template: RouteTemplate;
    viewport_class: ViewportClass;
    referrer_type?: 'direct' | 'internal' | 'external' | 'unknown';
    locale?: string;
  };
  frontend_error_occurred: {
    app: App;
    route_template: RouteTemplate;
    error_kind: 'js_exception' | 'unhandled_rejection' | 'fetch_failed';
    error_fingerprint: string;
    http_status?: number;
  };
  web_vitals_measured: {
    app: App;
    route_template: RouteTemplate;
    metric: 'LCP' | 'CLS' | 'INP' | 'TTFB' | 'FCP';
    value: number;
    rating: 'good' | 'needs_improvement' | 'poor';
    viewport_class?: ViewportClass;
  };
};
export type EventType = keyof EventProperties;

type Envelope = {
  eventId: string;
  timestamp: string;
  sessionId: string | null;
  userId: null; // No Auth yet.
  event_type: EventType;
  schemaVersion: string;
  requestId: string | null;
  properties: EventProperties[EventType];
};

const ENDPOINT = process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT || '/api/telemetry/events';
const SCHEMA_VERSION = '1.0.0';
const BATCH_SIZE = 20;
const FLUSH_INTERVAL_MS = 30_000;
const MAX_RETRIES = 3;
const BASE_BACKOFF_MS = 1_000;
const SESSION_KEY = 'trackflow.telemetry.session';
const SESSION_IDLE_MS = 30 * 60_000;

let queue: Envelope[] = [];
const waitingRetry = new Map<ReturnType<typeof setTimeout>, Envelope[]>();
let started = false;
let memorySession: { id: string; lastSeen: number } | null = null;

function uuid(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  // randomUUID needs a secure context; getRandomValues does not.
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

// Random per-tab session, rotated after 30 minutes of inactivity.
function sessionId(): string {
  const now = Date.now();
  let session = memorySession;
  try {
    session = JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? 'null');
  } catch {
    // Storage unavailable: keep the in-memory session.
  }
  if (!session || now - session.lastSeen > SESSION_IDLE_MS) session = { id: uuid(), lastSeen: now };
  session.lastSeen = now;
  memorySession = session;
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Ignore: in-memory session already updated.
  }
  return session.id;
}

function send(batch: Envelope[], attempt: number): void {
  fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ events: batch }),
    keepalive: true,
  })
    .then((response) => {
      // 4xx means the batch breaks the contract: retrying cannot fix it.
      if (response.status >= 500 || response.status === 429) retry(batch, attempt);
    })
    .catch(() => retry(batch, attempt));
}

function retry(batch: Envelope[], attempt: number): void {
  if (attempt >= MAX_RETRIES) return;
  const timer = setTimeout(() => {
    waitingRetry.delete(timer);
    send(batch, attempt + 1);
  }, BASE_BACKOFF_MS * 2 ** attempt);
  waitingRetry.set(timer, batch);
}

function flush(): void {
  while (queue.length) send(queue.splice(0, BATCH_SIZE), 0);
}

// On hide/close, hand everything still local (queued or waiting for a retry) to sendBeacon.
function flushOnExit(): void {
  const pending = [...waitingRetry.values()].flat().concat(queue);
  waitingRetry.forEach((_, timer) => clearTimeout(timer));
  waitingRetry.clear();
  queue = [];
  for (let i = 0; i < pending.length; i += BATCH_SIZE) {
    const batch = pending.slice(i, i + BATCH_SIZE);
    const body = new Blob([JSON.stringify({ events: batch })], { type: 'application/json' });
    if (!navigator.sendBeacon?.(ENDPOINT, body)) send(batch, MAX_RETRIES);
  }
}

function start(): void {
  started = true;
  setInterval(flush, FLUSH_INTERVAL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushOnExit();
  });
  window.addEventListener('pagehide', flushOnExit);
}

/** Queue a contract event. Never throws and never blocks the UI. */
export function track<T extends EventType>(
  eventType: T,
  properties: EventProperties[T],
  context: { requestId?: string } = {},
): void {
  if (typeof window === 'undefined') return;
  try {
    if (!started) start();
    queue.push({
      eventId: uuid(),
      timestamp: new Date().toISOString(),
      sessionId: sessionId(),
      userId: null,
      event_type: eventType,
      schemaVersion: SCHEMA_VERSION,
      requestId: context.requestId ?? null,
      properties,
    });
    if (queue.length >= BATCH_SIZE) flush();
  } catch {
    // Telemetry must never break the page.
  }
}
