// Business performance dashboard: KPI catalogue, weekly periods and formatting
// for GET /reporting/kpis (services/reporting). Pure functions, no React, so
// they can be unit tested with node:test.

export type KpiName =
  | 'shipments_total'
  | 'on_time_delivery_rate'
  | 'shipping_cost_total'
  | 'shipping_cost_per_kg'
  | 'return_rate'
  | 'customer_satisfaction_avg';
export type KpiStatus = 'ok' | 'no_activity' | 'capture_gap' | 'not_instrumented';

export type KpiRow = {
  kpi: KpiName;
  period_start: string;
  period_end: string; // exclusive
  country: string;
  carrier: string;
  currency: 'USD' | 'EUR' | 'n/a';
  numerator: number;
  denominator: number | null;
  value: number | null;
  unit: string;
  status: KpiStatus;
  days_covered: number;
  revision: number;
  computed_at: string;
};
export type KpiResponse = { start_date: string; end_date: string; granularity: 'day' | 'week'; country: string; rows: KpiRow[] };
export type PipelineStatus = {
  latest_computed_at: string | null;
  data_freshness_hours: number | null;
  last_run: { status: string; finished_at: string | null } | null;
};

type Kind = 'count' | 'ratio' | 'money' | 'money_per_kg' | 'score';

// Names follow the executive KPIs in CONTEXT.md (Dirección Ejecutiva) until
// the company BRIEFING exists; see data/pipelines/PIPELINE_DESIGN.md.
export const KPIS: ReadonlyArray<{ kpi: KpiName; label: string; question: string; kind: Kind }> = [
  { kpi: 'shipments_total', label: 'Shipment volume', question: 'How many shipments did we send?', kind: 'count' },
  { kpi: 'on_time_delivery_rate', label: 'On-time delivery rate', question: 'What share of deliveries arrived on time?', kind: 'ratio' },
  {
    kpi: 'shipping_cost_total',
    label: 'Operating cost (shipping)',
    question: 'How much did carriers charge us? Shipping only, in each country’s currency.',
    kind: 'money',
  },
  { kpi: 'shipping_cost_per_kg', label: 'Shipping cost per kg', question: 'How much does each kilogram cost to ship?', kind: 'money_per_kg' },
  { kpi: 'return_rate', label: 'Return rate', question: 'Returns requested for every delivery in the same week.', kind: 'ratio' },
  {
    kpi: 'customer_satisfaction_avg',
    label: 'Customer satisfaction',
    question: 'Average survey score, from 1 (very unhappy) to 5 (very happy).',
    kind: 'score',
  },
];

const COUNTRY_NAMES: Record<string, string> = { US: 'United States', ES: 'Spain', unknown: 'Country not reported' };
const COUNTRY_ORDER = ['US', 'ES'];
const DAY_MS = 86_400_000;

export const countryName = (code: string) => COUNTRY_NAMES[code] ?? code;

const isoDay = (date: Date) => date.toISOString().slice(0, 10);
const parseDay = (iso: string) => new Date(`${iso}T00:00:00Z`);

/** Monday (UTC) of the week that contains `date`. */
export function mondayOf(date: Date): Date {
  const day = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  return new Date(day.getTime() - ((day.getUTCDay() + 6) % 7) * DAY_MS);
}

/** The last `weeks` ISO weeks up to and including the current one: [start, end) for the API. */
export function weekRange(today: Date, weeks: number): { start: string; end: string; lastCompleteWeek: string } {
  const monday = mondayOf(today);
  return {
    start: isoDay(new Date(monday.getTime() - (weeks - 1) * 7 * DAY_MS)),
    end: isoDay(new Date(monday.getTime() + 7 * DAY_MS)),
    lastCompleteWeek: isoDay(new Date(monday.getTime() - 7 * DAY_MS)),
  };
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2 – 8 Nov 2026", "28 Sep – 4 Oct 2026" or "29 Dec 2025 – 4 Jan 2026" (end is exclusive). */
export function formatWeek(periodStart: string, periodEnd: string): string {
  const first = parseDay(periodStart);
  const last = new Date(parseDay(periodEnd).getTime() - DAY_MS);
  const [d1, m1, y1] = [first.getUTCDate(), MONTHS[first.getUTCMonth()], first.getUTCFullYear()];
  const [d2, m2, y2] = [last.getUTCDate(), MONTHS[last.getUTCMonth()], last.getUTCFullYear()];
  if (y1 !== y2) return `${d1} ${m1} ${y1} – ${d2} ${m2} ${y2}`;
  if (m1 !== m2) return `${d1} ${m1} – ${d2} ${m2} ${y2}`;
  return `${d1} – ${d2} ${m2} ${y2}`;
}

/** "13 Nov 2026, 04:02 UTC". */
export function formatUpdated(iso: string): string {
  const date = new Date(iso);
  const time = date.toISOString().slice(11, 16);
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}, ${time} UTC`;
}

const number = (value: number, digits: number) =>
  value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const money = (value: number, currency: string) =>
  currency === 'n/a' ? number(value, 2) : value.toLocaleString('en-US', { style: 'currency', currency });

const SEVERITY: Record<KpiStatus, number> = { no_activity: 0, ok: 1, capture_gap: 2, not_instrumented: 3 };

export type Cell = { text: string; note?: string; status: KpiStatus; revised: boolean };

const NOT_MEASURED: Partial<Record<KpiStatus, Omit<Cell, 'status' | 'revised'>>> = {
  not_instrumented: { text: 'Not tracked yet', note: 'TrackFlow does not record this activity yet, so there is no figure.' },
  capture_gap: { text: 'Incomplete data', note: 'Some days could not be measured, so this week has no figure.' },
};

/** Text for one KPI row: the formatted value, or why there is none. */
export function formatValue(row: KpiRow): Omit<Cell, 'status' | 'revised'> {
  const missing = NOT_MEASURED[row.status];
  if (missing) return missing;
  if (row.value === null) return { text: 'No activity', note: 'Nothing to measure this week.' };
  const kind = KPIS.find((entry) => entry.kpi === row.kpi)?.kind ?? 'count';
  switch (kind) {
    case 'count':
      return { text: number(row.value, 0) };
    case 'ratio':
      return { text: `${number(row.value * 100, 1)} %` };
    case 'money':
      return { text: money(row.value, row.currency) };
    case 'money_per_kg':
      return { text: `${money(row.value, row.currency)} / kg` };
    case 'score':
      return { text: `${number(row.value, 1)} / 5` };
  }
}

/** One cell: a country and week can have one row per currency (costs are never added across currencies). */
export function cellFor(rows: KpiRow[]): Cell {
  const parts = rows.map(formatValue);
  const worst = rows.reduce<KpiStatus>((status, row) => (SEVERITY[row.status] > SEVERITY[status] ? row.status : status), 'no_activity');
  return {
    text: parts.map((part) => part.text).join(' · '),
    note: parts.find((part) => part.note)?.note,
    status: worst,
    revised: rows.some((row) => row.revision > 1),
  };
}

export type WeekLine = { start: string; label: string; daysCovered: number; cells: Record<string, Cell> };

/** Countries sorted with the two markets first, then the rest alphabetically and "unknown" last. */
export function countriesOf(rows: KpiRow[]): string[] {
  const rank = (code: string) => (COUNTRY_ORDER.includes(code) ? COUNTRY_ORDER.indexOf(code) : code === 'unknown' ? 99 : 50);
  return [...new Set(rows.map((row) => row.country))].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
}

/** Weekly rows of one KPI as a table: newest week first, one cell per country. */
export function kpiTable(rows: KpiRow[], kpi: KpiName): { countries: string[]; weeks: WeekLine[] } {
  const ofKpi = rows.filter((row) => row.kpi === kpi);
  const countries = countriesOf(ofKpi);
  const weeks = new Map<string, KpiRow[]>();
  for (const row of ofKpi) weeks.set(row.period_start, [...(weeks.get(row.period_start) ?? []), row]);
  return {
    countries,
    weeks: [...weeks.entries()]
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([start, weekRows]) => ({
        start,
        label: formatWeek(start, weekRows[0].period_end),
        daysCovered: Math.max(...weekRows.map((row) => row.days_covered)),
        cells: Object.fromEntries(
          countries
            .map((country) => [country, weekRows.filter((row) => row.country === country)] as const)
            .filter(([, countryRows]) => countryRows.length > 0)
            .map(([country, countryRows]) => [country, cellFor(countryRows)]),
        ),
      })),
  };
}
