// Unit tests for src/services/reporting.ts (business performance dashboard).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { type KpiRow, cellFor, countriesOf, formatUpdated, formatValue, formatWeek, kpiTable, mondayOf, weekRange } from '../src/services/reporting.ts';

const row = (overrides: Partial<KpiRow>): KpiRow => ({
  kpi: 'shipments_total',
  period_start: '2026-11-02',
  period_end: '2026-11-09',
  country: 'US',
  carrier: 'all',
  currency: 'n/a',
  numerator: 55,
  denominator: null,
  value: 55,
  unit: 'shipments',
  status: 'ok',
  days_covered: 7,
  revision: 1,
  computed_at: '2026-11-09T04:01:00Z',
  ...overrides,
});

test('weeks start on Monday (UTC) and the range ends after the current week', () => {
  assert.equal(mondayOf(new Date('2026-11-13T22:30:00Z')).toISOString().slice(0, 10), '2026-11-09');
  assert.equal(mondayOf(new Date('2026-11-09T00:00:00Z')).toISOString().slice(0, 10), '2026-11-09');
  assert.equal(mondayOf(new Date('2026-11-15T23:59:00Z')).toISOString().slice(0, 10), '2026-11-09');
  assert.deepEqual(weekRange(new Date('2026-11-13T10:00:00Z'), 8), {
    start: '2026-09-21',
    end: '2026-11-16',
    lastCompleteWeek: '2026-11-02',
  });
});

test('week labels show the last day, not the exclusive end', () => {
  assert.equal(formatWeek('2026-11-02', '2026-11-09'), '2 – 8 Nov 2026');
  assert.equal(formatWeek('2026-09-28', '2026-10-05'), '28 Sep – 4 Oct 2026');
  assert.equal(formatWeek('2025-12-29', '2026-01-05'), '29 Dec 2025 – 4 Jan 2026');
  assert.equal(formatUpdated('2026-11-13T04:02:31.5Z'), '13 Nov 2026, 04:02 UTC');
});

test('values are formatted for a business reader', () => {
  assert.equal(formatValue(row({ value: 1234 })).text, '1,234');
  assert.equal(formatValue(row({ kpi: 'on_time_delivery_rate', value: 0.775862, unit: 'ratio' })).text, '77.6 %');
  assert.equal(formatValue(row({ kpi: 'shipping_cost_total', value: 1239.38, currency: 'USD' })).text, '$1,239.38');
  assert.equal(formatValue(row({ kpi: 'shipping_cost_total', value: 906.1, currency: 'EUR' })).text, '€906.10');
  assert.equal(formatValue(row({ kpi: 'shipping_cost_per_kg', value: 3.521466, currency: 'USD' })).text, '$3.52 / kg');
  assert.equal(formatValue(row({ kpi: 'customer_satisfaction_avg', value: 4.0667 })).text, '4.1 / 5');
});

test('missing figures say why instead of showing a zero', () => {
  assert.equal(formatValue(row({ status: 'not_instrumented', value: null })).text, 'Not tracked yet');
  assert.equal(formatValue(row({ status: 'capture_gap', value: null })).text, 'Incomplete data');
  assert.equal(formatValue(row({ kpi: 'return_rate', status: 'no_activity', value: null })).text, 'No activity');
  assert.equal(formatValue(row({ status: 'no_activity', value: 0 })).text, '0');
});

test('costs in two currencies stay apart and revised figures are flagged', () => {
  const cell = cellFor([
    row({ kpi: 'shipping_cost_total', value: 10, currency: 'USD' }),
    row({ kpi: 'shipping_cost_total', value: 3, currency: 'EUR', revision: 2 }),
  ]);
  assert.equal(cell.text, '$10.00 · €3.00');
  assert.equal(cell.revised, true);
  assert.equal(cellFor([row({}), row({ status: 'capture_gap', value: null })]).status, 'capture_gap');
});

test('a KPI table has the newest week first and one column per country', () => {
  const rows = [
    row({ country: 'ES', value: 40 }),
    row({ country: 'unknown', value: 1 }),
    row({ period_start: '2026-11-09', period_end: '2026-11-16', days_covered: 4, value: 20 }),
    row({ value: 55 }),
    row({ kpi: 'return_rate', value: 0.1 }),
    row({ country: 'FR', value: 2 }),
  ];
  assert.deepEqual(countriesOf(rows), ['US', 'ES', 'FR', 'unknown']);
  const table = kpiTable(rows, 'shipments_total');
  assert.deepEqual(table.countries, ['US', 'ES', 'FR', 'unknown']);
  assert.deepEqual(table.weeks.map((week) => [week.label, week.daysCovered]), [['9 – 15 Nov 2026', 4], ['2 – 8 Nov 2026', 7]]);
  assert.deepEqual(Object.keys(table.weeks[0].cells), ['US']);
  assert.equal(table.weeks[1].cells.ES.text, '40');
});
