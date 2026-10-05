/**
 * Inventory dashboard page — summary cards and navigation hub.
 */

import { getLowStock } from '../api.ts';
import { renderNav, renderHeader } from '../components/header.ts';

export async function renderInventoryDashboard(): Promise<string> {
  const lowStockData = await getLowStock().catch(() => null);

  let lowStockCount = 0;
  if (lowStockData) {
    for (const items of Object.values(lowStockData)) {
      if (items) lowStockCount += items.length;
    }
  }

  const nav = renderNav('/inventory', lowStockCount);
  const header = renderHeader('Inventory Dashboard');

  const lowStockCard = lowStockCount > 0
    ? `<div class="card" style="border-left:4px solid #dc2626;text-align:center">
         <div style="font-size:2.5rem;font-weight:700;color:#dc2626">${lowStockCount}</div>
         <div class="text-sm text-muted">Items Below Reorder Point</div>
         <a href="/inventory/low-stock" class="btn btn-sm mt-1" style="display:inline-block;margin-top:0.5rem">View Details</a>
       </div>`
    : `<div class="card" style="text-align:center">
         <div style="font-size:2.5rem;font-weight:700;color:#16a34a">0</div>
         <div class="text-sm text-muted">Items Below Reorder Point</div>
       </div>`;

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="card-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem">
        <a href="/inventory/items" class="card" style="text-align:center;cursor:pointer">
          <div style="font-size:2rem;font-weight:700;color:#2563eb">📦</div>
          <div class="text-sm text-muted">View All Items</div>
        </a>
        <a href="/inventory/create" class="card" style="text-align:center;cursor:pointer">
          <div style="font-size:2rem;font-weight:700;color:#16a34a">➕</div>
          <div class="text-sm text-muted">Create New Item</div>
        </a>
        <a href="/inventory/low-stock" class="card" style="text-align:center;cursor:pointer">
          <div style="font-size:2rem;font-weight:700;color:#dc2626">⚠️</div>
          <div class="text-sm text-muted">Low Stock Alerts</div>
        </a>
      </div>
      ${lowStockCard}
    </div>`;
}