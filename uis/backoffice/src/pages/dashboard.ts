/**
 * Dashboard page — shows open-by-severity cards and recent incidents.
 */

import type { Incident, OpenBySeverityResponse } from '../types.ts';
import { listIncidents, getOpenBySeverity } from '../api.ts';
import { severityBadge, statusBadge, formatDateShort } from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export async function renderDashboard(): Promise<string> {
  const nav = renderNav('/dashboard');
  const header = renderHeader('Dashboard');

  let cardsHtml = '<div class="loading">Loading metrics…</div>';
  let tableHtml = '<div class="loading">Loading incidents…</div>';

  // Fire both requests in parallel
  const [severityData, recentIncidents] = await Promise.all([
    getOpenBySeverity().catch(() => null),
    listIncidents().catch(() => [] as Incident[]),
  ]);

  // Cards
  if (severityData) {
    cardsHtml = renderCards(severityData);
  } else {
    cardsHtml = '<div class="error-box">Could not load metrics</div>';
  }

  // Recent table
  const open = recentIncidents.filter((i) => i.status !== 'closed' && i.status !== 'resolved');
  const recent = open.slice(0, 10);
  if (recent.length > 0) {
    tableHtml = renderRecentTable(recent);
  } else {
    tableHtml = '<div class="empty-state">No open incidents</div>';
  }

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="grid-4">${cardsHtml}</div>
      <div class="card mt-4">
        <h2 class="mb-2">Open Incidents</h2>
        ${tableHtml}
      </div>
    </div>`;
}

function renderCards(data: OpenBySeverityResponse): string {
  const items = [
    { label: 'Critical', count: data.critical, color: '#dc2626' },
    { label: 'High', count: data.high, color: '#ea580c' },
    { label: 'Medium', count: data.medium, color: '#ca8a04' },
    { label: 'Low', count: data.low, color: '#16a34a' },
  ];
  return items.map((i) => `
    <div class="card" style="text-align:center">
      <div style="font-size:2.5rem;font-weight:700;color:${i.color}">${i.count}</div>
      <div style="font-size:0.875rem;color:#64748b;margin-top:0.25rem">${i.label}</div>
    </div>`).join('');
}

function renderRecentTable(incidents: Incident[]): string {
  const rows = incidents.map((inc) => `
    <tr>
      <td><a href="/detail?id=${inc.id}" data-nav>${escape(inc.id.slice(0, 8))}…</a></td>
      <td>${escape(inc.title)}</td>
      <td>${severityBadge(inc.severity)}</td>
      <td>${statusBadge(inc.status)}</td>
      <td>${inc.assigned_to ? escape(inc.assigned_to) : '<span class="text-muted">—</span>'}</td>
      <td class="text-xs text-muted">${formatDateShort(inc.updated_at)}</td>
    </tr>`).join('');
  return `
    <table>
      <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th><th>Assignee</th><th>Updated</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function escape(s: string): string {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}