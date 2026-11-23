# Carpeta `data/eval`

Esta carpeta está orientada a **evaluación y validación**: datasets de evaluación, “golden sets”, resultados de experimentos, métricas, y artefactos usados para medir calidad de modelos, RAG, agentes o pipelines.

- **Propósito principal**: centralizar los insumos y salidas de evaluación para asegurar mejoras medibles a lo largo de los hitos del proyecto.
- **Recomendación**: documenta cada set de evaluación (qué mide, cómo se construyó, criterios de éxito) y evita incluir datos sensibles; si es necesario, usa datos sintéticos o anonimizados.

## Evaluación del pronóstico de ventas

- `evaluation_report.md`: evaluación técnica del pronóstico de ingresos (`scripts/train_sales_forecast.py`) antes de staging: validación cruzada temporal, curva de aprendizaje, MAE/RMSE de entrenamiento y validación, diagnóstico (overfitting moderado) y la acción correctiva propuesta. Las cifras salen de `scripts/evaluate_sales_forecast.py`.
- `learning_curve.png`: error de entrenamiento y de validación según crece la ventana de entrenamiento (validación en 2023).
- `sales_forecast/`: resultados del pronóstico sobre los años de prueba 2024-2025 (`README.md`) y el detalle de la validación cruzada (`evaluation_cv.json`).
