/**
 * Movement registration page — form to register inbound/outbound/adjustment.
 * Embedded in detail page via inline form.
 */

import { createMovement } from '../api.ts';
import { MOVEMENT_TYPES } from '../types.ts';
import { showToast, navigate, escapeHtml } from '../utils.ts';

/**
 * Renders an inline movement form for use in the inventory detail page.
 * This is returned as part of the detail page render.
 */
export function renderMovementForm(itemId: string, _currentStock: number, lots: Array<{ id: string; lot_code: string }>): string {
  const typeOpts = MOVEMENT_TYPES.map((t) =>
    `<option value="${t}">${t.charAt(0).toUpperCase() + t.slice(1)}</option>`).join('');
  const lotOpts = lots.length > 0
    ? lots.map((l) => `<option value="${l.id}">${escapeHtml(l.lot_code)}</option>`).join('')
    : '';
  const lotSection = lots.length > 0
    ? `<div class="form-row">
        <label for="mvt-lot-id">Lot</label>
        <select id="mvt-lot-id" name="mvt_lot_id"><option value="">— None —</option>${lotOpts}</select>
      </div>`
    : '<input type="hidden" name="mvt_lot_id" value="">';

  return `
    <form id="movement-form" data-form="movement" data-item-id="${itemId}">
      <div class="form-row half">
        <div>
          <label for="mvt-type">Type *</label>
          <select id="mvt-type" name="mvt_type" required>
            <option value="">— Select —</option>
            ${typeOpts}
          </select>
        </div>
        <div>
          <label for="mvt-qty">Quantity *</label>
          <input type="number" id="mvt-qty" name="mvt_quantity" step="any" min="0" required>
        </div>
      </div>
      ${lotSection}
      <div class="form-row">
        <label for="mvt-reason">Reason (required for adjustment)</label>
        <input type="text" id="mvt-reason" name="mvt_reason">
      </div>
      <div class="form-row">
        <button type="submit" class="primary">Register Movement</button>
      </div>
    </form>`;
}

export async function handleMovementSubmit(e: Event) {
  e.preventDefault();
  const form = e.currentTarget as HTMLFormElement;
  const itemId = form.dataset.itemId;
  if (!itemId) return;

  const fd = new FormData(form);
  const movementType = fd.get('mvt_type') as string;
  const quantity = parseFloat(fd.get('mvt_quantity') as string);
  const lotId = fd.get('mvt_lot_id') as string;
  const reason = fd.get('mvt_reason') as string;

  if (!movementType || isNaN(quantity) || quantity <= 0) {
    showToast('Please select a type and enter a positive quantity', 'error');
    return;
  }

  if (movementType === 'adjustment' && !reason) {
    showToast('Reason is required for adjustment movements', 'error');
    return;
  }

  const payload: Record<string, unknown> = {
    movement_type: movementType,
    quantity,
  };
  if (lotId) payload.lot_id = lotId;
  if (reason) payload.reason = reason;

  const btn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = 'Registering…';

  try {
    await createMovement(itemId, payload as any);
    showToast('Movement registered');
    navigate(`/inventory/detail?id=${itemId}`);
  } catch (err) {
    showToast((err as any).message || 'Movement failed', 'error');
    btn.disabled = false;
    btn.textContent = 'Register Movement';
  }
}