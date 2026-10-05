/**
 * API client layer for TrackFlow Incident Manager.
 * All communication with the FastAPI backend goes through this module.
 */

import type {
  Incident,
  IncidentAuditLog,
  IncidentCreatePayload,
  IncidentUpdatePayload,
  OpenBySeverityResponse,
  StatusTransitionPayload,
  IncidentStatus,
  Severity,
  ResponsibleArea,
  Item,
  ItemWithStock,
  ItemCreatePayload,
  ItemUpdatePayload,
  Lot,
  StockMovement,
  MovementCreatePayload,
  LowStockAlert,
  Warehouse,
} from './types.ts';

const BASE = '/api';

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`API error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, string>,
): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        url.searchParams.set(k, v);
      }
    }
  }
  const res = await fetch(url.toString(), {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = 'Unknown error';
    try {
      const err = await res.json();
      detail = err.detail ?? JSON.stringify(err);
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ──────────────────────── Public API: Incidents ────────────────────────

export function listIncidents(params?: {
  status?: IncidentStatus;
  severity?: Severity;
  responsible_area?: ResponsibleArea;
}): Promise<Incident[]> {
  return request<Incident[]>('GET', '/incidents', undefined, params as Record<string, string>);
}

export function getIncident(id: string): Promise<Incident & { audit_log: IncidentAuditLog[] }> {
  return request('GET', `/incidents/${id}`);
}

export function createIncident(payload: IncidentCreatePayload): Promise<Incident> {
  return request<Incident>('POST', '/incidents', payload);
}

export function updateIncident(id: string, payload: IncidentUpdatePayload): Promise<Incident> {
  return request<Incident>('PUT', `/incidents/${id}`, payload);
}

export function transitionStatus(id: string, payload: StatusTransitionPayload): Promise<Incident> {
  return request<Incident>('PATCH', `/incidents/${id}/status`, payload);
}

export function getOpenBySeverity(): Promise<OpenBySeverityResponse> {
  return request<OpenBySeverityResponse>('GET', '/incidents/open-by-severity');
}

// ──────────────────────── Public API: Inventory ────────────────────────

export function listItems(warehouse?: Warehouse): Promise<ItemWithStock[]> {
  const params: Record<string, string> = {};
  if (warehouse) params['warehouse'] = warehouse;
  return request<ItemWithStock[]>('GET', '/inventory/items', undefined, params);
}

export function getItem(id: string): Promise<ItemWithStock & { lots: Lot[]; movements: StockMovement[] }> {
  return request('GET', `/inventory/items/${id}`);
}

export function createItem(payload: ItemCreatePayload): Promise<Item> {
  return request<Item>('POST', '/inventory/items', payload);
}

export function updateItem(id: string, payload: ItemUpdatePayload): Promise<Item> {
  return request<Item>('PUT', `/inventory/items/${id}`, payload);
}

export function deleteItem(id: string): Promise<void> {
  return request<void>('DELETE', `/inventory/items/${id}`);
}

export function createLot(itemId: string, payload: { lot_code: string; expiry_date: string; received_at: string }): Promise<Lot> {
  return request<Lot>('POST', `/inventory/items/${itemId}/lots`, payload);
}

export function listLots(itemId: string): Promise<Lot[]> {
  return request<Lot[]>('GET', `/inventory/items/${itemId}/lots`);
}

export function getExpiredLots(): Promise<Lot[]> {
  return request<Lot[]>('GET', '/inventory/lots/expired');
}

export function createMovement(itemId: string, payload: MovementCreatePayload): Promise<StockMovement> {
  return request<StockMovement>('POST', `/inventory/items/${itemId}/movements`, payload);
}

export function listMovements(itemId: string): Promise<StockMovement[]> {
  return request<StockMovement[]>('GET', `/inventory/items/${itemId}/movements`);
}

export function getLowStock(): Promise<Record<string, LowStockAlert[]>> {
  return request<Record<string, LowStockAlert[]>>('GET', '/inventory/low-stock');
}