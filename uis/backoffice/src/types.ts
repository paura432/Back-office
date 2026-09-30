/**
 * Shared domain types for TrackFlow Incident Manager.
 * These mirror packages/shared/types/incident.ts exactly.
 * Imported locally because @repo/shared-types package entrypoint is broken.
 */

// ──────────────────────── Catalogs ────────────────────────

export const CHANNELS = [
  'carrier_portal_alert',
  'client_email',
  'wms_alert',
  'warehouse_call',
  'dashboard',
] as const;
export type Channel = (typeof CHANNELS)[number];

export const INCIDENT_TYPES = [
  'lost_parcel',
  'inventory_discrepancy',
  'carrier_failure',
  'system_outage',
  'return_dispute',
  'sla_breach',
] as const;
export type IncidentType = (typeof INCIDENT_TYPES)[number];

export const SEVERITIES = [
  'critical',
  'high',
  'medium',
  'low',
] as const;
export type Severity = (typeof SEVERITIES)[number];

export const RESPONSIBLE_AREAS = [
  'warehouse_operations',
  'last_mile_carrier',
  'reverse_logistics',
  'customer_experience',
  'commercial',
  'technology',
] as const;
export type ResponsibleArea = (typeof RESPONSIBLE_AREAS)[number];

export const INCIDENT_STATUSES = [
  'open',
  'assigned',
  'in_progress',
  'resolved',
  'closed',
  'reopened',
] as const;
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number];

export const WAREHOUSE_LOCATIONS = [
  'los_angeles',
  'zaragoza',
] as const;
export type WarehouseLocation = (typeof WAREHOUSE_LOCATIONS)[number];

// ──────────────────────── Transition graph ────────────────────────

export const VALID_TRANSITIONS: Record<string, string[]> = {
  open: ['assigned'],
  assigned: ['in_progress'],
  in_progress: ['resolved'],
  resolved: ['closed', 'reopened'],
  closed: [],
  reopened: [],
};

export function is_valid_transition(current: string, next: string): boolean {
  const allowed = VALID_TRANSITIONS[current];
  return allowed ? allowed.includes(next) : false;
}

// ──────────────────────── Interfaces ────────────────────────

export interface Incident {
  id: string;
  warehouse_location: WarehouseLocation | null;
  client_name: string | null;
  channel: Channel;
  type: IncidentType;
  severity: Severity;
  responsible_area: ResponsibleArea;
  title: string;
  description: string;
  status: IncidentStatus;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentAuditLog {
  id: string;
  incident_id: string;
  field_changed: string;
  old_value: string | null;
  new_value: string | null;
  changed_by: string;
  changed_at: string;
}

export interface IncidentCreatePayload {
  warehouse_location?: WarehouseLocation | null;
  client_name?: string | null;
  channel: Channel;
  type: IncidentType;
  severity: Severity;
  responsible_area: ResponsibleArea;
  title: string;
  description: string;
  assigned_to?: string | null;
  author: string;
}

export interface IncidentUpdatePayload {
  warehouse_location?: WarehouseLocation | null;
  client_name?: string | null;
  channel?: Channel;
  type?: IncidentType;
  severity?: Severity;
  responsible_area?: ResponsibleArea;
  title?: string;
  description?: string;
  assigned_to?: string | null;
  author: string;
}

export interface OpenBySeverityResponse {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface StatusTransitionPayload {
  status: IncidentStatus;
  author: string;
}