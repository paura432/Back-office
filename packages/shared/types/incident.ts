/**
 * Incident domain types for TrackFlow Incident Manager.
 * These types are shared between uis/ (frontend) and services/ (backend declarations).
 * Backend Python uses equivalent Pydantic enums with same catalog values.
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