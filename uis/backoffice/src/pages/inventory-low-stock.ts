/**
 * Inventory low-stock page — items with stock <= reorder_point, grouped by warehouse.
 */

import { getLowStock } from '../api.ts';
import { escapeHtml } from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export async function renderInventoryLowStock(): Promise<string> {
  const data = await getLowStock().catch(() => null);

  let totalLow = 0;
  const sections: string[] = [];

  if (data) {
    for (const [warehouse, items] of Object.entries(data)) {
      if (!items || items.length === 0) continue;
      totalLow += items.length;
      const whLabel = warehouse.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      const rows = items.map((item) => `
      <tr>
        <td>${escapeHtml(item.client_name)}</td>
        <td>${escapeHtml(item.sku)}</td>
        <td>${escapeHtml(item.name)}</td>
        <td class="text-right" style="color:#dc2626;font-weight:700">${item.stock}</td>
        <td class="text-right">${item.reorder_point}</td>
      </tr>`).join('');
      sections.push(`
      <div class="card mt-2">
        <h3 class="mb-2">${whLabel} <span class="badge" style="background:#dc2626;color:#fff">${items.length}</span></h3>
        <table>
          <thead><tr><th>Client</th><th>SKU</th><th>Name</th><th class="text-right">Stock</th><th class="text-right">Reorder Point</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`);
    }
  }

  const nav = renderNav('/inventory/low-stock', totalLow);
  const header = renderHeader('Low Stock Alerts');

  const summaryHtml = totalLow > 0
    ? `<div class="card mb-4" style="text-align:center;border-left:4px solid #dc2626">
        <div style="font-size:2rem;font-weight:700;color:#dc2626">${totalLow}</div>
        <div class="text-sm text-muted">Items Below Reorder Point</div>
      </div>`
    : '<div class="card mb-4" style="text-align:center"><div class="empty-state">No items below reorder point</div></div>';

  return `
    ${nav}
    ${header}
    <div class="container">
      ${summaryHtml}
      ${sections.join('\n') || '<div class="empty-state">No low-stock items found</div>'}
    </div>`;
}