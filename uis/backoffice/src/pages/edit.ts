/**
 * Edit page — form to edit an existing incident (PUT).
 */

import type { Incident } from '../types.ts';
import { getIncident, updateIncident } from '../api.ts';
import {
  CHANNELS, INCIDENT_TYPES, SEVERITIES, RESPONSIBLE_AREAS, WAREHOUSE_LOCATIONS,
} from '../types.ts';
import {
  showToast, navigate, renderSelect, renderTextInput, renderTextarea, formDataToJson,
} from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export async function renderEdit(id: string): Promise<string> {
  const nav = renderNav('/edit');

  const inc = await getIncident(id).catch(() => null);
  if (!inc) {
    return `
      ${nav}
      <div class="container">
        <div class="error-box">Incident not found.</div>
        <a href="/list" data-nav>← Back to list</a>
      </div>`;
  }

  const i = inc as Incident;
  const header = renderHeader(`Edit Incident ${i.id.slice(0, 8)}…`);

  const channelOpts = renderSelect('channel', CHANNELS, i.channel, 'Channel', false);
  const typeOpts = renderSelect('type', INCIDENT_TYPES, i.type, 'Type', false);
  const severityOpts = renderSelect('severity', SEVERITIES, i.severity, 'Severity', false);
  const areaOpts = renderSelect('responsible_area', RESPONSIBLE_AREAS, i.responsible_area, 'Responsible Area', false);
  const warehouseOpts = renderSelect('warehouse_location', WAREHOUSE_LOCATIONS, i.warehouse_location, 'Warehouse Location', false);

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="card">
        <p class="text-sm text-muted mb-2">Only include fields you want to change. Empty optional fields will be set to null.</p>
        <form id="edit-form" data-form="edit" data-id="${i.id}">
          <div class="form-row half">
            ${channelOpts}
            ${typeOpts}
          </div>
          <div class="form-row half">
            ${severityOpts}
            ${areaOpts}
          </div>
          <div class="form-row half">
            ${warehouseOpts}
            ${renderTextInput('client_name', i.client_name, 'Client Name', false)}
          </div>
          ${renderTextInput('title', i.title, 'Title', false)}
          ${renderTextarea('description', i.description, 'Description', false)}
          ${renderTextInput('assigned_to', i.assigned_to, 'Assigned To', false)}
          ${renderTextInput('author', '', 'Author', true)}
          <div class="form-row">
            <button type="submit" class="primary">Save Changes</button>
            <a href="/detail?id=${i.id}" data-nav style="margin-left:0.5rem">Cancel</a>
          </div>
        </form>
      </div>
    </div>`;
}

export async function handleEditSubmit(e: Event) {
  e.preventDefault();
  const form = e.currentTarget as HTMLFormElement;
  const id = form.dataset.id;
  if (!id) return;

  const data = formDataToJson(form);
  if (!data.author) {
    showToast('Author is required', 'error');
    return;
  }

  const btn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    await updateIncident(id, data as any);
    showToast('Incident updated successfully');
    navigate(`/detail?id=${id}`);
  } catch (err) {
    showToast((err as any).message || 'Update failed', 'error');
    btn.disabled = false;
    btn.textContent = 'Save Changes';
  }
}