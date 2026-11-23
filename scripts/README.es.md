# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## `train_sales_forecast.py`

Entrena y evalúa el pronóstico de ingresos mensuales (Random Forest con 2016-2023, probado sobre 2024-2025) y escribe métricas, predicciones y gráficos en `data/eval/sales_forecast/`. Las dependencias están declaradas dentro del script (metadatos inline, gestionados con `uv add --script`) y fijadas en `train_sales_forecast.py.lock`, así que no necesita un `pyproject.toml` en la raíz ni `pip`. Se ejecuta desde la raíz del repositorio, sin parámetros:

```sh
uv run scripts/train_sales_forecast.py
```

La elección del algoritmo está justificada en la cabecera del script; los resultados y la explicación de las métricas, en `data/eval/sales_forecast/README.md`.
