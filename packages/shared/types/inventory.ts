/**
 * Inventory domain types for TrackFlow Inventory Manager.
 * These types are shared between uis/ (frontend) and services/ (backend declarations).
 * Backend Python uses equivalent Pydantic enums with same catalog values.
 *
 * See: specs/inventory-manager/spec.md
 * See: specs/inventory-manager/plan.md §1
 */

// ──────────────────────── Catalogs ────────────────────────

export const WAREHOUSES = [
  'los_angeles',
  'zaragoza',
] as const;
export type Warehouse = (typeof WAREHOUSES)[number];

export const CATEGORIES = [
  'fashion',
  'electronics',
  'cosmetics',
] as const;
export type Category = (typeof CATEGORIES)[number];

export const UNITS_OF_MEASURE = [
  'unit',
  'box',
  'kg',
] as const;
export type UnitOfMeasure = (typeof UNITS_OF_MEASURE)[number];

export const MOVEMENT_TYPES = [
  'inbound',
  'outbound',
  'adjustment',
] as const;
export type MovementType = (typeof MOVEMENT_TYPES)[number];

// ──────────────────────── Domain interfaces ────────────────────────

/**
 * Item — inventory article.
 * No persistent stock field. Stock is derived from movements.
 */
export interface Item {
  id: string;
  warehouse: Warehouse;
  client_name: string;
  sku: string;
  name: string;
  category: Category;
  unit_of_measure: UnitOfMeasure;
  reorder_point: number;   // REAL in SQLite — supports decimals (e.g. kg)
  created_at: string;       // ISO-8601
  updated_at: string;       // ISO-8601
}

/**
 * Lot — batch linked to an item.
 */
export interface Lot {
  id: string;
  item_id: string;
  lot_code: string;
  expiry_date: string;  // ISO-8601 date
  received_at: string;  // ISO-8601 datetime
}

/**
 * StockMovement — inventory movement record.
 * quantity is signed for adjustment (positive = increment, negative = decrement).
 */
export interface StockMovement {
  id: string;
  item_id: string;
  lot_id: string | null;
  movement_type: MovementType;
  quantity: number;       // REAL in SQLite — supports decimals
  reason: string | null;  // required when movement_type === 'adjustment'
  created_at: string;     // ISO-8601
}

/**
 * ItemWithStock — Item plus its derived stock and low-stock signal.
 * NOT a persistent type. Computed at query time.
 */
export interface ItemWithStock {
  id: string;
  warehouse: Warehouse;
  client_name: string;
  sku: string;
  name: string;
  category: Category;
  unit_of_measure: UnitOfMeasure;
  reorder_point: number;
  created_at: string;
  updated_at: string;
  stock: number;          // derived: inbound − outbound + adjustment
  is_low_stock: boolean;  // stock <= reorder_point
}

// ──────────────────────── Payloads (contract-only) ────────────────────────

/**
 * InitialLotPayload — only used at item creation time.
 * NOT a persistent field on Item. Required when category === 'cosmetics'.
 */
export interface InitialLotPayload {
  lot_code: string;
  expiry_date: string;  // ISO-8601 date
  received_at: string;  // ISO-8601 datetime
}

/**
 * ItemCreatePayload — fields to create a new item.
 * initial_lot is required for cosmetics, optional for fashion/electronics.
 * No stock field — stock is never set directly.
 */
export interface ItemCreatePayload {
  warehouse: Warehouse;
  client_name: string;
  sku: string;
  name: string;
  category: Category;
  unit_of_measure: UnitOfMeasure;
  reorder_point: number;
  initial_lot?: InitialLotPayload;
}

/**
 * ItemUpdatePayload — fields that can be updated on an existing item.
 * All fields optional (partial update via PUT).
 * Warehouse change is rejected server-side if item has movements.
 */
export interface ItemUpdatePayload {
  warehouse?: Warehouse;
  client_name?: string;
  sku?: string;
  name?: string;
  category?: Category;
  unit_of_measure?: UnitOfMeasure;
  reorder_point?: number;
}

/**
 * MovementCreatePayload — fields to register a new movement.
 * item_id comes from the URL path, not the body.
 * reason is required when movement_type === 'adjustment'.
 */
export interface MovementCreatePayload {
  lot_id?: string | null;
  movement_type: MovementType;
  quantity: number;
  reason?: string | null;
}