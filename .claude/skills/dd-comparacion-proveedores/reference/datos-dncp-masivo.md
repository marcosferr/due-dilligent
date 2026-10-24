# Datos de la DNCP para comparar proveedores

Verificado contra las fuentes el 24/10/2026.

## Descargas masivas OCDS (por año)

`https://www.contrataciones.gov.py/images/opendata-v3/final/ocds/<año>/<paquete>.zip`, años 2010–2026,
actualizados a diario. Licencia CC BY 4.0. Son CSV aplanados con OCDS Flatten Tool.

| Paquete | Tamaño (2024–2026) | CSV que usa el sistema | Otros CSV disponibles |
|---|---|---|---|
| `awa-masivo.zip` (adjudicaciones) | ~65–80 MB | `records.csv` (procesos), `awards.csv`, `awa_suppliers.csv`; opcional `awa_items.csv` (precios; 21 MB comprimido / 232 MB) | `awa_documents`, `awa_ite_attributes` (marca, procedencia), `awa_ite_additionalClassific` (UNSPSC), `awa_ite_subItems` |
| `con-masivo.zip` (contratos) | ~40 MB | `contracts.csv`, `con_imp_transactions.csv` (pagos) | `con_amendments` (adendas), `con_guarantees`, `con_imp_purchaseOrders`, `con_imp_milestones` (entregables; 4,3 GB), `con_imp_tra_finantialObliga` (facturas), `con_imp_tra_fin_retentions`, `con_imp_fin_breakdown` (presupuesto), `con_imp_reportedPayment` |
| `ten-masivo.zip` (licitaciones) | ~100 MB | — | oferentes de cada proceso (para tasa de éxito: futuro) |
| `pla-masivo.zip` (planificación) | ~7 MB | — | presupuesto planificado |
| `masivo.zip` (todo) | ~245 MB | — | — |

**Cómo se baja:** `src/dd/masivo.py` lee con HTTP de rango el índice del zip y solo los CSV
necesarios (~4 MB por año). Un año completo (adjudicaciones + contratos + pagos) carga en ~30 s.

**Uniones:** todas las tablas comparten `compiledRelease/id` (el release del proceso).
Adjudicación ↔ proveedor por `compiledRelease/awards/0/id`; adjudicación ↔ contrato por
`compiledRelease/contracts/0/awardID`; pago ↔ contrato por `compiledRelease/contracts/0/id`; el RUC
del proveedor está en `awards/0/suppliers/0/id` y en `transactions/0/payee/id` (`PY-RUC-…`).

**Solapamiento:** el paquete de un año trae registros de años anteriores (el de 2026 tiene
adjudicaciones de 2024). La base local deduplica por id de adjudicación, contrato y pago.

## Columnas cargadas (base `var/fuentes/dncp_masivo.sqlite`)

| Tabla | Columnas | De |
|---|---|---|
| `proceso` | ocid, título, convocante, modalidad (`procurementMethodDetails`), categoría, monto estimado, cantidad de oferentes (`numberOfTenderers`), inicio y duración del período de ofertas, estado | `records.csv` |
| `adjudicacion` | id, fecha, monto, moneda, estado | `awards.csv` |
| `adjudicado` | id de adjudicación, RUC, nombre | `awa_suppliers.csv` |
| `contrato` | código, adjudicación, firma, período, monto, estado | `contracts.csv` |
| `pago` | id, contrato, fecha de pago, fecha de solicitud, monto, pagador, RUC del beneficiario, sistema (SICP/SIAF) | `con_imp_transactions.csv` |
| `item` | adjudicación, descripción, código de catálogo nivel 5, cantidad, unidad, precio unitario | `awa_items.csv` |

## API v3 (complementa: un proveedor por llamada, 15/min sin token)

| Endpoint | Dato para comparar |
|---|---|
| `/suppliers/{ruc}` | `details.size` (Micro, Pequeña, Mediana, Grande, Sin categorizar; autodeclarado), `legalEntityTypeDetail`, categorías, `cantidad_adjudicaciones`, sanciones con eventos |
| `/ocds/record/{ocid}` → `parties[].details.scale` | escala del proveedor en ese proceso (p. ej. `sme`) |
| `/contracts/{id}` | pagos con factura y retenciones, órdenes de compra, entregables (fecha comprometida y cumplida), garantías |
| `/search/awarded-items/{codigo}/amount/{anio}` | ítems adjudicados por código de catálogo y año (referencia de precios) |

## Fuera de la DNCP (no integrado)

| Fuente | Dato | Estado |
|---|---|---|
| DNIT (listado de RUC) | estado del RUC, RUC anterior | integrado (`dnit_buscar_ruc`); no informa tamaño ni facturación |
| Bolsa de Valores de Asunción / Superintendencia de Valores | balances de emisoras (S.A.E., S.A.E.C.A.) | no verificado; única fuente abierta posible de facturación real |
| IPS | cantidad de empleados | no verificado si hay consulta pública |
| MIC – registro MIPYMES | categoría oficial de tamaño | no verificado |
