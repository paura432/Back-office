# TrackFlow Inventory Manager — Especificación

## Criterios verificables

Cada criterio expresa un contrato observable. Los valores enumerados son cerrados para esta especificación.

### Artículos

- **INV-001 (EARS: Ubicuo)** Todo artículo deberá tener `warehouse` con exactamente uno de estos valores: `los_angeles` o `zaragoza`.
- **INV-002 (EARS: Ubicuo)** Todo artículo deberá exponer `client_name` como parte de sus datos.
- **INV-003 (EARS: Ubicuo)** Todo artículo deberá exponer `sku` como parte de sus datos.
- **INV-004 (EARS: Ubicuo)** Todo artículo deberá exponer `name` como parte de sus datos.
- **INV-005 (EARS: Ubicuo)** Todo artículo deberá tener `category` con exactamente uno de estos valores: `fashion`, `electronics` o `cosmetics`.
- **INV-006 (EARS: Ubicuo)** Todo artículo deberá tener `unit_of_measure` con exactamente uno de estos valores: `unit`, `box` o `kg`.
- **INV-007 (EARS: Ubicuo)** Todo artículo deberá exponer `reorder_point` como parte de sus datos.
- **INV-008 (EARS: Ubicuo)** Todo artículo deberá exponer `created_at`, que representa cuándo se dio de alta.
- **INV-009 (EARS: Dirigido por evento)** Cuando se cree o edite un artículo, el sistema deberá exponer `updated_at` con el momento de esa creación o edición.
- **INV-010 (EARS: Dirigido por evento)** Cuando se dé de alta un artículo, el sistema deberá rechazar un `sku` ya usado por otro artículo del mismo cliente.
- **INV-011 (EARS: Ubicuo)** El sistema deberá permitir que clientes distintos tengan artículos con el mismo `sku` y deberá tratarlos como artículos diferentes.

### Lotes

- **INV-012 (EARS: Ubicuo)** Todo lote deberá referenciar mediante `item_id` al artículo al que pertenece.
- **INV-013 (EARS: Ubicuo)** Todo lote deberá exponer `lot_code` como parte de sus datos.
- **INV-014 (EARS: Ubicuo)** Todo lote deberá exponer `expiry_date` como parte de sus datos.
- **INV-015 (EARS: Ubicuo)** Todo lote deberá exponer `received_at` como parte de sus datos.
- **INV-016 (EARS: Dirigido por evento)** Cuando se dé de alta un artículo de categoría `cosmetics`, el sistema deberá requerir que tenga al menos un lote asociado.
- **INV-017 (EARS: Dirigido por evento)** Cuando se dé de alta un artículo de categoría `fashion` o `electronics`, el sistema deberá permitir que no tenga lotes asociados.
- **INV-018 (EARS: No deseado)** Cuando se asocie un lote a un artículo, el sistema deberá rechazar la asociación si el `item_id` no identifica un artículo existente.

### Movimientos

- **INV-019 (EARS: Ubicuo)** Todo movimiento deberá referenciar mediante `item_id` al artículo cuyo inventario afecta.
- **INV-020 (EARS: Ubicuo)** Todo movimiento deberá exponer `lot_id`, que podrá ser nulo.
- **INV-021 (EARS: Ubicuo)** Todo movimiento deberá tener `movement_type` con exactamente uno de estos valores: `inbound`, `outbound` o `adjustment`.
- **INV-022 (EARS: Ubicuo)** Todo movimiento deberá exponer `quantity` como parte de sus datos.
- **INV-023 (EARS: Dirigido por evento)** Cuando se registre un movimiento de tipo `adjustment`, el sistema deberá requerir `reason`.
- **INV-024 (EARS: Ubicuo)** Todo movimiento deberá exponer `created_at`, que representa cuándo se registró.

### Stock derivado y cálculo

- **INV-025 (EARS: Ubicuo)** El stock disponible de un artículo deberá derivarse exclusivamente del historial de sus movimientos.
- **INV-026 (EARS: Ubicuo)** El sistema no deberá exponer un campo de stock editable en los datos de artículos.
- **INV-027 (EARS: Ubicuo)** El sistema no deberá ofrecer un endpoint cuya finalidad sea editar directamente el stock.
- **INV-028 (EARS: Ubicuo)** El sistema no deberá ofrecer un formulario cuya finalidad sea editar directamente el stock.
- **INV-029 (EARS: Ubicuo)** Ninguna operación deberá modificar el stock directamente, al margen del registro de movimientos.
- **INV-030 (EARS: Ubicuo)** Para cada artículo y almacén, el stock deberá calcularse como la suma de cantidades `inbound`, menos la suma de cantidades `outbound`, más la suma algebraica de cantidades `adjustment`.
- **INV-031 (EARS: Dirigido por evento)** Cuando se registre un movimiento `inbound`, su `quantity` positiva deberá incrementar el stock derivado en esa cantidad.
- **INV-032 (EARS: Dirigido por evento)** Cuando se registre un movimiento `outbound`, su `quantity` positiva deberá reducir el stock derivado en esa cantidad.
- **INV-033 (EARS: Dirigido por evento)** Cuando se registre un movimiento `adjustment`, una `quantity` positiva deberá incrementar el stock derivado y una `quantity` negativa deberá reducirlo por su valor absoluto.

### Rechazos e invariantes de almacén

- **INV-034 (EARS: No deseado)** Cuando un `outbound` deje el stock derivado del artículo por debajo de cero, el sistema deberá rechazar el movimiento.
- **INV-035 (EARS: No deseado)** Cuando se solicite un `outbound` para un `item_id` inexistente, el sistema deberá rechazarlo.
- **INV-036 (EARS: No deseado)** Cuando se solicite un `adjustment` para un `item_id` inexistente, el sistema deberá rechazarlo.
- **INV-037 (EARS: No deseado)** Cuando un movimiento indique un `lot_id` no nulo que no exista, el sistema deberá rechazarlo.
- **INV-038 (EARS: No deseado)** Cuando un movimiento indique un lote que pertenece a un artículo distinto del indicado por `item_id`, el sistema deberá rechazarlo.
- **INV-039 (EARS: No deseado)** Cuando un movimiento afecte a un artículo de categoría `cosmetics`, el sistema deberá exigir un `lot_id` existente y asociado a ese mismo artículo.
- **INV-040 (EARS: Ubicuo)** El sistema deberá calcular y validar el stock de cada almacén por separado; un saldo de `los_angeles` nunca deberá compensar un saldo de `zaragoza`, ni viceversa.

### Señal de reposición

- **INV-041 (EARS: Dirigido por estado)** Mientras el stock derivado de un artículo en su almacén sea menor o igual que su `reorder_point`, el sistema deberá mostrar una señal visible de stock bajo para ese artículo y ese almacén.

### CRUD de artículos

- **INV-042 (EARS: Dirigido por evento)** Cuando se solicite el alta de un artículo con datos válidos, el sistema deberá crear el artículo sin crear ni asignar un saldo de stock directo.
- **INV-043 (EARS: Dirigido por evento)** Cuando se edite un artículo con movimientos registrados, el sistema deberá conservar ese historial, rechazar cambios de `warehouse` que lo reasignen y calcular el stock únicamente a partir de esos movimientos.
- **INV-044 (EARS: Dirigido por evento)** Cuando se solicite el listado de artículos, el sistema deberá permitir consultar cada artículo con su stock derivado y su almacén, sin combinar saldos entre almacenes.
- **INV-045 (EARS: No deseado)** Cuando se solicite la baja de un artículo con movimientos registrados, el sistema deberá rechazarla si implica eliminar o alterar ese historial.
- **INV-046 (EARS: Dirigido por evento)** Cuando se solicite la baja de un artículo sin movimientos registrados, el sistema deberá dejar de incluirlo en el listado de artículos.

### Datos semilla

- **INV-047 (EARS: Dirigido por estado)** En el conjunto de datos semilla disponible, deberán existir al menos 15 artículos.
- **INV-048 (EARS: Dirigido por estado)** En el conjunto de datos semilla disponible, deberán existir artículos en `los_angeles` y en `zaragoza`.
- **INV-049 (EARS: Dirigido por estado)** En el conjunto de datos semilla disponible, deberán estar representados al menos 3 `client_name` distintos.
- **INV-050 (EARS: Dirigido por estado)** En el conjunto de datos semilla disponible, deberán estar representadas las tres categorías: `fashion`, `electronics` y `cosmetics`.
- **INV-051 (EARS: Dirigido por estado)** En el conjunto de datos semilla disponible, deberán existir al menos 3 artículos `cosmetics`, cada uno con al menos un lote asociado.
- **INV-052 (EARS: Dirigido por estado)** En el conjunto de datos semilla disponible, deberá existir al menos un lote cuya `expiry_date` sea anterior a la fecha actual.
- **INV-053 (EARS: Dirigido por estado)** En el conjunto de datos semilla disponible, deberán existir al menos 2 artículos cuyo stock derivado sea menor o igual a su `reorder_point`.
- **INV-054 (EARS: Dirigido por estado)** El historial de movimientos de los datos semilla deberá incluir al menos un movimiento de cada tipo: `inbound`, `outbound` y `adjustment`.
- **INV-055 (EARS: Dirigido por estado)** El historial de movimientos de los datos semilla deberá incluir al menos un `adjustment` cuyo `reason` sea `return_restock`.

## Trazabilidad de criterios

| ID | Tipo EARS | Comportamiento verificable |
|---|---|---|
| INV-001 | Ubicuo | `warehouse` solo acepta `los_angeles` o `zaragoza`. |
| INV-002 | Ubicuo | El artículo expone `client_name`. |
| INV-003 | Ubicuo | El artículo expone `sku`. |
| INV-004 | Ubicuo | El artículo expone `name`. |
| INV-005 | Ubicuo | `category` solo acepta `fashion`, `electronics` o `cosmetics`. |
| INV-006 | Ubicuo | `unit_of_measure` solo acepta `unit`, `box` o `kg`. |
| INV-007 | Ubicuo | El artículo expone `reorder_point`. |
| INV-008 | Ubicuo | El artículo expone `created_at` como momento de alta. |
| INV-009 | Dirigido por evento | Alta o edición refleja el momento en `updated_at`. |
| INV-010 | Dirigido por evento | Se rechaza SKU repetido dentro del mismo cliente. |
| INV-011 | Ubicuo | Clientes distintos pueden compartir SKU y sus artículos son distintos. |
| INV-012 | Ubicuo | El lote identifica su artículo mediante `item_id`. |
| INV-013 | Ubicuo | El lote expone `lot_code`. |
| INV-014 | Ubicuo | El lote expone `expiry_date`. |
| INV-015 | Ubicuo | El lote expone `received_at`. |
| INV-016 | Dirigido por evento | Un artículo cosmetics requiere al menos un lote. |
| INV-017 | Dirigido por evento | Fashion y electronics pueden existir sin lotes. |
| INV-018 | No deseado | Se rechaza asociar un lote a un artículo inexistente. |
| INV-019 | Ubicuo | El movimiento identifica el artículo mediante `item_id`. |
| INV-020 | Ubicuo | `lot_id` está presente y puede ser nulo. |
| INV-021 | Ubicuo | `movement_type` solo acepta `inbound`, `outbound` o `adjustment`. |
| INV-022 | Ubicuo | El movimiento expone `quantity`. |
| INV-023 | Dirigido por evento | `adjustment` requiere `reason`. |
| INV-024 | Ubicuo | El movimiento expone `created_at`. |
| INV-025 | Ubicuo | Todo stock disponible deriva únicamente de movimientos. |
| INV-026 | Ubicuo | No existe campo de stock editable en artículos. |
| INV-027 | Ubicuo | No existe endpoint para editar stock directamente. |
| INV-028 | Ubicuo | No existe formulario para editar stock directamente. |
| INV-029 | Ubicuo | No hay operaciones de modificación directa del stock. |
| INV-030 | Ubicuo | Stock = inbound − outbound + ajustes algebraicos firmados. |
| INV-031 | Dirigido por evento | Cantidad inbound positiva incrementa stock. |
| INV-032 | Dirigido por evento | Cantidad outbound positiva reduce stock. |
| INV-033 | Dirigido por evento | Ajuste positivo incrementa y negativo decrementa. |
| INV-034 | No deseado | Se rechaza outbound que deje stock menor que cero. |
| INV-035 | No deseado | Se rechaza outbound de un artículo inexistente. |
| INV-036 | No deseado | Se rechaza adjustment de un artículo inexistente. |
| INV-037 | No deseado | Se rechaza `lot_id` no nulo inexistente. |
| INV-038 | No deseado | Se rechaza lote perteneciente a otro artículo. |
| INV-039 | No deseado | Todo movimiento cosmetics exige lote válido del mismo artículo. |
| INV-040 | Ubicuo | No se compensa stock entre almacenes. |
| INV-041 | Dirigido por estado | Stock igual o inferior al reorder point muestra señal por artículo y almacén. |
| INV-042 | Dirigido por evento | Alta crea artículo sin asignar stock directo. |
| INV-043 | Dirigido por evento | Edición conserva los movimientos, no los reasigna a otro almacén y mantiene el stock derivado. |
| INV-044 | Dirigido por evento | Listado muestra artículos y stock derivado sin mezclar almacenes. |
| INV-045 | No deseado | La baja no puede eliminar ni alterar historial de artículos con movimientos. |
| INV-046 | Dirigido por evento | La baja de artículo sin movimientos lo retira del listado. |
| INV-047 | Dirigido por estado | Hay al menos 15 artículos semilla. |
| INV-048 | Dirigido por estado | Los seeds cubren ambos almacenes. |
| INV-049 | Dirigido por estado | Los seeds cubren al menos 3 clientes. |
| INV-050 | Dirigido por estado | Los seeds cubren las 3 categorías. |
| INV-051 | Dirigido por estado | Hay al menos 3 artículos cosmetics con lote. |
| INV-052 | Dirigido por estado | Hay al menos un lote expirado. |
| INV-053 | Dirigido por estado | Hay al menos 2 artículos en o bajo reorder point. |
| INV-054 | Dirigido por estado | El historial incluye inbound, outbound y adjustment. |
| INV-055 | Dirigido por estado | Hay un adjustment con `reason` `return_restock`. |