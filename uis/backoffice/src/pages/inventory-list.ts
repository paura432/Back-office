/**
 * Inventory list page — table of items with derived stock.
 */

import type { Warehouse } from '../types.ts';
import { WAREHOUSES } from '../types.ts';
import { listItems } from '../api.ts';
import { escapeHtml } from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export async function renderInventoryList(params: URLSearchParams): Promise<string> {
  const nav = renderNav('/inventory/items');
  const header = renderHeader('Inventory');

  const filterWarehouse = params.get('warehouse') || '';
  const wh = filterWarehouse ? (filterWarehouse as Warehouse) : undefined;

  const items = await listItems(wh).catch(() => []);

  const filterForm = renderWarehouseFilter(filterWarehouse);
  const tableHtml = items.length > 0 ? renderTable(items) : '<div class="empty-state">No inventory items found</div>';

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
          <h2>Items <span class="text-muted text-sm">(${items.length})</span></h2>
          <a href="/inventory/create" class="button primary" data-nav>+ New Item</a>
        </div>
        ${tableHtml}
      </div>
    </div>`;
}

function renderWarehouseFilter(current: string): string {
  const opts = ['', ...WAREHOUSES].map((v) =>
    `<option value="${v}"${v === current ? ' selected' : ''}>${v ? v.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'All Warehouses'}</option>`).join('');
  return `
    <form method="get" data-nav-form-inventory>
      <div class="form-row">
        <label for="warehouse">Warehouse</label>
        <select id="warehouse" name="warehouse" onchange="this.form.submit()">${opts}</select>
      </div>
    </form>`;
}

function renderTable(items: Array<{
  id: string;
  warehouse: string;
  client_name: string;
  sku: string;
  name: string;
  category: string;
  stock: number;
  reorder_point: number;
  is_low_stock: boolean;
}>): string {
  const rows = items.map((item) => {
    const lowStockBadge = item.is_low_stock
      ? '<span class="badge" style="background:#dc2626;color:#fff">Low Stock</span>'
      : '';
    return `
    <tr>
      <td><a href="/inventory/detail?id=${item.id}" data-nav>${escapeHtml(item.sku)}</a></td>
      <td>${escapeHtml(item.client_name)}</td>
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.warehouse.replace(/_/g, ' '))}</td>
      <td>${escapeHtml(item.category)}</td>
      <td class="text-right">${item.stock}</td>
      <td class="text-right">${item.reorder_point}</td>
      <td>${lowStockBadge}</td>
    </tr>`;
  }).join('');
  return `
    <table>
      <thead><tr>
        <th>SKU</th>
        <th>Client</th>
        <th>Name</th>
        <th>Warehouse</th>
        <th>Category</th>
        <th class="text-right">Stock</th>
        <th class="text-right">Reorder Point</th>
        <th>Status</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}