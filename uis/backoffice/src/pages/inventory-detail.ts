/**
 * Inventory detail page — item info, lots, movements, and actions.
 */

import { getItem, deleteItem } from '../api.ts';
import { escapeHtml, formatDate, showToast, navigate } from '../utils.ts';
import { renderNav, renderHeader } from '../components/header.ts';
import { renderMovementForm } from './inventory-movement.ts';

export async function renderInventoryDetail(id: string): Promise<string> {
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
    reorder_point: number; created_at: string; updated_at: string;
    stock: number; is_low_stock: boolean;
    lots: Array<{ id: string; lot_code: string; expiry_date: string; received_at: string }>;
    movements: Array<{
      id: string; movement_type: string; quantity: number;
      reason: string | null; lot_id: string | null; created_at: string;
    }>;
  };

  const header = renderHeader(`${item.name} (${item.sku})`);
  const detailCard = renderDetailCard(item);
  const lotsSection = renderLotsSection(item.lots);
  const movementsSection = renderMovementsSection(item.movements);
  const actionsCard = renderActions(item);

  return `
    ${nav}
    ${header}
    <div class="container">
      <div class="card mb-4">${detailCard}</div>
      ${actionsCard}
      <div class="card mt-4">
        <h2 class="mb-2">Lots</h2>
        ${lotsSection}
      </div>
      <div class="card mt-4">
        <h2 class="mb-2">Movements</h2>
        ${movementsSection}
      </div>
    </div>`;
}

function renderDetailCard(item: {
  id: string; warehouse: string; client_name: string; sku: string;
  name: string; category: string; unit_of_measure: string;
  reorder_point: number; stock: number; is_low_stock: boolean;
  created_at: string; updated_at: string;
}): string {
  const lowStockBadge = item.is_low_stock
    ? '<span class="badge" style="background:#dc2626;color:#fff">Low Stock</span>'
    : '';
  const rows: [string, string][] = [
    ['ID', item.id],
    ['SKU', item.sku],
    ['Name', item.name],
    ['Client', item.client_name],
    ['Warehouse', item.warehouse.replace(/_/g, ' ')],
    ['Category', item.category],
    ['Unit of Measure', item.unit_of_measure],
    ['Stock', `${item.stock} ${lowStockBadge}`],
    ['Reorder Point', String(item.reorder_point)],
    ['Created', formatDate(item.created_at)],
    ['Updated', formatDate(item.updated_at)],
  ];
  const dts = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
  return `<dl class="grid-detail">${dts}</dl>`;
}

function renderLotsSection(lots: Array<{
  id: string; lot_code: string; expiry_date: string; received_at: string;
}>): string {
  if (!lots || lots.length === 0) {
    return '<div class="empty-state">No lots for this item.</div>';
  }
  const rows = lots.map((lot) => {
    const expired = new Date(lot.expiry_date) < new Date();
    const expiredBadge = expired ? '<span class="badge" style="background:#dc2626;color:#fff">Expired</span>' : '';
    return `
    <tr>
      <td>${escapeHtml(lot.lot_code)}</td>
      <td>${formatDate(lot.expiry_date)}</td>
      <td>${formatDate(lot.received_at)}</td>
      <td>${expiredBadge}</td>
    </tr>`;
  }).join('');
  return `
    <table>
      <thead><tr><th>Lot Code</th><th>Expiry Date</th><th>Received At</th><th>Status</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderMovementsSection(movements: Array<{
  id: string; movement_type: string; quantity: number;
  reason: string | null; lot_id: string | null; created_at: string;
}>): string {
  if (!movements || movements.length === 0) {
    return '<div class="empty-state">No movements recorded.</div>';
  }
  const typeColors: Record<string, string> = {
    inbound: '#16a34a',
    outbound: '#dc2626',
    adjustment: '#ca8a04',
  };
  const rows = movements.map((m) => {
    const color = typeColors[m.movement_type] ?? '#94a3b8';
    return `
    <tr>
      <td><span class="badge" style="background:${color};color:#fff">${m.movement_type}</span></td>
      <td class="text-right">${m.movement_type === 'outbound' ? '-' : ''}${m.quantity}</td>
      <td>${m.reason ? escapeHtml(m.reason) : '<span class="text-muted">—</span>'}</td>
      <td>${m.lot_id ? escapeHtml(m.lot_id.slice(0, 8)) + '…' : '<span class="text-muted">—</span>'}</td>
      <td class="text-xs text-muted">${formatDate(m.created_at)}</td>
    </tr>`;
  }).join('');
  return `
    <table>
      <thead><tr><th>Type</th><th class="text-right">Qty</th><th>Reason</th><th>Lot</th><th>Date</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderActions(item: {
  id: string; stock: number;
  lots: Array<{ id: string; lot_code: string; expiry_date: string; received_at: string }>;
}): string {
  const editBtn = `<a href="/inventory/edit?id=${item.id}" class="primary button" data-nav>✏️ Edit</a>`;
  const deleteBtn = `<button class="danger" data-action="inventory-delete" data-id="${item.id}">🗑 Delete</button>`;
  return `
    <div class="card">
      <div class="flex gap-2 mb-2" style="align-items:center">
        ${editBtn}
        ${deleteBtn}
      </div>
      <hr class="mt-2 mb-2">
      <h3 class="mb-2">Register Movement</h3>
      ${renderMovementForm(item.id, item.stock, item.lots)}
    </div>`;
}

export function handleInventoryDeleteClick(e: MouseEvent) {
  const btn = e.currentTarget as HTMLButtonElement;
  const id = btn.dataset.id;
  if (!id) return;
  if (!confirm('Are you sure you want to delete this item?')) return;
  btn.disabled = true;
  btn.textContent = 'Deleting…';
  deleteItem(id)
    .then(() => {
      showToast('Item deleted');
      navigate('/inventory/items');
    })
    .catch((err) => {
      showToast(err.message || 'Delete failed', 'error');
      btn.disabled = false;
      btn.textContent = '🗑 Delete';
    });
}