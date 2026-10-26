"""Telemetry contract models built from ``event-schemas.json``.

The JSON file is a copy of ``docs/telemetry/event-schemas.json`` (a test keeps
both identical), so event names, envelope and property allowlists have a single
source of truth. Each event type becomes a closed Pydantic model and each
event of a batch is validated with a discriminated union on ``event_type``.
"""
import json
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, Strict, StringConstraints, TypeAdapter, create_model

CONTRACT = json.loads(Path(__file__).with_name("event-schemas.json").read_text(encoding="utf-8"))
DEFS = CONTRACT["$defs"]
ENVELOPE = CONTRACT["properties"]
SCHEMA_VERSION = CONTRACT["allOf"][0]["then"]["properties"]["schemaVersion"]["const"]
MAX_BATCH_EVENTS = 100

Closed = ConfigDict(extra="forbid", allow_inf_nan=False)


def _iso(parse):
    def check(value: str) -> str:
        parse(value)
        return value
    return AfterValidator(check)


def _resolve(spec: dict) -> dict:
    while "$ref" in spec:
        spec = DEFS[spec["$ref"].rsplit("/", 1)[-1]]
    return spec


def _not_equal(forbidden):
    def check(value):
        if value == forbidden:
            raise ValueError(f"must not be {forbidden!r}")
        return value
    return AfterValidator(check)


def _annotation(spec: dict) -> Any:
    """Translate the JSON Schema subset used by the contract into a Pydantic type."""
    spec = _resolve(spec)
    if "oneOf" in spec:
        return Union[tuple(_annotation(option) for option in spec["oneOf"])]
    if "enum" in spec or "const" in spec:
        return Literal[tuple(spec.get("enum", [spec.get("const")]))]
    kind = spec["type"]
    if kind == "null":
        return type(None)
    if kind == "boolean":
        return Annotated[bool, Strict()]
    bounds = {"ge": spec.get("minimum"), "le": spec.get("maximum"), "gt": spec.get("exclusiveMinimum")}
    extra = [_not_equal(spec["not"]["const"])] if "not" in spec else []
    if kind in ("integer", "number"):
        base = int if kind == "integer" else float
        return Annotated[base, Strict(), Field(**{k: v for k, v in bounds.items() if v is not None}), *extra]
    extra += {"date": [_iso(date.fromisoformat)], "date-time": [_iso(datetime.fromisoformat)]}.get(spec.get("format"), [])
    return Annotated[str, Strict(), StringConstraints(pattern=spec.get("pattern"), max_length=spec.get("maxLength")), *extra]


class EnvelopeBase(BaseModel):
    """Common envelope; ``event_type`` and ``properties`` are set per event."""

    model_config = Closed

    eventId: _annotation(ENVELOPE["eventId"])
    timestamp: _annotation(ENVELOPE["timestamp"])
    sessionId: _annotation(ENVELOPE["sessionId"])
    userId: _annotation(ENVELOPE["userId"])
    schemaVersion: Literal[SCHEMA_VERSION]
    requestId: _annotation(ENVELOPE["requestId"])


def _event_model(event_type: str, spec: dict) -> type[BaseModel]:
    fields = {
        name: (_annotation(prop), ... if name in spec["required"] else None)
        for name, prop in spec["properties"].items()
    }
    properties = create_model(f"{event_type}_properties", __config__=Closed, **fields)
    return create_model(
        event_type,
        __base__=EnvelopeBase,
        event_type=(Literal[event_type], ...),
        properties=(properties, ...),
    )


EVENT_MODELS = {name: _event_model(name, spec) for name, spec in DEFS["events"].items()}
TelemetryEvent = Annotated[Union[tuple(EVENT_MODELS.values())], Field(discriminator="event_type")]


TELEMETRY_EVENT_ADAPTER = TypeAdapter(TelemetryEvent)


class TelemetryBatch(BaseModel):
    """Raw batch sent by clients. Items are validated one by one against
    ``TelemetryEvent`` so an invalid event does not reject the rest."""

    model_config = Closed

    events: list[Any] = Field(max_length=MAX_BATCH_EVENTS)


class TelemetryAck(BaseModel):
    """Outcome of a batch. ``stored`` counts rows inserted by this request;
    events whose ``eventId`` was already stored or repeated in the batch count
    only in ``received`` (``received - stored - rejected``)."""

    received: int = Field(ge=0)
    stored: int = Field(ge=0)
    rejected: int = Field(ge=0)
