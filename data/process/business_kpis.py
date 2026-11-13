"""Transformaciones puras del pipeline de desempeño de negocio.

Cada task de transformación de ``data/pipelines/pipeline.py`` envuelve una
función de este módulo: ``prepare_kpi_events`` (UTC, validación, dedupe y país
de las devoluciones), una función por KPI (``shipments_total_rows``,
``on_time_delivery_rate_rows``...) y ``assign_statuses``. También las usan
``check_quality`` y el agregado semanal de ``GET /reporting/kpis``. No leen ni
escriben en ninguna base de datos: la misma entrada da siempre la misma salida,
y por eso ``prepare_kpi_events`` se puede cachear por contenido.

Diseño: ``data/pipelines/PIPELINE_DESIGN.md``, §2.2 (KPIs), §2.5 (eventos
repetidos y tardíos), §6.4 (estados) y §10 (subflows).
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

EMPTY_CHECKSUM = hashlib.md5(b"").hexdigest()
UNKNOWN_COUNTRY = "unknown"
NOT_APPLICABLE = "n/a"


@dataclass(frozen=True)
class SourceEvent:
    """``producer`` es el ``service`` con el que llega el evento a
    ``telemetry_events`` (``x-source`` del contrato). ``required`` son las
    propiedades sin las que el evento no sirve para ningún KPI."""

    producer: str
    natural_key: str | None
    required: tuple[str, ...]


SOURCE_EVENTS = {
    "shipment_created": SourceEvent("backend", "shipment_id", ("shipment_id", "carrier", "destination_country")),
    "shipment_delivered": SourceEvent(
        "integration", "shipment_id", ("shipment_id", "carrier", "destination_country", "on_time")
    ),
    "order_created": SourceEvent("backend", "order_id", ("order_id",)),
    "return_requested": SourceEvent("backend", "return_id", ("return_id", "order_id")),
    # Sin clave de negocio: solo se deduplica por eventId (PK de la tabla).
    "customer_satisfaction_submitted": SourceEvent("frontend", None, ("score",)),
}
SOURCE_EVENT_TYPES = tuple(SOURCE_EVENTS)


@dataclass(frozen=True)
class Kpi:
    sources: tuple[str, ...]
    unit: str  # "{currency}" se sustituye por la moneda de la fila
    is_ratio: bool


KPIS = {
    "shipments_total": Kpi(("shipment_created",), "shipments", False),
    "on_time_delivery_rate": Kpi(("shipment_delivered",), "ratio", True),
    "shipping_cost_total": Kpi(("shipment_delivered",), "{currency}", False),
    "shipping_cost_per_kg": Kpi(("shipment_delivered",), "{currency}/kg", True),
    "return_rate": Kpi(("return_requested", "shipment_delivered"), "ratio", True),
    "customer_satisfaction_avg": Kpi(("customer_satisfaction_submitted",), "score_1_5", True),
}

# Gravedad para combinar estados de varios días o filas: una cifra que no se
# puede medir domina sobre una medida, y una medida sobre la ausencia real.
STATUS_SEVERITY = {"no_activity": 0, "ok": 1, "capture_gap": 2, "not_instrumented": 3}
MEASURABLE = ("ok", "no_activity")

ID_FIELDS = ("shipment_id", "order_id", "return_id")
NUMBER_FIELDS = ("shipping_cost", "weight_kg", "score")
REQUIRED_COLUMNS = ("event_id", "event_type", "timestamp", "service", "tags")

COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")
CARRIER_CODE = re.compile(r"^[a-z0-9_]{2,32}$")
CURRENCIES = ("USD", "EUR")


def checksum(event_ids: Iterable[str]) -> str:
    """md5 de los ``event_id`` ordenados y unidos por comas. Es la misma
    huella que calcula en SQL ``storage.day_fingerprints`` con
    ``md5(string_agg(event_id::text, ',' order by event_id))``."""
    return hashlib.md5(",".join(sorted(event_ids)).encode()).hexdigest()


def days_between(start: date, end: date) -> list[date]:
    """Días de ``[start, end)``."""
    return [start + timedelta(days=offset) for offset in range((end - start).days)]


def unit_for(kpi: str, currency: str) -> str:
    unit = KPIS[kpi].unit
    return unit.replace("{currency}", "currency" if currency == NOT_APPLICABLE else currency)


# --- Validación de propiedades -----------------------------------------------
#
# Cada propiedad que usa algún KPI se acepta solo si cumple su definición en
# docs/telemetry/event-schemas.json; si no, queda vacía. Si era obligatoria
# para su evento, ``flag_invalid`` descarta el evento y lo cuenta en
# ``events_invalid``. Así un ``on_time: "yes"`` no cuenta como entrega tardía,
# ni un coste negativo resta, ni un ``score: 9`` sube la media.


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _entity_id(value):
    """``entityId``: entero >= 1."""
    return int(value) if _is_number(value) and float(value).is_integer() and value >= 1 else None


def _matching(pattern: re.Pattern):
    return lambda value: value if isinstance(value, str) and pattern.fullmatch(value) else None


def _at_least(minimum: float, *, exclusive: bool = False):
    def conform(value):
        if not _is_number(value) or value < minimum or (exclusive and value == minimum):
            return None
        return float(value)

    return conform


def _score(value):
    """Encuesta: entero de 1 a 5."""
    return int(value) if _is_number(value) and float(value).is_integer() and 1 <= value <= 5 else None


TAG_RULES = {
    "shipment_id": _entity_id,
    "order_id": _entity_id,
    "return_id": _entity_id,
    "carrier": _matching(CARRIER_CODE),
    "destination_country": _matching(COUNTRY_CODE),
    "country": _matching(COUNTRY_CODE),
    "currency": lambda value: value if isinstance(value, str) and value in CURRENCIES else None,
    "on_time": lambda value: value if isinstance(value, bool) else None,
    "shipping_cost": _at_least(0),
    "weight_kg": _at_least(0, exclusive=True),
    "score": _score,
}


# --- Preparación -----------------------------------------------------------


def prepare_events(events: pd.DataFrame) -> pd.DataFrame:
    """Normaliza las filas leídas de ``telemetry_events``: ``event_id`` como
    texto, ``timestamp`` en UTC, ``metric_date`` (día UTC del hecho) y una
    columna validada por cada propiedad de ``tags`` que usa algún KPI.

    Una fila sin las columnas de ``telemetry_events`` es un error de código,
    no de datos, y se rechaza entera. Un ``timestamp`` ilegible o unos
    ``tags`` que no son un objeto dejan el evento inválido."""
    missing = [column for column in REQUIRED_COLUMNS if column not in events.columns]
    if missing:
        raise ValueError(f"telemetry_events rows are missing columns: {', '.join(missing)}")
    df = events.loc[:, list(REQUIRED_COLUMNS)].copy()
    df["event_id"] = df["event_id"].astype(str)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601", errors="coerce")
    df["metric_date"] = df["timestamp"].dt.date
    tags = [value if isinstance(value, dict) else {} for value in df["tags"]]
    for field, conform in TAG_RULES.items():
        values = [conform(tag.get(field)) for tag in tags]
        if field in ID_FIELDS:
            df[field] = pd.Series(pd.array(values, dtype="Int64"), index=df.index)
        elif field in NUMBER_FIELDS:
            df[field] = pd.to_numeric(pd.Series(values, index=df.index, dtype=object))
        else:
            df[field] = pd.Series(values, index=df.index, dtype=object)
    return df.drop(columns=["tags"])


def flag_invalid(df: pd.DataFrame) -> pd.Series:
    """True en los eventos sin ``timestamp`` legible o a los que les falta una
    propiedad obligatoria para el pipeline (o no cumple el contrato). Se
    descartan y se cuentan en ``events_invalid``."""
    invalid = df["timestamp"].isna()
    for event_type, spec in SOURCE_EVENTS.items():
        missing = df[list(spec.required)].isna().any(axis=1)
        invalid |= df["event_type"].eq(event_type) & missing
    return invalid


def flag_duplicates(df: pd.DataFrame) -> pd.Series:
    """True en las repeticiones del mismo hecho con otro ``eventId``. Se
    queda la primera aparición por ``timestamp`` y, si empatan, por
    ``event_id``. ``df`` solo debe contener eventos válidos."""
    ordered = df.sort_values(["timestamp", "event_id"])
    duplicated = pd.Series(False, index=df.index)
    for event_type, spec in SOURCE_EVENTS.items():
        if spec.natural_key is None:
            continue
        of_type = ordered[ordered["event_type"].eq(event_type)]
        duplicated.loc[of_type.index] = of_type.duplicated(subset=[spec.natural_key], keep="first")
    return duplicated


def return_countries(df: pd.DataFrame) -> dict[int, str]:
    """País de cada pedido: ``destination_country`` de ``order_created`` y, si
    falta, el del ``shipment_created`` del mismo ``order_id``."""
    countries: dict[int, str] = {}
    for event_type in ("shipment_created", "order_created"):  # order_created gana
        rows = df[df["event_type"].eq(event_type) & df["order_id"].notna() & df["destination_country"].notna()]
        for order_id, country in zip(rows["order_id"], rows["destination_country"]):
            countries[int(order_id)] = country
    return countries


def prepare_kpi_events(events: pd.DataFrame, window_start: date, window_end: date) -> dict:
    """Primer paso de la transformación (§2.2 y §2.5).

    ``events`` son las filas de ``telemetry_events`` de los tipos fuente desde
    30 días antes de la ventana: hacen falta para deduplicar y para encontrar
    el país de las devoluciones. Devuelve:

    - ``events``: los eventos válidos, sin duplicados y con ``metric_date``
      dentro de ``[window_start, window_end)``. Las devoluciones llevan en
      ``country`` el país de su pedido (o ``unknown``).
    - ``days``: el resumen de cada día de la ventana para
      ``pipeline_run_days`` (eventos leídos, inválidos, duplicados y huella).
    - ``totals``: los contadores de la corrida para ``pipeline_runs``.
    """
    window = days_between(window_start, window_end)
    df = prepare_events(events)
    invalid = flag_invalid(df)
    duplicated = flag_duplicates(df[~invalid]).reindex(df.index, fill_value=False)
    clean = df[~invalid & ~duplicated]

    in_window = clean[clean["metric_date"].isin(window)].copy()
    is_return = in_window["event_type"].eq("return_requested")
    countries = return_countries(clean)
    in_window.loc[is_return, "country"] = [
        countries.get(int(order_id), UNKNOWN_COUNTRY) for order_id in in_window.loc[is_return, "order_id"]
    ]

    days = []
    for day in window:
        of_day = df["metric_date"].eq(day)
        days.append({
            "metric_date": day.isoformat(),
            "events_extracted": int(of_day.sum()),
            "events_invalid": int((of_day & invalid).sum()),
            "events_deduplicated": int((of_day & duplicated).sum()),
            "events_after_dedupe": int((of_day & ~invalid & ~duplicated).sum()),
            # Huella del día completo (también inválidos y duplicados), la que
            # compara detect_changed_days en las corridas siguientes.
            "source_checksum": checksum(df.loc[of_day, "event_id"]),
        })

    window_events = df[df["metric_date"].isin(window)]
    return {
        "events": in_window,
        "days": days,
        "totals": {
            "events_extracted": sum(day["events_extracted"] for day in days),
            "events_deduplicated": sum(day["events_deduplicated"] for day in days),
            "events_invalid": sum(day["events_invalid"] for day in days),
            "source_max_timestamp": window_events["timestamp"].max().isoformat() if not window_events.empty else None,
        },
    }


# --- KPIs ------------------------------------------------------------------
#
# Una función por KPI de §2.2. Todas reciben ``prepare_kpi_events()["events"]``
# y devuelven las filas ``ok`` (medidas) de ese KPI; ``assign_statuses``
# completa después los días y países sin medida.


def _fsum(values: Iterable) -> float:
    """Suma exacta e independiente del orden: la misma entrada da siempre la
    misma cifra, y el upsert no ve cambios donde no los hay."""
    return math.fsum(float(value) for value in values)


def _row(kpi, day, country, carrier, currency, numerator, denominator, status, event_ids) -> dict:
    if status not in MEASURABLE:
        value = None
    elif KPIS[kpi].is_ratio:
        value = round(numerator / denominator, 6) if denominator else None
    else:
        value = numerator
    return {
        "kpi": kpi,
        "metric_date": day.isoformat(),
        "country": country,
        "carrier": carrier,
        "currency": currency,
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "unit": unit_for(kpi, currency),
        "status": status,
        "source_event_count": len(event_ids),
        "source_checksum": checksum(event_ids),
    }


def _grouped(frame: pd.DataFrame, by: list[str]):
    for key, group in frame.groupby(by, sort=True):
        yield dict(zip(by, key)), group


def _of_type(events: pd.DataFrame, event_type: str) -> pd.DataFrame:
    return events[events["event_type"].eq(event_type)]


def _with_cost(events: pd.DataFrame) -> pd.DataFrame:
    """Entregas con coste y moneda. Nunca se suman USD y EUR: el coste se
    agrupa siempre por moneda."""
    delivered = _of_type(events, "shipment_delivered")
    return delivered[delivered["shipping_cost"].notna() & delivered["currency"].notna()]


def shipments_total_rows(events: pd.DataFrame) -> list[dict]:
    """Volumen de envíos: ``shipment_id`` distintos creados por día, país y
    transportista."""
    return [
        _row("shipments_total", key["metric_date"], key["destination_country"], key["carrier"], NOT_APPLICABLE,
             float(len(group)), None, "ok", group["event_id"])
        for key, group in _grouped(_of_type(events, "shipment_created"),
                                   ["metric_date", "destination_country", "carrier"])
    ]


def on_time_delivery_rate_rows(events: pd.DataFrame) -> list[dict]:
    """Tasa de entrega a tiempo: entregas con ``on_time = true`` / entregas."""
    return [
        _row("on_time_delivery_rate", key["metric_date"], key["destination_country"], key["carrier"], NOT_APPLICABLE,
             float(group["on_time"].eq(True).sum()), float(len(group)), "ok", group["event_id"])
        for key, group in _grouped(_of_type(events, "shipment_delivered"),
                                   ["metric_date", "destination_country", "carrier"])
    ]


def shipping_cost_total_rows(events: pd.DataFrame) -> list[dict]:
    """Coste de transporte: Σ ``shipping_cost`` por moneda."""
    return [
        _row("shipping_cost_total", key["metric_date"], key["destination_country"], key["carrier"], key["currency"],
             _fsum(group["shipping_cost"]), None, "ok", group["event_id"])
        for key, group in _grouped(_with_cost(events), ["metric_date", "destination_country", "carrier", "currency"])
    ]


def shipping_cost_per_kg_rows(events: pd.DataFrame) -> list[dict]:
    """Coste por kg: Σ ``shipping_cost`` / Σ ``weight_kg``, solo con las
    entregas que traen los dos."""
    with_weight = _with_cost(events)
    with_weight = with_weight[with_weight["weight_kg"].notna()]
    return [
        _row("shipping_cost_per_kg", key["metric_date"], key["destination_country"], key["carrier"], key["currency"],
             _fsum(group["shipping_cost"]), _fsum(group["weight_kg"]), "ok", group["event_id"])
        for key, group in _grouped(with_weight, ["metric_date", "destination_country", "carrier", "currency"])
    ]


def return_rate_rows(events: pd.DataFrame, heartbeat: pd.DataFrame) -> list[dict]:
    """Tasa de devoluciones: devoluciones solicitadas ÷ entregas del mismo día
    y país. Es una aproximación de periodo, no una cohorte por envío (§2.2)."""
    alive = heartbeat_by_day(heartbeat)
    returns = _of_type(events, "return_requested")
    delivered = _of_type(events, "shipment_delivered")
    returned = {key: group for key, group in returns.groupby(["metric_date", "country"])}
    deliveries = {key: group for key, group in delivered.groupby(["metric_date", "destination_country"])}
    rows = []
    for day, country in sorted(set(returned) | set(deliveries)):
        numerator_events = returned.get((day, country), returns.iloc[0:0])
        denominator_events = deliveries.get((day, country), delivered.iloc[0:0])
        # Sin devoluciones y con el backend en silencio no sabemos si hubo
        # alguna: no es un 0. Igual para las entregas y la integración.
        silent = (numerator_events.empty and (day, SOURCE_EVENTS["return_requested"].producer) not in alive) or (
            denominator_events.empty and (day, SOURCE_EVENTS["shipment_delivered"].producer) not in alive
        )
        event_ids = [*numerator_events["event_id"], *denominator_events["event_id"]]
        rows.append(_row("return_rate", day, country, NOT_APPLICABLE, NOT_APPLICABLE,
                         float(len(numerator_events)), float(len(denominator_events)),
                         "capture_gap" if silent else "ok", event_ids))
    return rows


def customer_satisfaction_avg_rows(events: pd.DataFrame) -> list[dict]:
    """Satisfacción del cliente: Σ ``score`` / respuestas, por país (``unknown``
    si la encuesta no lo trae)."""
    surveys = _of_type(events, "customer_satisfaction_submitted")
    surveys = surveys.assign(country=surveys["country"].fillna(UNKNOWN_COUNTRY))
    return [
        _row("customer_satisfaction_avg", key["metric_date"], key["country"], NOT_APPLICABLE, NOT_APPLICABLE,
             _fsum(group["score"]), float(len(group)), "ok", group["event_id"])
        for key, group in _grouped(surveys, ["metric_date", "country"])
    ]


# --- Estados ---------------------------------------------------------------


def assign_status(*, instrumented: bool, has_source_events: bool, producers_alive: bool) -> str:
    """Estado de un KPI, día y país sin ninguna fila medida (§6.4)."""
    if not instrumented:
        return "not_instrumented"
    if has_source_events:
        # Hay eventos fuente, pero ninguno sirve para este KPI (por ejemplo,
        # entregas sin coste): no se puede medir, no es actividad cero.
        return "capture_gap"
    return "no_activity" if producers_alive else "capture_gap"


def _instrumented(kpi: str, day: date, instrumented_since: dict[str, str | None]) -> bool:
    """Un KPI está instrumentado un día si todos sus eventos fuente habían
    aparecido ya en ``telemetry_events`` ese día o antes."""
    for source in KPIS[kpi].sources:
        first_seen = instrumented_since.get(source)
        if first_seen is None or pd.Timestamp(first_seen).tz_convert("UTC").date() > day:
            return False
    return True


def heartbeat_by_day(heartbeat: pd.DataFrame) -> set[tuple[date, str]]:
    """(día UTC, service) con al menos un evento de cualquier tipo."""
    if heartbeat.empty:
        return set()
    hours = pd.to_datetime(heartbeat["hour"], utc=True)
    return set(zip(hours.dt.date, heartbeat["service"]))


def assign_statuses(
    measured: list[dict],
    events: pd.DataFrame,
    heartbeat: pd.DataFrame,
    instrumented_since: dict[str, str | None],
    window_start: date,
    window_end: date,
    expected_countries: tuple[str, ...],
) -> list[dict]:
    """Filas finales de la ventana. Descarta las medidas de días en los que su
    KPI aún no estaba instrumentado y añade una fila por cada KPI, día y país
    esperado sin medida, con su estado: ``no_activity``, ``capture_gap`` o
    ``not_instrumented`` (§6.4)."""
    measured = [row for row in measured
                if _instrumented(row["kpi"], date.fromisoformat(row["metric_date"]), instrumented_since)]
    present = {(row["kpi"], row["metric_date"], row["country"]) for row in measured}
    alive = heartbeat_by_day(heartbeat)
    source_countries = defaultdict(set)  # (event_type, día) -> países con eventos válidos
    for event_type, day, country in zip(events["event_type"], events["metric_date"],
                                        events["destination_country"].fillna(events["country"])):
        if isinstance(country, str):
            source_countries[(event_type, day)].add(country)

    rows = list(measured)
    for kpi, spec in KPIS.items():
        for day in days_between(window_start, window_end):
            for country in expected_countries:
                if (kpi, day.isoformat(), country) in present:
                    continue
                status = assign_status(
                    instrumented=_instrumented(kpi, day, instrumented_since),
                    has_source_events=any(country in source_countries[(source, day)] for source in spec.sources),
                    producers_alive=all((day, SOURCE_EVENTS[source].producer) in alive for source in spec.sources),
                )
                denominator = 0.0 if spec.is_ratio and status == "no_activity" else None
                rows.append(_row(kpi, day, country, NOT_APPLICABLE, NOT_APPLICABLE, 0.0, denominator, status, []))
    rows.sort(key=lambda row: (row["metric_date"], row["kpi"], row["country"], row["carrier"], row["currency"]))
    return rows


def count_kpi_rows(days: list[dict], rows: list[dict]) -> list[dict]:
    """Añade a cada resumen de día cuántas filas de KPI tiene (checkpoint)."""
    per_day = defaultdict(int)
    for row in rows:
        per_day[row["metric_date"]] += 1
    return [{**day, "kpi_rows": per_day[day["metric_date"]]} for day in days]


# --- Ventana y calidad -----------------------------------------------------


def plan_window(
    current: dict[date, str],
    stored: dict[date, str],
    today: date,
    audit_days: int,
    default_days: int,
) -> dict:
    """Ventana de la corrida automática (§2.5): como mínimo los últimos
    ``default_days`` días completos y, si la huella de algún día de los
    últimos ``audit_days`` ya no coincide con la que se cargó, desde ese día
    hasta hoy. Un día sin eventos tiene la huella vacía."""
    base_start = today - timedelta(days=default_days)
    changed = [
        day for day in days_between(today - timedelta(days=audit_days), today)
        if current.get(day, EMPTY_CHECKSUM) != stored.get(day, EMPTY_CHECKSUM)
    ]
    late = [day for day in changed if day < base_start and day in stored]
    return {
        "window_start": min([base_start, *changed]),
        "window_end": today,
        "late_days": len(late),
        "changed_days": [day.isoformat() for day in changed],
    }


def quality_by_day(
    events: pd.DataFrame,
    heartbeat: pd.DataFrame,
    days: list[dict],
    window_start: date,
    window_end: date,
    run_started_at: datetime,
) -> dict[str, dict]:
    """Señales de calidad por día (§6.5 y §6.6): eventos por ``service`` y
    hora (huecos y ráfagas), volumen frente a la mediana de los 7 días
    previos, duplicados, inválidos y eventos con fecha posterior a la
    corrida (reloj adelantado)."""
    df = prepare_events(events)
    per_day = df.groupby("metric_date").size()
    hours = pd.to_datetime(heartbeat["hour"], utc=True) if not heartbeat.empty else pd.Series(dtype="datetime64[ns, UTC]")
    summary = {day["metric_date"]: day for day in days}
    quality = {}
    for day in days_between(window_start, window_end):
        previous = [int(per_day.get(day - timedelta(days=offset), 0)) for offset in range(1, 8)]
        median = float(pd.Series(previous).median())
        source_events = int(per_day.get(day, 0))
        of_day = heartbeat[hours.dt.date.eq(day).to_numpy()] if not heartbeat.empty else heartbeat
        by_service: dict[str, dict[str, int]] = defaultdict(dict)
        for service, hour, count in zip(of_day["service"], pd.to_datetime(of_day["hour"], utc=True), of_day["events"]):
            by_service[service][f"{hour.hour:02d}"] = int(count)
        extracted = summary[day.isoformat()]["events_extracted"]
        duplicates = summary[day.isoformat()]["events_deduplicated"]
        quality[day.isoformat()] = {
            "events_by_service_hour": dict(sorted(by_service.items())),
            "source_events": source_events,
            "median_source_events_prev_7d": median,
            "volume_ratio_vs_median": round(source_events / median, 4) if median else None,
            "duplicates": duplicates,
            "duplicate_rate": round(duplicates / extracted, 4) if extracted else None,
            "invalid": summary[day.isoformat()]["events_invalid"],
            "future_timestamps": int((df["metric_date"].eq(day) & df["timestamp"].gt(run_started_at)).sum()),
        }
    return quality


# --- Agregado semanal (endpoint) -------------------------------------------


def combine_status(statuses: Iterable[str]) -> str:
    return max(statuses, key=STATUS_SEVERITY.__getitem__)


def aggregate_weekly(rows: list[dict]) -> list[dict]:
    """Agrega filas diarias de ``executive_kpis_daily`` por semana ISO
    (lunes a domingo), KPI, país y moneda, sumando transportistas:
    ``Σ numerador / Σ denominador``, nunca una media de medias.

    El estado de la semana es el más grave de sus días; si algún día no se
    pudo medir (``capture_gap`` o ``not_instrumented``) la semana no tiene
    ``value``. ``days_covered`` cuenta los días con filas: si es menor que 7,
    la semana está incompleta (bordes del periodo pedido o días sin
    calcular)."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        week_start = row["metric_date"] - timedelta(days=row["metric_date"].weekday())
        groups[(row["kpi"], week_start, row["country"])].append(row)

    result = []
    for (kpi, week_start, country), group in sorted(groups.items()):
        spec = KPIS[kpi]
        status = combine_status(row["status"] for row in group)
        currencies = sorted({row["currency"] for row in group} - {NOT_APPLICABLE}) or [NOT_APPLICABLE]
        for currency in currencies:
            measured = [row for row in group if row["currency"] == currency and row["status"] in MEASURABLE]
            numerator = _fsum(row["numerator"] for row in measured)
            denominator = _fsum(row["denominator"] or 0 for row in measured) if spec.is_ratio else None
            if status not in MEASURABLE:
                value = None
            elif spec.is_ratio:
                value = round(numerator / denominator, 6) if denominator else None
            else:
                value = numerator
            result.append({
                "kpi": kpi,
                "period_start": week_start,
                "period_end": week_start + timedelta(days=7),
                "country": country,
                "carrier": "all",
                "currency": currency,
                "numerator": numerator,
                "denominator": denominator,
                "value": value,
                "unit": unit_for(kpi, currency),
                "status": status,
                "days_covered": len({row["metric_date"] for row in group}),
                "revision": max(row["revision"] for row in group),
                "computed_at": max(row["computed_at"] for row in group),
            })
    return result
