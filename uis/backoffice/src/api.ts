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

// ──────────────────────── Public API ────────────────────────

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