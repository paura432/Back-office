"""Parámetros del pipeline de desempeño de negocio que no son secretos.

Van en el código, versionados con ``PIPELINE_VERSION`` (PIPELINE_DESIGN.md
§4.4). Los DSN no: se leen de variables de entorno o de bloques ``Secret`` de
Prefect (ver ``pipeline.py``).
"""
from datetime import date, timedelta

FLOW_NAME = "business-performance"
DEPLOYMENT_NAME = "business-performance-daily"
DEPLOYMENT_PATH = f"{FLOW_NAME}/{DEPLOYMENT_NAME}"
# Diario a las 04:00 UTC. El informe ejecutivo es semanal (lunes a las 07:00,
# CONTEXT.md) y lee los 7 días anteriores: a las 04:00 UTC del lunes el
# domingo UTC lleva 4 horas cerrado y aún queda margen antes de las 07:00
# tanto en Los Ángeles como en Zaragoza. La corrida diaria además recoge cada
# día los eventos tardíos.
DEPLOYMENT_CRON = "0 4 * * *"

PIPELINE_VERSION = "1.0.0"

DEFAULT_WINDOW_DAYS = 7  # corrida automática: los últimos 7 días completos
AUDIT_DAYS = 35  # días cuya huella se compara para detectar eventos tardíos
DEDUPE_LOOKBACK_DAYS = 30  # lectura previa a la ventana para deduplicar
MAX_WINDOW_DAYS = 90  # ventana explícita máxima (CLI, API)
EXPECTED_COUNTRIES = ("US", "ES")  # siempre hay una fila por KPI, día y país

# Clave de pg_try_advisory_lock: una sola corrida a la vez (§6.10).
LOCK_KEY = 7_340_211_601

SOURCE_DSN_ENV = "BUSINESS_PERFORMANCE_SOURCE_DSN"
REPORTING_DSN_ENV = "BUSINESS_PERFORMANCE_REPORTING_DSN"
SOURCE_DSN_BLOCK = "business-performance-source-dsn"
REPORTING_DSN_BLOCK = "business-performance-reporting-dsn"
READ_DSN_ENV = "REPORTING_READ_DATABASE_DSN"  # API: rol con reporting_reader
EVAL_DIR_ENV = "BUSINESS_PERFORMANCE_EVAL_DIR"


class InvalidWindow(ValueError):
    """Ventana de recálculo no válida."""


def resolve_window(window_start: date | None, window_end: date | None, today: date) -> tuple[date, date]:
    """Sin fechas, la ventana por defecto (los últimos 7 días completos). Con
    fechas, ``[window_start, window_end)`` validada: las dos o ninguna, fin
    posterior al inicio, como mucho hasta mañana (hoy incluido) y 90 días."""
    if window_start is None and window_end is None:
        return today - timedelta(days=DEFAULT_WINDOW_DAYS), today
    if window_start is None or window_end is None:
        raise InvalidWindow("window_start and window_end must be given together")
    if window_start >= window_end:
        raise InvalidWindow("window_start must be before window_end")
    if window_end > today + timedelta(days=1):
        raise InvalidWindow("window_end cannot be later than tomorrow (UTC)")
    if (window_end - window_start).days > MAX_WINDOW_DAYS:
        raise InvalidWindow(f"The window cannot exceed {MAX_WINDOW_DAYS} days")
    return window_start, window_end
