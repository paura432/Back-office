# TrackFlow Incident Manager — Backend API

## Estructura

```
services/api/
├── README.md
├── pyproject.toml
├── main.py              # FastAPI app entrypoint
├── database.py          # SQLite connection + init_db
├── seed.py              # Data seeder (12+ incidents)
├── schemas/
│   └── __init__.py      # Pydantic models + validations
├── models/
│   └── __init__.py      # Row helpers
├── routers/
│   ├── __init__.py
│   └── incidents.py     # CRUD + transitions + audit endpoints
└── tests/
    └── test_incidents.py
```

## Requisitos

- Python ≥ 3.11
- uv

## Instalación

```bash
cd services/api
uv sync
```

## Ejecutar backend

```bash
cd services/api
uv run uvicorn main:app --reload --port 8000
```

API disponible en: http://localhost:8000

## Ejecutar seeds

Los seeds se ejecutan automáticamente al arrancar si no se han aplicado antes.

Para ejecutarlos manualmente:

```bash
cd services/api
uv run seed.py
```

Son **idempotentes**: si ya se ejecutaron, no duplican datos.

## Tests

```bash
cd services/api
uv run pytest tests/ -v
```

## Variables de entorno

| Variable | Valor por defecto | Propósito |
|---|---|---|
| `INCIDENT_DB_PATH` | `incidents.db` (en `services/api/`) | Ruta de la base de datos SQLite |