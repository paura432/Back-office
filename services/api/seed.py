"""
Seed script for TrackFlow Incident Manager.
Creates 12+ incidents with required coverage.

Idempotent: checks if seeds already exist before inserting.
"""

from __future__ import annotations

from uuid import uuid4

from database import get_connection, init_db

SEED_FLAG_KEY = "seed_applied_v1"


def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def generate_id() -> str:
    return str(uuid4())


SEED_INCIDENTS = [
    # 1 — critical, los_angeles
    {
        "id": generate_id(),
        "warehouse_location": "los_angeles",
        "client_name": "StyleMart",
        "channel": "wms_alert",
        "type": "system_outage",
        "severity": "critical",
        "responsible_area": "technology",
        "title": "WMS Los Ángeles caído — sin operación",
        "description": "El sistema de gestión de almacén de Los Ángeles no responde. Todo el picking y packing está detenido.",
        "status": "in_progress",
        "assigned_to": "Andrés Kim",
    },
    # 2 — critical, zaragoza
    {
        "id": generate_id(),
        "warehouse_location": "zaragoza",
        "client_name": "MundoModa",
        "channel": "client_email",
        "type": "sla_breach",
        "severity": "critical",
        "responsible_area": "last_mile_carrier",
        "title": "MundoModa: SLA superado 48h sin entrega",
        "description": "Lote de 300 pedidos de MundoModa no entregado. El cliente ha escalado a dirección.",
        "status": "assigned",
        "assigned_to": "Carlos Vega",
    },
    # 3 — high, los_angeles
    {
        "id": generate_id(),
        "warehouse_location": "los_angeles",
        "client_name": "QuickShip",
        "channel": "carrier_portal_alert",
        "type": "lost_parcel",
        "severity": "high",
        "responsible_area": "last_mile_carrier",
        "title": "Lote de 50 paquetes perdido en tránsito LA",
        "description": "El transportista reporta 50 paquetes como perdidos en el hub de Los Ángeles.",
        "status": "open",
        "assigned_to": None,
    },
    # 4 — high, zaragoza
    {
        "id": generate_id(),
        "warehouse_location": "zaragoza",
        "client_name": "Distribuciones García",
        "channel": "warehouse_call",
        "type": "carrier_failure",
        "severity": "high",
        "responsible_area": "warehouse_operations",
        "title": "Transportista no se presentó a recogida ZGZ",
        "description": "MRW no recogió los pedidos programados para hoy. 200 paquetes pendientes.",
        "status": "assigned",
        "assigned_to": "Ana Whitfield",
    },
    # 5 — medium, los_angeles
    {
        "id": generate_id(),
        "warehouse_location": "los_angeles",
        "client_name": "PetSupply Co",
        "channel": "dashboard",
        "type": "inventory_discrepancy",
        "severity": "medium",
        "responsible_area": "warehouse_operations",
        "title": "Discrepancia inventario SKU-445 en LA",
        "description": "El recuento físico muestra 45 unidades menos que el sistema para el SKU-445.",
        "status": "in_progress",
        "assigned_to": "Ana Whitfield",
    },
    # 6 — medium, zaragoza
    {
        "id": generate_id(),
        "warehouse_location": "zaragoza",
        "client_name": None,
        "channel": "dashboard",
        "type": "return_dispute",
        "severity": "medium",
        "responsible_area": "reverse_logistics",
        "title": "Devolución sin etiqueta — cliente no identificado",
        "description": "Producto devuelto sin información de remitente. No se puede procesar el reembolso.",
        "status": "open",
        "assigned_to": None,
    },
    # 7 — low, los_angeles
    {
        "id": generate_id(),
        "warehouse_location": "los_angeles",
        "client_name": "GreenHome",
        "channel": "client_email",
        "type": "return_dispute",
        "severity": "low",
        "responsible_area": "customer_experience",
        "title": "Cliente solicita revisión de devolución",
        "description": "GreenHome reclama que el reembolso de su devolución del 15/09 no se ha procesado.",
        "status": "open",
        "assigned_to": None,
    },
    # 8 — low, zaragoza
    {
        "id": generate_id(),
        "warehouse_location": "zaragoza",
        "client_name": "DecoHogar",
        "channel": "client_email",
        "type": "sla_breach",
        "severity": "low",
        "responsible_area": "customer_experience",
        "title": "Consulta DecoHogar sobre SLA estándar",
        "description": "El cliente pregunta si el SLA de entrega se ha cumplido en su último envío.",
        "status": "resolved",
        "assigned_to": "Valentina Cruz",
    },
    # 9 — critical, no client_name (null coverage)
    {
        "id": generate_id(),
        "warehouse_location": None,
        "client_name": None,
        "channel": "wms_alert",
        "type": "system_outage",
        "severity": "critical",
        "responsible_area": "technology",
        "title": "API de tracking global caída",
        "description": "El endpoint de tracking unificado no responde. Afecta a todos los transportistas.",
        "status": "open",
        "assigned_to": None,
    },
    # 10 — high, zaragoza
    {
        "id": generate_id(),
        "warehouse_location": "zaragoza",
        "client_name": "EuroFashion",
        "channel": "carrier_portal_alert",
        "type": "carrier_failure",
        "severity": "high",
        "responsible_area": "last_mile_carrier",
        "title": "SEUR no actualiza tracking ZGZ",
        "description": "SEUR no ha actualizado el estado de 120 envíos desde hace 24 horas.",
        "status": "assigned",
        "assigned_to": "Carlos Vega",
    },
    # 11 — reopened incident (must have audit trail showing resolved→reopened)
    {
        "id": generate_id(),
        "warehouse_location": "los_angeles",
        "client_name": "TechGear",
        "channel": "client_email",
        "type": "lost_parcel",
        "severity": "medium",
        "responsible_area": "last_mile_carrier",
        "title": "Paquete TechGear reabierto — cliente dice no recibido",
        "description": "Incidencia reopening. El cliente afirma no haber recibido el paquete que marcamos como entregado.",
        "status": "reopened",
        "assigned_to": "Carlos Vega",
    },
    # 12 — low, zaragoza, client_name null again for coverage
    {
        "id": generate_id(),
        "warehouse_location": "zaragoza",
        "client_name": "ZaraHome",
        "channel": "dashboard",
        "type": "inventory_discrepancy",
        "severity": "low",
        "responsible_area": "warehouse_operations",
        "title": "Ajuste inventario ZaraHome ZGZ",
        "description": "Diferencia de 3 unidades en SKU-982. Probable error de conteo.",
        "status": "resolved",
        "assigned_to": None,
    },
]


def run_seed(conn=None) -> None:
    """Execute the seed. Idempotent via metadata check."""
    close = conn is None
    if conn is None:
        conn = get_connection()

    init_db(conn)

    # Ensure metadata table exists before checking seed flag
    conn.execute(
        "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)"
    )

    # Check if seed already applied
    cursor = conn.execute(
        "SELECT value FROM metadata WHERE key = ?", (SEED_FLAG_KEY,)
    )
    if cursor.fetchone():
        print("Seed already applied. Skipping.")
        if close:
            conn.close()
        return

    now = utc_now()

    for inc in SEED_INCIDENTS:
        conn.execute(
            """
            INSERT OR IGNORE INTO incidents
                (id, warehouse_location, client_name, channel, type, severity,
                 responsible_area, title, description, status, assigned_to, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inc["id"],
                inc["warehouse_location"],
                inc["client_name"],
                inc["channel"],
                inc["type"],
                inc["severity"],
                inc["responsible_area"],
                inc["title"],
                inc["description"],
                inc["status"],
                inc["assigned_to"],
                now,
                now,
            ),
        )

    # Add audit trail for reopened incident (seed #11: TechGear → reopened)
    reopened_inc = SEED_INCIDENTS[10]  # index 10 = TechGear
    before_reopen = now.replace("T", " ")[:10] + " 00:00:00"

    # Insert resolved→reopened audit log
    conn.execute(
        """
        INSERT INTO incident_audit_log (id, incident_id, field_changed, old_value, new_value, changed_by, changed_at)
        VALUES (?, ?, 'status', 'resolved', 'reopened', 'system', ?)
        """,
        (generate_id(), reopened_inc["id"], now),
    )

    conn.execute(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        (SEED_FLAG_KEY, "true"),
    )
    conn.commit()
    print(f"Seed complete: {len(SEED_INCIDENTS)} incidents inserted.")

    if close:
        conn.close()


if __name__ == "__main__":
    run_seed()