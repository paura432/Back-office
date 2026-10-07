# TrackFlow — Project brief

## Identidad y negocio

TrackFlow es una empresa de logística de última milla y gestión de almacenes fundada en 2009 en Los Ángeles. Opera en Estados Unidos y España, con almacenes en Los Ángeles y Zaragoza, unos 130 empleados y alrededor de 9 millones de euros de facturación anual. Guarda inventario de marcas de comercio electrónico, prepara y empaqueta pedidos, los entrega a transportistas y gestiona devoluciones.

**TrackFlow Tech** es la unidad interna creada para construir los sistemas, integraciones y automatizaciones inteligentes que permitan modernizar y escalar la operación. La tecnología está liderada desde Zaragoza por el CTO Andrés Kim y un equipo de siete personas.

## Situación y problemas actuales

La operación está fragmentada y depende de tareas manuales: los dos almacenes usan sistemas de gestión diferentes y no comparten visibilidad de inventario; la recepción de pedidos, el picking y el seguimiento de transportistas requieren trabajo manual; las devoluciones se revisan una por una; la atención consulta documentación dispersa y responde mayoritariamente consultas repetitivas; la gestión comercial y los informes a clientes dependen de hojas de cálculo y consolidaciones manuales; y dirección recibe información semanal tardía.

La arquitectura tecnológica es un patchwork de dos SGA, un ERP de principios de los años 2010, scripts punto a punto poco documentados, bases de datos en dos proveedores cloud y falta de telemetría centralizada. Los fallos se comunican por WhatsApp y desplegar cambios tarda entre una y dos semanas. Estas limitaciones hacen la operación más lenta, propensa a errores y menos rentable.

## Usuarios, responsables y áreas

- **Operaciones de almacén:** Ana Whitfield, dos almacenes y unos 70 operarios; necesita inventario unificado, ingesta de pedidos, dashboard y alertas de stock.
- **Última milla y transportistas:** Carlos Vega y seis coordinadores; trabaja con ocho transportistas en ambos países. Necesita selección, tracking agregado y análisis de rendimiento.
- **Logística inversa:** Sofía Ramos y cinco personas; gestiona devoluciones que representan entre el 18 % y el 25 % del volumen según cliente y país. Necesita reglas, recogida automatizada, inspección asistida y análisis.
- **Atención al cliente:** Valentina Cruz y 15 agentes en Los Ángeles y Zaragoza, para marcas B2B y destinatarios B2C. Necesita tickets unificados, conocimiento consultable, automatización, métricas y soporte multiidioma recomendado.
- **Comercial y relación con clientes:** Miguel Torres, cuatro account managers y cuatro personas de desarrollo de negocio. Necesita perfiles de cuenta, informes, salud y riesgo de renovación, alertas y ayuda comercial.
- **Tecnología:** Andrés Kim y siete personas en Zaragoza. Necesita telemetría y logging centralizados, datos para dashboards, alertas y automatización operativa.
- **Dirección ejecutiva:** el contexto identifica al CEO como Thomas Harry en la descripción organizativa y como Daniel Espinoza en el apartado de necesidades ejecutivas. Se conserva esta discrepancia del contexto sin resolverla: necesita KPIs globales por país, informes automatizados, alertas y consultas en lenguaje natural.

## Objetivos de transformación y roadmap funcional

Los siguientes objetivos son las necesidades descritas por departamento en `CONTEXT.md`; no implican que estén implementados ni fijan un orden de entrega:

1. **Almacenes:** API de inventario en tiempo real por SKU y almacén, ingesta automatizada de pedidos por email, dashboard y alertas de stock bajo.
2. **Transportistas:** recomendación de transportista según destino, peso y urgencia; tracking unificado; portal público de seguimiento; dashboard de rendimiento.
3. **Devoluciones:** aprobación automática configurable por cliente, automatización de recogida y etiquetas, inspección asistida por IA y dashboard de patrones.
4. **Experiencia del cliente:** agente de primera línea para tracking y devoluciones, base de conocimiento semántica para RAG, tickets unificados, dashboard, análisis de sentimiento y soporte multiidioma recomendado.
5. **Comercial:** integración/perfil unificado de CRM, informes PDF automatizados, salud y riesgo de renovación, avisos 90 y 30 días antes del vencimiento, y agente de apoyo a prospectos.
6. **Tecnología:** telemetría y logs centralizados, pipeline de datos para dashboards, monitorización y alertas en tiempo real, documentación técnica asistida y automatización de operaciones.
7. **Dirección:** dashboard ejecutivo en tiempo real con KPIs globales, informe semanal automático los lunes a las 7:00, comparación por país, alertas por umbral y asistente en lenguaje natural.

Los retos de IA expresamente señalados incluyen clasificación visual del estado de productos devueltos, búsqueda semántica de políticas logísticas bilingües, selección explicable de transportistas y agregación de tracking de ocho APIs.

## Fuente de verdad

`CONTEXT.md` es la fuente de verdad de TrackFlow. Este resumen facilita la orientación; ante cualquier conflicto o detalle no recogido aquí, consultar el contexto original. No modificarlo ni inventar hechos de negocio sin autorización.