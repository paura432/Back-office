/**
 * Utility helpers for TrackFlow Incident Manager UI.
 */

import type { Severity, IncidentStatus } from './types.ts';

// ──────────────────────── Badge styles ────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#ca8a04',
  low: '#16a34a',
};

const STATUS_COLORS: Record<string, string> = {
  open: '#6366f1',
  assigned: '#2563eb',
  in_progress: '#ca8a04',
  resolved: '#16a34a',
  closed: '#64748b',
  reopened: '#dc2626',
};

export function severityBadge(s: Severity): string {
  const color = SEVERITY_COLORS[s] ?? '#94a3b8';
  return `<span class="badge" style="background:${color};color:#fff">${s}</span>`;
}

export function statusBadge(s: IncidentStatus): string {
  const color = STATUS_COLORS[s] ?? '#94a3b8';
  return `<span class="badge" style="background:${color};color:#fff">${s.replace('_', ' ')}</span>`;
}

// ──────────────────────── Date formatting ────────────────────────

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDateShort(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ──────────────────────── Field label map ────────────────────────

export const FIELD_LABELS: Record<string, string> = {
  status: 'Status',
  assigned_to: 'Assigned to',
  responsible_area: 'Responsible area',
  severity: 'Severity',
  channel: 'Channel',
  type: 'Type',
  title: 'Title',
  description: 'Description',
  warehouse_location: 'Warehouse',
  client_name: 'Client name',
};

export function fieldLabel(f: string): string {
  return FIELD_LABELS[f] ?? f.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ──────────────────────── Toast notifications ────────────────────────

export function showToast(message: string, type: 'success' | 'error' = 'success') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ──────────────────────── Loading overlay ────────────────────────

export function showLoading(container: HTMLElement, msg = 'Loading…') {
  container.innerHTML = `<div class="loading">${msg}</div>`;
}

export function showError(container: HTMLElement, message: string) {
  container.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

export function showEmpty(container: HTMLElement, message = 'No data available') {
  container.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

// ──────────────────────── HTML escaping ────────────────────────

export function escapeHtml(s: string): string {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(s));
  return div.innerHTML;
}

// ──────────────────────── Form builder ────────────────────────

export function renderSelect(
  name: string,
  values: readonly string[],
  current?: string | null,
  label?: string,
  required = false,
): string {
  const lbl = label ?? name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const requiredAttr = required ? ' required' : '';
  const opts = values.map(
    (v) => `<option value="${v}"${v === current ? ' selected' : ''}>${v.replace(/_/g, ' ')}</option>`,
  ).join('');
  let nullOpt = '';
  if (!required) {
    nullOpt = `<option value=""${current === null || current === undefined ? ' selected' : ''}>— None —</option>`;
  }
  return `
    <div class="form-row">
      <label for="${name}">${lbl}${requiredAttr ? ' *' : ''}</label>
      <select id="${name}" name="${name}"${requiredAttr}>
        ${nullOpt}
        ${opts}
      </select>
    </div>`;
}

export function renderTextInput(
  name: string,
  current?: string | null,
  label?: string,
  required = false,
): string {
  const lbl = label ?? name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const requiredAttr = required ? ' required' : '';
  const val = current ?? '';
  return `
    <div class="form-row">
      <label for="${name}">${lbl}${requiredAttr ? ' *' : ''}</label>
      <input type="text" id="${name}" name="${name}" value="${escapeHtml(val)}"${requiredAttr}>
    </div>`;
}

export function renderTextarea(
  name: string,
  current?: string | null,
  label?: string,
  required = false,
): string {
  const lbl = label ?? name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const requiredAttr = required ? ' required' : '';
  const val = escapeHtml(current ?? '');
  return `
    <div class="form-row">
      <label for="${name}">${lbl}${requiredAttr ? ' *' : ''}</label>
      <textarea id="${name}" name="${name}"${requiredAttr}>${val}</textarea>
    </div>`;
}

// ──────────────────────── Parse form data ────────────────────────

export function formDataToJson(form: HTMLFormElement): Record<string, unknown> {
  const data: Record<string, unknown> = {};
  const fd = new FormData(form);
  for (const [k, v] of fd.entries()) {
    if (k === 'author') {
      data[k] = v;
    } else if (v === '') {
      data[k] = null;
    } else {
      data[k] = v;
    }
  }
  return data;
}

// ──────────────────────── Navigation helper ────────────────────────

export function navigate(path: string) {
  window.dispatchEvent(new CustomEvent('navigate', { detail: path }));
}

// ──────────────────────── Field changed labels ────────────────────────

export function changedFieldLabel(field: string): string {
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