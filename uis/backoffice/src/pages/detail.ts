/**
 * Detail page — full incident info + audit timeline + transition buttons.
 */

import type { Incident, IncidentAuditLog, IncidentStatus } from '../types.ts';
import { VALID_TRANSITIONS } from '../types.ts';
import { getIncident, transitionStatus } from '../api.ts';
import {
  severityBadge, statusBadge, formatDate,
  navigate, showToast,
} from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export async function renderDetail(id: string): Promise<string> {
  const nav = renderNav('/detail');

  const data = await getIncident(id).catch(() => null);
  if (!data) {
    return `
      ${nav}
      <div class="container">
        <div class="error-box">Incident not found.</div>
        <a href="/list" data-nav>← Back to list</a>
      </div>`;
  }

  const inc = data as Incident;
  const audit = (data as any).audit_log as IncidentAuditLog[];

  const header = renderHeader(`Incident ${esc(inc.id.slice(0, 8))}…`);
  const detailCard = renderDetailCard(inc);
  const transitionsCard = renderTransitions(inc);
  const editLink = `<a href="/edit?id=${inc.id}" class="primary button" data-nav style="display:inline-block;margin-bottom:1rem">✏️ Edit</a>`;
  const auditCard = renderAuditTimeline(audit);

  return `
    ${nav}
    ${header}
    <div class="container">
      ${editLink}
      <div class="card mb-4">${detailCard}</div>
      ${transitionsCard}
      <div class="card mt-4">
        <h2 class="mb-2">Audit Log</h2>
        ${auditCard}
      </div>
    </div>`;
}

function esc(s: string): string {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}

function renderDetailCard(inc: Incident): string {
  const rows: [string, string][] = [
    ['ID', inc.id],
    ['Title', inc.title],
    ['Description', inc.description],
    ['Severity', severityBadge(inc.severity)],
    ['Status', statusBadge(inc.status)],
    ['Channel', inc.channel.replace(/_/g, ' ')],
    ['Type', inc.type.replace(/_/g, ' ')],
    ['Area', inc.responsible_area.replace(/_/g, ' ')],
    ['Warehouse', inc.warehouse_location ?? '<span class="text-muted">—</span>'],
    ['Client', inc.client_name ?? '<span class="text-muted">—</span>'],
    ['Assignee', inc.assigned_to ?? '<span class="text-muted">—</span>'],
    ['Created', formatDate(inc.created_at)],
    ['Updated', formatDate(inc.updated_at)],
  ];
  const dts = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
  return `<dl class="grid-detail">${dts}</dl>`;
}

function renderTransitions(inc: Incident): string {
  if (inc.status === 'closed') {
    return '<div class="card"><p class="text-muted">This incident is closed. No transitions available.</p></div>';
  }
  const allowed = VALID_TRANSITIONS[inc.status] ?? [];
  if (allowed.length === 0) {
    return '<div class="card"><p class="text-muted">No transitions available from current status.</p></div>';
  }
  const buttons = allowed.map((s) => `
    <button class="primary" data-action="transition" data-status="${s}" data-id="${inc.id}">→ ${s.replace(/_/g, ' ')}</button>
  `).join('');
  return `
    <div class="card">
      <h2 class="mb-2">Change Status</h2>
      <p class="text-sm text-muted mb-2">From: <strong>${inc.status.replace(/_/g, ' ')}</strong></p>
      <div class="flex gap-2">${buttons}</div>
    </div>`;
}

export function handleTransitionClick(e: MouseEvent) {
  const btn = e.currentTarget as HTMLButtonElement;
  const status = btn.dataset.status;
  const id = btn.dataset.id;
  if (!status || !id) return;
  btn.disabled = true;
  btn.textContent = '…';
  const typedStatus = status as IncidentStatus;
  transitionStatus(id, { status: typedStatus, author: 'backoffice_user' })
    .then(() => {
      showToast(`Status changed to ${status.replace(/_/g, ' ')}`);
      navigate(`/detail?id=${id}`);
    })
    .catch((err) => {
      showToast(err.message || 'Transition failed', 'error');
      btn.disabled = false;
      btn.textContent = `→ ${status.replace(/_/g, ' ')}`;
    });
}

function renderAuditTimeline(audit: IncidentAuditLog[]): string {
  if (!audit || audit.length === 0) {
    return '<div class="empty-state">No audit entries yet.</div>';
  }
  const items = audit.map((e) => {
    const lbl = changedFieldLabel(e.field_changed);
    return `
    <div class="audit-item">
      <div class="flex items-center justify-between">
        <strong>${lbl}</strong>
        <span class="text-xs text-muted">${formatDate(e.changed_at)}</span>
      </div>
      <div class="text-sm text-muted">
        ${esc(e.old_value ?? '—')} → ${esc(e.new_value ?? '—')}
        <span class="text-xs">by ${esc(e.changed_by)}</span>
      </div>
    </div>`;
  }).join('');
  return `<div class="audit-timeline">${items}</div>`;
}

function changedFieldLabel(field: string): string {
  const m: Record<string, string> = {
    status: 'Status',
    assigned_to: 'Assignee',
    responsible_area: 'Area',
    severity: 'Severity',
    channel: 'Channel',
    type: 'Type',
    title: 'Title',
    description: 'Description',
    warehouse_location: 'Warehouse',
    client_name: 'Client',
  };
  return m[field] ?? field;
}