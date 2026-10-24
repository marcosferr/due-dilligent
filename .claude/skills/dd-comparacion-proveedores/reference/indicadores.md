# Indicadores de comparación: definición y límites

Calculados en `src/dd/perfil.py` sobre la base local. Período = año de la fecha de adjudicación (o de
pago, para pagos). Todos los montos suman solo **PYG**; otras monedas se cuentan pero no se suman.

| Indicador | Definición | Límites (decirlos al presentar) |
|---|---|---|
| Adjudicaciones / procesos | Adjudicaciones al RUC y procesos distintos | Solo años cargados |
| Monto adjudicado y por año | Σ monto de adjudicaciones en PYG | En contratos abiertos el monto adjudicado es un máximo, no lo gastado |
| Monto medio por adjudicación | monto total ÷ adjudicaciones en PYG | Sensible a pocas adjudicaciones grandes |
| Primer / último año, años activos | Años con adjudicaciones | El primer año real puede ser anterior a lo cargado |
| Convocantes distintos | Cantidad de convocantes con adjudicaciones | — |
| % del monto con el principal convocante | Monto del mayor convocante ÷ monto total | Proveedores de nicho (un solo cliente posible) lo tienen alto por naturaleza |
| % del monto no competitivo | Monto en modalidades "Contratación Directa" o "Excepción" ÷ total | Incluye excepciones legítimas (exclusividad, urgencia) |
| % oferente único | Procesos competitivos (excluye directa y excepción) con `numberOfTenderers = 1` ÷ procesos competitivos con dato | Muchos procesos no informan cantidad de oferentes |
| Mediana adjudicado / estimado | Solo procesos con una única adjudicación y estimado en PYG | En procesos por lotes no se puede comparar; 1,0 suele indicar monto máximo |
| % por encima del estimado | Procesos comparables con adjudicado > estimado | Idem |
| Contratos / monto contratado | Contratos de las adjudicaciones del período | — |
| Monto pagado | Σ pagos al RUC en el período (SICP y SIAF) | Incluye pagos de contratos firmados antes del período o de años no cargados |
| % pagado de lo contratado | Pagos que se emparejan con contratos del período ÷ monto contratado | Contratos en curso dan valores bajos; adendas o reajustes pueden dar más de 100 % |
| Mediana de días solicitud → pago | Entre `requestDate` y `date` del pago | Mide al pagador (el Estado), no al proveedor |
| Tamaño declarado | `details.size` de la API | Autodeclarado; muchos figuran "Sin categorizar" |
| Sanciones / inhabilitación vigente | Desde la API, con eventos | `vigente` falso si hubo cautelar o rehabilitación |
| Precio vs. mercado | Precio unitario ÷ mediana del mismo código de catálogo, unidad y moneda | La mediana usa solo los ítems cargados; exigir `comparables` ≥ 5; distintas especificaciones bajo un mismo código |

## Ejemplo real (2022–2026)

`casos/comparaciones/itti-competidores/comparacion.md`: ITTI S.A.E., J. Fleischman, Konecta, Roshka y
Data Systems. Muestra, por ejemplo, que el BNF concentra el 54 % del monto de ITTI y que Roshka
tiene el 86 % de su monto con el MITIC. Son datos para comparar, sin calificación.
