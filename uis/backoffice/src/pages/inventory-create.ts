/**
 * Inventory create page — form to create a new item.
 * Cosmetics category requires initial_lot fields.
 */

import { createItem } from '../api.ts';
import { WAREHOUSES, CATEGORIES, UNITS_OF_MEASURE } from '../types.ts';
import { showToast, navigate, renderSelect, renderTextInput, formDataToJson } from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export function renderInventoryCreate(): string {
  const nav = renderNav('/inventory/create');
  const header = renderHeader('New Inventory Item');

  const warehouseOpts = renderSelect('warehouse', WAREHOUSES, undefined, 'Warehouse', true);
  const categoryOpts = renderSelect('category', CATEGORIES, undefined, 'Category', true);
  const uomOpts = renderSelect('unit_of_measure', UNITS_OF_MEASURE, undefined, 'Unit of Measure', true);

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="card">
        <form id="inventory-create-form" data-form="inventory-create">
          <div class="form-row half">
            ${warehouseOpts}
            ${categoryOpts}
          </div>
          <div class="form-row half">
            ${renderTextInput('client_name', undefined, 'Client Name', true)}
            ${renderTextInput('sku', undefined, 'SKU', true)}
          </div>
          ${renderTextInput('name', undefined, 'Item Name', true)}
          <div class="form-row half">
            ${uomOpts}
            ${renderTextInput('reorder_point', undefined, 'Reorder Point', false)}
          </div>
          <div id="initial-lot-section" style="display:none" class="card mt-2">
            <h3 class="mb-2">Initial Lot (required for Cosmetics)</h3>
            <div class="form-row half">
              ${renderTextInput('lot_code', undefined, 'Lot Code', false)}
              ${renderTextInput('expiry_date', undefined, 'Expiry Date (YYYY-MM-DD)', false)}
            </div>
            ${renderTextInput('received_at', undefined, 'Received At (ISO-8601)', false)}
          </div>
          <div class="form-row">
            <button type="submit" class="primary">Create Item</button>
            <a href="/inventory/items" data-nav style="margin-left:0.5rem">Cancel</a>
          </div>
        </form>
      </div>
    </div>
    <script>
      document.addEventListener('DOMContentLoaded', function() {
        const cat = document.querySelector('[name="category"]');
        const lotSection = document.getElementById('initial-lot-section');
        if (cat && lotSection) {
          cat.addEventListener('change', function() {
            lotSection.style.display = cat.value === 'cosmetics' ? 'block' : 'none';
          });
          if (cat.value === 'cosmetics') lotSection.style.display = 'block';
        }
      });
    </script>`;
}

export async function handleInventoryCreateSubmit(e: Event) {
  e.preventDefault();
  const form = e.currentTarget as HTMLFormElement;
  const data = formDataToJson(form);

  const btn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = 'Creating…';

  try {
    const payload: Record<string, unknown> = {
      warehouse: data.warehouse,
      client_name: data.client_name,
      sku: data.sku,
      name: data.name,
      category: data.category,
      unit_of_measure: data.unit_of_measure,
      reorder_point: data.reorder_point !== null ? parseFloat(data.reorder_point as string) : 0,
    };

    if (data.category === 'cosmetics' && data.lot_code) {
      payload.initial_lot = {
        lot_code: data.lot_code,
        expiry_date: data.expiry_date,
        received_at: data.received_at || new Date().toISOString(),
      };
    }

    const item = await createItem(payload as any);
    showToast('Item created successfully');
    navigate(`/inventory/detail?id=${item.id}`);
  } catch (err) {
    showToast((err as any).message || 'Create failed', 'error');
    btn.disabled = false;
    btn.textContent = 'Create Item';
  }
}