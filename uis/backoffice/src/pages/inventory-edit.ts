/**
 * Inventory edit page — form to edit an existing item.
 * Warehouse field is disabled if item has movements.
 */

import { getItem, updateItem } from '../api.ts';
import { WAREHOUSES, CATEGORIES, UNITS_OF_MEASURE } from '../types.ts';
import { showToast, navigate, renderSelect, renderTextInput, formDataToJson } from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export async function renderInventoryEdit(id: string): Promise<string> {
  const nav = renderNav('/inventory/items');

  const data = await getItem(id).catch(() => null);
  if (!data) {
    return `
      ${nav}
      <div class="container">
        <div class="error-box">Item not found.</div>
        <a href="/inventory/items" data-nav>← Back to inventory</a>
      </div>`;
  }

  const item = data as {
    id: string; warehouse: string; client_name: string; sku: string;
    name: string; category: string; unit_of_measure: string;
    reorder_point: number; stock: number;
  };
  const hasMovements = data.movements && (data.movements as any[]).length > 0;

  const header = renderHeader(`Edit ${item.sku}`);
  const warehouseOpts = renderSelect('warehouse', WAREHOUSES, item.warehouse, 'Warehouse', false);
  const categoryOpts = renderSelect('category', CATEGORIES, item.category, 'Category', false);
  const uomOpts = renderSelect('unit_of_measure', UNITS_OF_MEASURE, item.unit_of_measure, 'Unit of Measure', false);

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="card">
        <p class="text-sm text-muted mb-2">Only include fields you want to change.</p>
        <form id="inventory-edit-form" data-form="inventory-edit" data-id="${item.id}">
          <div class="form-row half">
            ${warehouseOpts.replace('id="warehouse"', `id="warehouse" ${hasMovements ? 'disabled' : ''}`)}
            ${categoryOpts}
          </div>
          <div class="form-row half">
            ${renderTextInput('client_name', item.client_name, 'Client Name', false)}
            ${renderTextInput('sku', item.sku, 'SKU', false)}
          </div>
          ${renderTextInput('name', item.name, 'Item Name', false)}
          <div class="form-row half">
            ${uomOpts}
            ${renderTextInput('reorder_point', String(item.reorder_point), 'Reorder Point', false)}
          </div>
          ${hasMovements ? '<div class="notice">Warehouse change is locked because this item has movements.</div>' : ''}
          <div class="form-row">
            <button type="submit" class="primary">Save Changes</button>
            <a href="/inventory/detail?id=${item.id}" data-nav style="margin-left:0.5rem">Cancel</a>
          </div>
        </form>
      </div>
    </div>`;
}

export async function handleInventoryEditSubmit(e: Event) {
  e.preventDefault();
  const form = e.currentTarget as HTMLFormElement;
  const id = form.dataset.id;
  if (!id) return;

  const data = formDataToJson(form);

  // Remove warehouse if empty (disabled fields are not submitted)
  const payload: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(data)) {
    if (v === null || v === undefined) continue;
    if (k === 'reorder_point') {
      payload[k] = parseFloat(v as string);
    } else {
      payload[k] = v;
    }
  }

  const btn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    await updateItem(id, payload as any);
    showToast('Item updated successfully');
    navigate(`/inventory/detail?id=${id}`);
  } catch (err) {
    showToast((err as any).message || 'Update failed', 'error');
    btn.disabled = false;
    btn.textContent = 'Save Changes';
  }
}