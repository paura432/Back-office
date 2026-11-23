# Pronóstico de ingresos mensuales de TrackFlow

Modelo de regresión que predice `revenue_eur` (fila `consolidated`) de `data/raw/trackflow_sales.csv`, según el BRIEFING de *sales forecasting* de TrackFlow. Responde al ticket de Finanzas: si con el histórico se pueden predecir las ventas de los próximos meses con un error aceptable antes de construir el dashboard ejecutivo.

**Respuesta corta:** sí. En 2024 y 2025, que el modelo no vio al entrenar, el error típico es de unos 46.000 EUR al mes, el 3,6 % del ingreso mensual medio. Eso es casi la mitad del error de repetir el mismo mes del año anterior. 22 de los 24 meses reales caen dentro del rango de variabilidad que da el modelo.

## Cómo se reproduce

Desde la raíz del monorepo:

```sh
uv run scripts/train_sales_forecast.py
uv run --project data/pipelines python -m pytest tests/pipelines/test_sales_forecast.py
```

El script tarda unos segundos, usa `random_state=42` y reescribe los archivos de esta carpeta:

| Archivo | Qué es |
|---|---|
| `metrics.json` | Split, modelo, importancia de features, métricas de prueba del modelo y de dos referencias simples, banda, PSI y descomposición |
| `predictions.csv` | Los 24 meses de prueba: real, predicción mes a mes con su banda del 80 %, predicción a 24 meses vista y el mismo mes del año anterior |
| `forecast_vs_actual.png` | Predicción con su rango de variabilidad frente a los datos reales de 2024-2025 |
| `decomposition.png` | Tendencia, estacionalidad y residuo de 2016-2023 |

## Datos y split

- 120 meses de 2016-01 a 2025-12. `load_sales` comprueba las columnas del BRIEFING, que no falte ningún mes, que todos los ingresos sean positivos y que no haya nulos en el target. El archivo no tiene nulos; si faltara un ingreso, se rechaza en vez de inventarlo.
- **Entrenamiento:** los primeros 8 años, 2016-2023. 2016 solo aporta historia para el lag de 12 meses, así que el modelo aprende de 84 meses (2017-2023).
- **Prueba:** los 2 años más recientes, 2024-2025 (24 meses). El corte es por fecha. `tests/pipelines/test_sales_forecast.py` comprueba que los dos conjuntos no comparten meses y que multiplicar por 10 las ventas de 2024-2025 no cambia ninguna fila de entrenamiento.

## Descomposición frente al BRIEFING

Descomposición multiplicativa (`statsmodels.tsa.seasonal.seasonal_decompose`, periodo 12) de los años de entrenamiento:

| Patrón del BRIEFING | Lo que muestra la serie (2016-2023) |
|---|---|
| Noviembre-diciembre, +25-35 % respecto al promedio | Noviembre +27,0 % y diciembre +23,9 % sobre la media de los meses normales |
| Febrero, −10-15 % | −11,2 % |
| Resto de meses, ±5 % | Entre −2,9 % y +4,7 % |
| Crecimiento anual que alterna entre 3 % y 9 % | Alterna cada año, pero entre 1,8 % y 10,1 % (2017: 9,6; 2018: 1,8; … 2023: 10,1; 2024: 4,0; 2025: 7,9) |

El patrón coincide con el BRIEFING, con dos matices. Diciembre queda un punto por debajo del rango. El crecimiento anual medido con los ingresos sale algo más extremo que el 3-9 % descrito, probablemente porque el ruido mensual se suma a cada año. La comparación es «respecto a los meses normales» porque los índices de la descomposición están referidos a la media de todo el año, que ya incluye el pico. Frente a esa media, los valores son +23,0 %, +19,9 % y −14,1 %.

## Features

Todos se calculan en `data/process/sales_forecast_features.py` solo con meses anteriores al que se predice:

- **Lags:** `lag_1`, `lag_2`, `lag_3` y `lag_12`, el mismo mes del año anterior.
- **Rolling:** `rolling_mean_3`, `rolling_mean_12` y `rolling_std_12`, calculados con `shift(1)` antes de `rolling()`.
- **Calendario:** `month_sin` y `month_cos`, una codificación cíclica del mes en la que diciembre y enero quedan juntos.

Un test comprueba que `lag_1` de la fila `t` es el valor real de `t-1`. Otro comprueba que alterar el mes `t` y los siguientes no cambia ningún feature de los meses anteriores. Además, se introdujo a propósito una fuga en el código (una media rodante sin `shift(1)`, un lag desplazado) para verificar que los tests fallan.

**Escalado.** Las columnas en euros se dividen entre `rolling_mean_12`, la media de los 12 meses anteriores, y el modelo predice ese mismo cociente para el mes siguiente. Hace falta porque un Random Forest no puede predecir valores mayores que los que vio al entrenar, y en 2024-2025 la facturación ya está por encima de todos los meses de 2016-2023. El PSI de `revenue_eur` entre entrenamiento y prueba es 5,9, un desplazamiento enorme. En valores relativos el modelo aprende la forma del año (pico, valle, ritmo reciente), que sí se repite.

`shipments_processed` y `avg_revenue_per_shipment_eur` no entran en el modelo. Su producto es `revenue_eur`, así que los del mismo mes serían el target disfrazado, y los de meses anteriores no aportan nada que no esté ya en los lags de ingresos.

## Por qué Random Forest

La justificación completa está en la cabecera de `scripts/train_sales_forecast.py`. En resumen:

- **Tamaño de datos:** son 84 filas de entrenamiento. Random Forest promedia árboles independientes y es estable con parámetros casi por defecto (500 árboles, `min_samples_leaf=2`). XGBoost corrige errores árbol a árbol y, con tan pocos datos, se ajusta al ruido si no se tunean con cuidado la tasa de aprendizaje, la profundidad y la regularización.
- **Tiempo de ajuste:** con 84 meses no hay margen para una validación fiable en la que tunear XGBoost. Random Forest da además el error fuera de bolsa (OOB), que usamos para la banda de variabilidad sin tocar los años de prueba.
- **Explicabilidad:** a Finanzas se le explica como cientos de árboles que miran los meses anteriores y el mes del año y cuyo resultado se promedia. El feature que más pesa es `lag_12_rel` (89 % de la importancia): el mismo mes del año anterior, relativo al nivel reciente. Es lo mismo que Ana y Carlos ya hacen a mano cada año.

## Resultados sobre 2024-2025

**Predicción mes a mes:** cada mes se predice con los meses reales anteriores, como pasaría al cerrar cada mes, sin reentrenar.

| Métrica | Valor | Qué mide |
|---|---|---|
| **MSE** | 2,14 × 10⁹ EUR² | Media del error al cuadrado. Penaliza mucho los errores grandes, pero su unidad (EUR²) no se puede leer directamente |
| RMSE | 46.241 EUR, **3,56 % del ingreso mensual medio** (1,30 M EUR) | Raíz del MSE, en euros. Es la forma de contarle el MSE a Finanzas: «nos solemos equivocar en unos 46.000 EUR al mes» |
| MAE / MAPE | 40.401 EUR / 3,13 % | Error medio absoluto y en porcentaje del mes real |
| Sesgo | +3.774 EUR | Media de predicción − real: el modelo sobreestima ligeramente |
| **PSI** del target escalado | 0,16 | Cuánto ha cambiado la distribución de lo que el modelo predice (ingreso relativo al nivel reciente) entre entrenamiento y prueba. Por debajo de 0,1 es estable, entre 0,1 y 0,25 es un cambio moderado y por encima de 0,25, grande |
| **Gini** normalizado | 0,918 | Si el modelo ordena los meses de mayor a menor ingreso como la realidad (1 = orden perfecto). Es lo que Thomas necesita para distinguir un febrero normal de una caída atípica |
| **K2 Score** | K² = 0,23, p = 0,89 | Test de normalidad de D'Agostino (K²) sobre los residuos, la definición de la solución de referencia del syllabus. Un p alto indica que no hay evidencia de errores sesgados o con colas raras |
| Cobertura de la banda del 80 % | 22 de 24 meses (92 %) | Cuántos meses reales caen dentro del rango de variabilidad |

**Comparación con alternativas simples** sobre los mismos 24 meses:

| Predicción | RMSE (% del ingreso medio) | MAPE | Gini |
|---|---|---|---|
| Random Forest, mes a mes | 3,56 % | 3,13 % | 0,918 |
| Random Forest, a 24 meses vista (todo 2024-2025 desde diciembre de 2023) | 3,16 % | 2,70 % | 0,956 |
| Mismo mes del año anterior | 7,17 % | 5,99 % | 0,851 |
| Mismo mes del año anterior × crecimiento de los últimos 12 meses | 5,01 % | 4,34 % | 0,794 |

En la predicción a 24 meses vista, cada mes predicho ocupa el lugar del dato real en los lags del siguiente. Es el escenario de presupuestar los dos años enteros a cierre de 2023. Sale incluso algo mejor que la predicción mes a mes porque no arrastra el ruido de cada mes real a través de `lag_1`. Con 24 meses, esa diferencia no permite decir que uno sea mejor que el otro.

**Dónde falla.** Los dos meses fuera de la banda son enero de 2024, sobreestimado un 8,7 % (1,16 M real frente a 1,26 M predicho), y marzo de 2025, subestimado un 6,9 %. El resto de errores no pasa del 5 %.

## Por qué un MSE bajo no basta

- **No dice si el error es aceptable.** En EUR² no tiene una escala intuitiva: hay que pasarlo a euros (RMSE) y compararlo con el ingreso medio y con una predicción trivial. Aquí el modelo mejora claramente a «el mismo mes del año pasado».
- **Puede venir de memorizar.** Un error bajo en los años de entrenamiento no prueba nada. Por eso todas las métricas son sobre 2024-2025, que el modelo no vio, y los tests vigilan que no haya fuga.
- **No dice si el modelo ordena bien los meses (Gini)**, ni si los errores están sesgados (sesgo y K2), ni si los datos nuevos se parecen a los de entrenamiento (PSI). Un MSE bajo puede convivir con un modelo que siempre sobreestima o que confunde una temporada baja normal con una anómala.
- **Es un único número optimista.** Por eso la predicción va con su banda y con cuántos meses reales caen dentro.

## PSI y deriva entre entrenamiento y prueba

PSI con 5 cortes por cuantiles de entrenamiento (`metrics.json` → `psi_train_vs_test`):

| Variable | PSI | Lectura |
|---|---|---|
| `revenue_eur` (nivel) | 5,95 | Cambio enorme, esperado: la empresa crece. Es el motivo del escalado |
| Target escalado (`target_rel`) | 0,16 | Moderado |
| `lag_12_rel`, el feature principal | 0,13 | Moderado |
| `lag_2_rel`, `lag_3_rel` | 0,02 / 0,05 | Estable |
| `rolling_std_12_rel` | 0,52 | Grande: la volatilidad relativa de los últimos 12 meses es distinta en 2024-2025 |
| `avg_revenue_per_shipment_eur` (no entra en el modelo) | 0,48 | Grande: el ingreso por envío de 2024-2025 cae en otros tramos que en entrenamiento |

Con solo 24 meses de prueba (unos 5 por tramo), el PSI es ruidoso: sirve para señalar qué vigilar, no como alarma. El BRIEFING pide usarlo para detectar si cambió la mezcla de volumen entre Los Ángeles y Zaragoza. **No se puede medir con este dataset**, porque solo trae la fila `consolidated` y no hay filas por mercado. El cambio en el ingreso por envío podría tener que ver con esa mezcla, pero con estos datos no se puede afirmar.

## Evaluación previa a staging

La validación cruzada temporal, la curva de aprendizaje y el diagnóstico de este modelo (overfitting moderado y acción correctiva propuesta) están en [`../evaluation_report.md`](../evaluation_report.md). El detalle numérico está en `evaluation_cv.json`, que escribe `scripts/evaluate_sales_forecast.py`.

## Límites

- 84 meses de entrenamiento y 24 de prueba: las métricas tienen incertidumbre. Una validación cruzada temporal daría una estimación más robusta.
- La banda sale de los errores fuera de bolsa en entrenamiento. En prueba cubrió el 92 % de los meses, algo más que el 80 % nominal, así que es algo conservadora.
- El dataset es una serie generada con un patrón conocido (BRIEFING §4). Con datos reales habría que vigilar eventos que la serie no tiene, como la pérdida de un cliente grande o cambios de tarifa.
