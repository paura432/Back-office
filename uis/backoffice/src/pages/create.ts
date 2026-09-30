/**
 * Create page — form to create a new incident.
 */

import { createIncident } from '../api.ts';
import { CHANNELS, INCIDENT_TYPES, SEVERITIES, RESPONSIBLE_AREAS, WAREHOUSE_LOCATIONS } from '../types.ts';
import { showToast, navigate, renderSelect, renderTextInput, renderTextarea, formDataToJson } from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export function renderCreate(): string {
  const nav = renderNav('/create');
  const header = renderHeader('New Incident');
  const channelOpts = renderSelect('channel', CHANNELS, undefined, 'Channel', true);
  const typeOpts = renderSelect('type', INCIDENT_TYPES, undefined, 'Type', true);
  const severityOpts = renderSelect('severity', SEVERITIES, undefined, 'Severity', true);
  const areaOpts = renderSelect('responsible_area', RESPONSIBLE_AREAS, undefined, 'Responsible Area', true);
  const warehouseOpts = renderSelect('warehouse_location', WAREHOUSE_LOCATIONS, undefined, 'Warehouse Location', false);

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="card">
        <form id="create-form" data-form="create">
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
            ${renderTextInput('client_name', undefined, 'Client Name', false)}
          </div>
          ${renderTextInput('title', undefined, 'Title', true)}
          ${renderTextarea('description', undefined, 'Description', true)}
          ${renderTextInput('assigned_to', undefined, 'Assigned To', false)}
          ${renderTextInput('author', undefined, 'Author', true)}
          <div class="form-row">
            <button type="submit" class="primary">Create Incident</button>
            <button type="reset" style="margin-left:0.5rem">Reset</button>
          </div>
        </form>
      </div>
    </div>`;
}

export async function handleCreateSubmit(e: Event) {
  e.preventDefault();
  const form = e.currentTarget as HTMLFormElement;
  const data = formDataToJson(form);
  data.author = data.author || 'backoffice_user';

  const btn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = 'Creating…';

  try {
    const inc = await createIncident(data as any);
    showToast('Incident created successfully');
    navigate(`/detail?id=${inc.id}`);
  } catch (err) {
    showToast((err as any).message || 'Create failed', 'error');
    btn.disabled = false;
    btn.textContent = 'Create Incident';
  }
}