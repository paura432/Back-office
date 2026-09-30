/**
 * List page — full incident table with filters.
 */

import type { Incident, IncidentStatus, Severity, ResponsibleArea } from '../types.ts';
import { listIncidents } from '../api.ts';
import {
  severityBadge, statusBadge, formatDateShort, escapeHtml,
} from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';
import { SEVERITIES, RESPONSIBLE_AREAS, INCIDENT_STATUSES } from '../types.ts';

export async function renderList(params: URLSearchParams): Promise<string> {
  const nav = renderNav('/list');
  const header = renderHeader('Incidents');

  // Read current filter values
  const filterStatus = params.get('status') || '';
  const filterSeverity = params.get('severity') || '';
  const filterArea = params.get('responsible_area') || '';

  // Build API params
  const apiParams: {
    status?: IncidentStatus;
    severity?: Severity;
    responsible_area?: ResponsibleArea;
  } = {};
  if (filterStatus) apiParams.status = filterStatus as IncidentStatus;
  if (filterSeverity) apiParams.severity = filterSeverity as Severity;
  if (filterArea) apiParams.responsible_area = filterArea as ResponsibleArea;

  const incidents = await listIncidents(apiParams).catch(() => [] as Incident[]);

  const filterForm = renderFilters(filterStatus, filterSeverity, filterArea);
  const tableHtml = incidents.length > 0 ? renderTable(incidents) : '<div class="empty-state">No incidents match your filters</div>';

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="card mb-4">
        <h2 class="mb-2">Filters</h2>
        ${filterForm}
      </div>
      <div class="card">
        <div class="flex justify-between items-center mb-2">
          <h2>Results <span class="text-muted text-sm">(${incidents.length})</span></h2>
          <a href="/create" class="button primary" data-nav>+ New Incident</a>
        </div>
        ${tableHtml}
      </div>
    </div>`;
}

function renderFilters(status: string, severity: string, area: string): string {
  const statusOpts = ['', ...INCIDENT_STATUSES].map((v) =>
    `<option value="${v}"${v === status ? ' selected' : ''}>${v ? v.replace(/_/g, ' ') : 'All'}</option>`).join('');
  const severityOpts = ['', ...SEVERITIES].map((v) =>
    `<option value="${v}"${v === severity ? ' selected' : ''}>${v ? v.charAt(0).toUpperCase() + v.slice(1) : 'All'}</option>`).join('');
  const areaOpts = ['', ...RESPONSIBLE_AREAS].map((v) =>
    `<option value="${v}"${v === area ? ' selected' : ''}>${v ? v.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'All'}</option>`).join('');

  return `
    <form id="filter-form" method="get" data-nav-form>
      <div class="form-row half">
        <div>
          <label for="status">Status</label>
          <select id="status" name="status" onchange="this.form.submit()">${statusOpts}</select>
        </div>
        <div>
          <label for="severity">Severity</label>
          <select id="severity" name="severity" onchange="this.form.submit()">${severityOpts}</select>
        </div>
        <div>
          <label for="responsible_area">Area</label>
          <select id="responsible_area" name="responsible_area" onchange="this.form.submit()">${areaOpts}</select>
        </div>
        <div style="display:flex;align-items:flex-end">
          <button type="submit" class="primary" style="width:100%">Apply</button>
        </div>
      </div>
    </form>`;
}

function renderTable(incidents: Incident[]): string {
  const rows = incidents.map((inc) => `
    <tr>
      <td><a href="/detail?id=${inc.id}" data-nav>${escapeHtml(inc.id.slice(0, 8))}…</a></td>
      <td>${escapeHtml(inc.title)}</td>
      <td>${severityBadge(inc.severity)}</td>
      <td>${statusBadge(inc.status)}</td>
      <td>${inc.assigned_to ? escapeHtml(inc.assigned_to) : '<span class="text-muted">—</span>'}</td>
      <td class="text-xs text-muted">${formatDateShort(inc.updated_at)}</td>
    </tr>`).join('');
  return `
    <table>
      <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th><th>Assignee</th><th>Updated</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}