'use client';

import { type FormEvent, useEffect, useState } from 'react';

type EventsRow = { date: string; service: string; event_type: string; events: number; share: number };
type ErrorRateRow = { date: string; app: string; sessions: number; sessions_with_errors: number; errors: number; error_rate: number };
type FrontendErrorRow = { date: string; app: string; route_template: string; error_kind: string; errors: number; distinct_errors: number; sessions: number };
type VitalRow = { date: string; app: string; route_template: string; metric: string; unit: string; samples: number; mean: number; p75: number; poor_rate: number };
type Report = {
  period: { from: string; to: string };
  metrics: { events_per_day: EventsRow[]; error_rate_per_day: ErrorRateRow[]; frontend_errors_per_day: FrontendErrorRow[]; web_vitals_per_day: VitalRow[] };
};
type State = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; report: Report };

const percent = (value: number) => `${(value * 100).toFixed(1)} %`;
const vital = (value: number, unit: string) => (unit === 'ms' ? `${Math.round(value)} ms` : value.toFixed(3));
const utc = (iso: string) => iso.replace('T', ' ').replace(/(:\d\d)(\.\d+)?Z$/, '$1 UTC');

function Bar({ ratio, label }: { ratio: number; label: string }) {
  return (
    <span className="tr-bar" title={label}>
      <i style={{ width: `${Math.max(ratio * 100, ratio > 0 ? 2 : 0)}%` }} />
    </span>
  );
}

function Empty({ columns }: { columns: number }) {
  return (
    <tr>
      <td className="tr-empty" colSpan={columns}>No events in this period.</td>
    </tr>
  );
}

export default function TelemetryReportView() {
  const [range, setRange] = useState({ from: '', to: '' });
  const [query, setQuery] = useState('');
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    fetch(`/api/telemetry/report${query}`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`The API answered ${response.status}`);
        return (await response.json()) as Report;
      })
      .then((report) => !cancelled && setState({ status: 'ready', report }))
      .catch((error: Error) => !cancelled && setState({ status: 'error', message: error.message }));
    return () => {
      cancelled = true;
    };
  }, [query]);

  function apply(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (range.from) params.set('start_date', `${range.from}T00:00:00Z`);
    if (range.to) params.set('end_date', `${range.to}T00:00:00Z`);
    setQuery(params.size ? `?${params}` : '');
  }

  const report = state.status === 'ready' ? state.report : null;
  const metrics = report?.metrics;
  const maxEvents = Math.max(1, ...(metrics?.events_per_day.map((row) => row.events) ?? []));

  return (
    <main className="tr-page">
      <header className="tr-header">
        <div>
          <a className="tr-back" href="/">← Operations Backoffice</a>
          <h1>Telemetry report</h1>
          <p>Technical view for the engineering team, built from <code>telemetry_events</code>. The API caches each period for 60 s.</p>
        </div>
        <form className="tr-range" onSubmit={apply}>
          <label>From (UTC, inclusive)<input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label>
          <label>To (UTC, exclusive)<input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label>
          <button type="submit">Apply</button>
        </form>
      </header>

      {report && (
        <p className="tr-period">
          Period: <b>{utc(report.period.from)}</b> → <b>{utc(report.period.to)}</b>
          {!query && ' (default: last 7 days)'}
        </p>
      )}
      {state.status === 'loading' && <p className="tr-status">Loading report…</p>}
      {state.status === 'error' && <p className="tr-status tr-status--error">Report unavailable. {state.message}.</p>}

      {metrics && (
        <div className="tr-grid">
          <section className="tr-card tr-card--wide">
            <h2>Events per day</h2>
            <p className="tr-question">How many events does each service record per day, and which types dominate?</p>
            <table>
              <thead><tr><th>Date</th><th>Service</th><th>Event type</th><th className="tr-num">Events</th><th className="tr-bar-col" aria-hidden="true" /><th className="tr-num">Share of day</th></tr></thead>
              <tbody>
                {metrics.events_per_day.length === 0 && <Empty columns={6} />}
                {metrics.events_per_day.map((row) => (
                  <tr key={`${row.date}-${row.service}-${row.event_type}`}>
                    <td>{row.date}</td><td>{row.service}</td><td><code>{row.event_type}</code></td>
                    <td className="tr-num">{row.events}</td>
                    <td className="tr-bar-col"><Bar ratio={row.events / maxEvents} label={`${row.events} events`} /></td>
                    <td className="tr-num">{percent(row.share)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="tr-card">
            <h2>Error rate per day</h2>
            <p className="tr-question">What share of browser sessions hit at least one frontend error?</p>
            <table>
              <thead><tr><th>Date</th><th>App</th><th className="tr-num">Sessions</th><th className="tr-num">With errors</th><th className="tr-num">Errors</th><th className="tr-num">Rate</th><th className="tr-bar-col" aria-hidden="true" /></tr></thead>
              <tbody>
                {metrics.error_rate_per_day.length === 0 && <Empty columns={7} />}
                {metrics.error_rate_per_day.map((row) => (
                  <tr key={`${row.date}-${row.app}`}>
                    <td>{row.date}</td><td>{row.app}</td>
                    <td className="tr-num">{row.sessions}</td><td className="tr-num">{row.sessions_with_errors}</td><td className="tr-num">{row.errors}</td>
                    <td className="tr-num">{percent(row.error_rate)}</td>
                    <td className="tr-bar-col"><Bar ratio={row.error_rate} label={percent(row.error_rate)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="tr-card">
            <h2>Frontend errors per day</h2>
            <p className="tr-question">Where and how does the frontend fail?</p>
            <table>
              <thead><tr><th>Date</th><th>App</th><th>Route</th><th>Kind</th><th className="tr-num">Errors</th><th className="tr-num">Distinct</th><th className="tr-num">Sessions</th></tr></thead>
              <tbody>
                {metrics.frontend_errors_per_day.length === 0 && <Empty columns={7} />}
                {metrics.frontend_errors_per_day.map((row) => (
                  <tr key={`${row.date}-${row.app}-${row.route_template}-${row.error_kind}`}>
                    <td>{row.date}</td><td>{row.app}</td><td><code>{row.route_template}</code></td><td>{row.error_kind}</td>
                    <td className="tr-num">{row.errors}</td><td className="tr-num">{row.distinct_errors}</td><td className="tr-num">{row.sessions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="tr-card tr-card--wide">
            <h2>Web Vitals per day</h2>
            <p className="tr-question">How fast do pages load and respond for real users? CLS is a unitless score.</p>
            <table>
              <thead><tr><th>Date</th><th>App</th><th>Route</th><th>Metric</th><th className="tr-num">Samples</th><th className="tr-num">Mean</th><th className="tr-num">p75</th><th className="tr-num">Rated poor</th></tr></thead>
              <tbody>
                {metrics.web_vitals_per_day.length === 0 && <Empty columns={8} />}
                {metrics.web_vitals_per_day.map((row) => (
                  <tr key={`${row.date}-${row.app}-${row.route_template}-${row.metric}`}>
                    <td>{row.date}</td><td>{row.app}</td><td><code>{row.route_template}</code></td><td>{row.metric}</td>
                    <td className="tr-num">{row.samples}</td><td className="tr-num">{vital(row.mean, row.unit)}</td><td className="tr-num">{vital(row.p75, row.unit)}</td>
                    <td className="tr-num">{percent(row.poor_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </main>
  );
}
