"""Technical telemetry report: operational metrics over ``public.telemetry_events``.

Every metric follows the same order: load (SQL) -> refine (pandas) -> convert
types -> group -> aggregate -> serve. The period ``[start, end)`` is resolved
once by the caller (``GET /telemetry/report``) and only applied here, in SQL.
Metric functions have no side effects: the same period over the same stored
rows always gives the same result.

Reads use ``TELEMETRY_READ_DATABASE_DSN``, a login role granted
``telemetry_reader`` (SELECT only, see ``supabase/migrations``). Errors never
include the DSN.
"""
import os
from datetime import datetime, timezone

import pandas as pd
import psycopg
from psycopg import sql

SESSION_EVENTS = ("page_viewed", "frontend_error_occurred")
ERROR_EVENT = "frontend_error_occurred"
VITALS_EVENT = "web_vitals_measured"
VITAL_UNITS = {"CLS": "score", "FCP": "ms", "INP": "ms", "LCP": "ms", "TTFB": "ms"}


class TelemetryReportError(Exception):
    """The events could not be loaded, so no report was produced."""


def load_events(columns: list[str], start: datetime, end: datetime, event_types: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Load ``columns`` of the events in ``[start, end)``, optionally only some
    event types. It never reads the whole table."""
    dsn = os.environ.get("TELEMETRY_READ_DATABASE_DSN")
    if not dsn:
        raise TelemetryReportError("telemetry report storage is not configured")
    query = sql.SQL('select {} from public.telemetry_events where "timestamp" >= %s and "timestamp" < %s').format(
        sql.SQL(", ").join(map(sql.Identifier, columns))
    )
    params: list = [start, end]
    if event_types:
        query += sql.SQL(" and event_type = any(%s)")
        params.append(list(event_types))
    try:
        with psycopg.connect(dsn, connect_timeout=3) as connection:
            rows = connection.execute(query, params).fetchall()
    except psycopg.Error as exc:
        raise TelemetryReportError("telemetry report read failed") from exc
    return pd.DataFrame(rows, columns=columns)


def _add_date(df: pd.DataFrame) -> pd.DataFrame:
    """Timestamps may arrive as strings or as datetimes in the session time
    zone. Grouping by them as they are splits days silently, so convert to
    UTC datetimes first and derive the UTC calendar date."""
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    df["date"] = df["timestamp"].dt.date
    return df


def _extract(df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    """Turn the given ``tags`` keys into columns; a missing key becomes NaN."""
    return df.join(pd.DataFrame(df["tags"].tolist(), index=df.index, columns=fields))


def _serve(df: pd.DataFrame, keys: list[str]) -> list[dict]:
    """Sorted list of plain dicts, ready for ``json.dumps``."""
    df = df.sort_values(keys).astype({"date": str})
    return df.to_dict(orient="records")


def events_per_day(start: datetime, end: datetime) -> list[dict]:
    """How many events does each service record per day, and which event
    types dominate that day's volume?"""
    df = load_events(["timestamp", "service", "event_type"], start, end)
    df = _add_date(df)
    result = df.groupby(["date", "service", "event_type"]).size().reset_index(name="events")
    result["share"] = (result["events"] / result.groupby("date")["events"].transform("sum")).round(4)
    return _serve(result, ["date", "service", "event_type"])


def error_rate_per_day(start: datetime, end: datetime) -> list[dict]:
    """What share of browser sessions hits at least one frontend error each
    day, per app? A session counts on every UTC day it was active."""
    df = load_events(["timestamp", "event_type", "session_id", "tags"], start, end, SESSION_EVENTS)
    df = _extract(df, ["app"])
    df = df.dropna(subset=["app", "session_id"])
    df["is_error"] = df["event_type"].eq(ERROR_EVENT)
    df = _add_date(df)
    sessions = (
        df.groupby(["date", "app", "session_id"])
        .agg(had_error=("is_error", "any"), errors=("is_error", "sum"))
        .reset_index()
    )
    result = (
        sessions.groupby(["date", "app"])
        .agg(sessions=("had_error", "size"), sessions_with_errors=("had_error", "sum"), errors=("errors", "sum"))
        .reset_index()
    )
    result["error_rate"] = (result["sessions_with_errors"] / result["sessions"]).round(4)
    return _serve(result, ["date", "app"])


def frontend_errors_per_day(start: datetime, end: datetime) -> list[dict]:
    """Where and how does the frontend fail each day: by app, route template
    and error kind, with distinct errors (fingerprints) and affected sessions."""
    df = load_events(["timestamp", "session_id", "tags"], start, end, (ERROR_EVENT,))
    df = _extract(df, ["app", "route_template", "error_kind", "error_fingerprint"])
    df = df.dropna(subset=["app", "route_template", "error_kind"])
    df = _add_date(df)
    result = (
        df.groupby(["date", "app", "route_template", "error_kind"])
        .agg(errors=("tags", "size"), distinct_errors=("error_fingerprint", "nunique"), sessions=("session_id", "nunique"))
        .reset_index()
    )
    return _serve(result, ["date", "app", "route_template", "error_kind"])


def web_vitals_per_day(start: datetime, end: datetime) -> list[dict]:
    """How fast do pages load and respond for real users each day? Mean and
    p75 of each Web Vital per app and route, plus the share rated poor."""
    df = load_events(["timestamp", "tags"], start, end, (VITALS_EVENT,))
    df = _extract(df, ["app", "route_template", "metric", "value", "rating"])
    df = df.dropna(subset=["app", "route_template", "metric", "value"])
    df["value"] = pd.to_numeric(df["value"])
    df["is_poor"] = df["rating"].eq("poor")
    df["unit"] = df["metric"].map(VITAL_UNITS)
    df = _add_date(df)
    result = (
        df.groupby(["date", "app", "route_template", "metric", "unit"])
        .agg(
            samples=("value", "size"),
            mean=("value", "mean"),
            p75=("value", lambda values: values.quantile(0.75)),
            poor_rate=("is_poor", "mean"),
        )
        .reset_index()
        .round({"mean": 3, "p75": 3, "poor_rate": 4})
    )
    return _serve(result, ["date", "app", "route_template", "metric"])


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_report(start: datetime, end: datetime) -> dict:
    """Run every metric over the same ``[start, end)`` period."""
    return {
        "period": {"from": _iso(start), "to": _iso(end)},
        "metrics": {
            "events_per_day": events_per_day(start, end),
            "error_rate_per_day": error_rate_per_day(start, end),
            "frontend_errors_per_day": frontend_errors_per_day(start, end),
            "web_vitals_per_day": web_vitals_per_day(start, end),
        },
    }
