'use client';

import { useEffect, useState } from 'react';
import {
  type Cell,
  type KpiResponse,
  type KpiRow,
  type PipelineStatus,
  KPIS,
  countryName,
  formatUpdated,
  formatWeek,
  kpiTable,
  mondayOf,
  weekRange,
} from '../../src/services/reporting';

const WEEKS = 8;
const STALE_AFTER_HOURS = 36; // the pipeline runs every day at 04:00 UTC

type State =
  | { status: 'loading' }
  | { status: 'error'; detail: string }
  | { status: 'ready'; rows: KpiRow[]; pipeline: PipelineStatus | null };

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`The API answered ${response.status}`);
  return (await response.json()) as T;
}

function Value({ cell }: { cell: Cell | undefined }) {
  if (!cell) return <td className="bp-num bp-muted">—</td>;
  return (
    <td className={`bp-num bp-cell--${cell.status}`} title={cell.note}>
      {cell.text}
      {cell.revised && <span className="bp-revised" title="Updated after it was first published because late data arrived."> revised</span>}
    </td>
  );
}

function Freshness({ pipeline }: { pipeline: PipelineStatus | null }) {
  if (!pipeline?.latest_computed_at) return null;
  const stale = (pipeline.data_freshness_hours ?? 0) > STALE_AFTER_HOURS;
  const failed = pipeline.last_run?.status === 'failed';
  return (
    <p className={`bp-updated${stale || failed ? ' bp-updated--warn' : ''}`}>
      Figures updated {formatUpdated(pipeline.latest_computed_at)}.
      {failed && ' The latest update failed, so these are the figures from the previous one.'}
      {!failed && stale && ' The daily update has not run for more than a day and a half; figures may be out of date.'}
    </p>
  );
}

export default function KpiDashboard() {
  const [state, setState] = useState<State>({ status: 'loading' });
  const [today] = useState(() => new Date());
  const range = weekRange(today, WEEKS);
  const currentWeek = mondayOf(today).toISOString().slice(0, 10);

  useEffect(() => {
    let cancelled = false;
    const query = new URLSearchParams({ granularity: 'week', start_date: range.start, end_date: range.end });
    Promise.all([
      getJson<KpiResponse>(`/api/reporting/kpis?${query}`),
      getJson<PipelineStatus>('/api/reporting/pipeline/status').catch(() => null),
    ])
      .then(([kpis, pipeline]) => !cancelled && setState({ status: 'ready', rows: kpis.rows, pipeline }))
      .catch((error: Error) => !cancelled && setState({ status: 'error', detail: error.message }));
    return () => {
      cancelled = true;
    };
  }, [range.start, range.end]);

  const rows = state.status === 'ready' ? state.rows : [];
  const lastWeekRows = rows.filter((row) => row.period_start === range.lastCompleteWeek);
  const lastWeekEnd = new Date(Date.parse(`${range.lastCompleteWeek}T00:00:00Z`) + 7 * 86_400_000).toISOString().slice(0, 10);

  return (
    <main className="bp-page">
      <header className="bp-header">
        <a className="bp-back" href="/">← Operations Backoffice</a>
        <h1>Business performance</h1>
        <p>
          Weekly executive KPIs for TrackFlow, compared by country. Weeks run Monday to Sunday (UTC); the last {WEEKS} weeks
          are shown, newest first.
        </p>
        {state.status === 'ready' && <Freshness pipeline={state.pipeline} />}
      </header>

      {state.status === 'loading' && <p className="bp-status">Loading business figures…</p>}
      {state.status === 'error' && (
        <p className="bp-status bp-status--error" title={state.detail}>
          Business figures are not available right now. Please try again in a few minutes.
        </p>
      )}
      {state.status === 'ready' && rows.length === 0 && (
        <p className="bp-status">No figures have been calculated for these weeks yet.</p>
      )}

      {rows.length > 0 && (
        <>
          <section className="bp-summary" aria-labelledby="bp-summary-title">
            <h2 id="bp-summary-title">
              Last complete week <span>{formatWeek(range.lastCompleteWeek, lastWeekEnd)}</span>
            </h2>
            <div className="bp-tiles">
              {KPIS.map(({ kpi, label }) => {
                const [week] = kpiTable(lastWeekRows, kpi).weeks;
                return (
                  <article className="bp-tile" key={kpi}>
                    <h3>{label}</h3>
                    {week ? (
                      <>
                        <dl>
                          {Object.entries(week.cells).map(([country, cell]) => (
                            <div key={country} className={`bp-cell--${cell.status}`} title={cell.note}>
                              <dt>{countryName(country)}</dt>
                              <dd>{cell.text}</dd>
                            </div>
                          ))}
                        </dl>
                        {week.daysCovered < 7 && <p className="bp-partial bp-tile-note">{week.daysCovered} of 7 days</p>}
                      </>
                    ) : (
                      <p className="bp-muted">No figures for this week yet.</p>
                    )}
                  </article>
                );
              })}
            </div>
          </section>

          <div className="bp-grid">
            {KPIS.map(({ kpi, label, question }) => {
              const table = kpiTable(rows, kpi);
              return (
                <section className="bp-card" key={kpi} aria-labelledby={`bp-${kpi}`}>
                  <h2 id={`bp-${kpi}`}>{label}</h2>
                  <p className="bp-question">{question}</p>
                  <table>
                    <thead>
                      <tr>
                        <th>Week</th>
                        {table.countries.map((country) => (
                          <th key={country} className="bp-num">{countryName(country)}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {table.weeks.map((week) => (
                        <tr key={week.start}>
                          <td>
                            {week.label}
                            {week.start === currentWeek && <span className="bp-partial"> · so far</span>}
                            {week.start !== currentWeek && week.daysCovered < 7 && (
                              <span className="bp-partial"> · {week.daysCovered} of 7 days</span>
                            )}
                          </td>
                          {table.countries.map((country) => (
                            <Value key={country} cell={week.cells[country]} />
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              );
            })}
          </div>

          <section className="bp-legend" aria-label="How to read this page">
            <p><b>Not tracked yet</b>: TrackFlow does not record this activity yet, so there is no figure to show.</p>
            <p><b>Incomplete data</b>: some days of the week could not be measured, so the week has no figure.</p>
            <p><b>No activity</b>: there was nothing to measure that week (for example, no deliveries).</p>
            <p><b>revised</b>: the figure changed after it was first published because late data arrived.</p>
            <p>
              Return rate compares returns requested with deliveries in the same week. Shipping costs are shown in each country’s
              currency and never added together. Figures are recalculated every day at 04:00 UTC.
            </p>
          </section>
        </>
      )}
    </main>
  );
}
