---
name: dd-comparacion-proveedores
description: Compara varios proveedores del Estado paraguayo con datos oficiales de la DNCP - histórico de montos adjudicados por año, tamaño declarado, dependencia de un convocante, modalidades no competitivas, oferente único, adjudicado frente a estimado, contratado, pagado, demora de pago y precios unitarios frente al mercado. Usar cuando pidan comparar proveedores, un ranking, una base comparativa, el histórico de montos o el tamaño de una empresa, o elegir entre oferentes.
---

# Comparación de proveedores

Los datos salen de las **descargas masivas OCDS de la DNCP** (una por año, 2010–2026), cargadas en
una base local; se bajan solo los CSV necesarios (~4 MB por año, no los zips de 80 MB). Fuentes,
tablas y columnas en `reference/datos-dncp-masivo.md`; definición y límites de cada indicador en
`reference/indicadores.md`.

## 1. Preparar los datos (una vez)
- Ver qué hay cargado: `estado_datos_masivos()` (dd-dncp).
- Si falta, el usuario corre: `uv run dd descargar-fuentes --dncp-masivo 2020-2026`
  (adjudicaciones, procesos, contratos y pagos; ~30 s por año).
- Para precios unitarios: agregar `--items <RUC> <RUC> …` (ítems de esos proveedores) o cargar los
  ítems sin filtro para tener una mediana de mercado real (~230 MB por año descomprimido).
- **La cobertura depende de los años cargados**: un proveedor activo desde 2016 se ve incompleto si
  solo se cargó 2022–2026. Decirlo siempre junto a la tabla.

## 2. Comparar
- Un proveedor: `perfil_proveedor(caso_id, ruc, desde, hasta)`.
- Varios (2 a 10): `comparar_proveedores(caso_id, rucs, desde, hasta)` → tabla y Markdown listo.
  Suma tamaño declarado y sanciones de la API (`vigente` ya contempla cautelares).
- Precios: `precios_vs_mercado(caso_id, ruc)` → ítems más caros y más baratos frente a la mediana del
  mismo código de catálogo y unidad, con la cantidad de comparables.
- Sin servidor: `uv run dd comparar RUC RUC … --desde 2022 --salida casos/comparaciones/<nombre>`.
- Usar el mismo período para todos los proveedores comparados.

## 3. Registrar y presentar
- Cada indicador relevante se registra como hallazgo **`contexto`** (A, fuente "DNCP datos masivos
  OCDS", `identificador_que_ata: "RUC …"`, `consulta_id` de la herramienta, URL de verificación
  `…/search/processes?awards.suppliers.id=<RUC>`). No lleva `categoria_alerta`: la comparación no
  entra al semáforo salvo que el criterio del caso lo diga.
- Un valor llamativo (p. ej. 100 % de oferente único, 86 % del monto con un convocante) se presenta
  con los números y los ocid, sin calificarlo. Si coincide con una bandera roja de
  `dd-contrataciones-py`, esa skill decide si se registra como `indicador_ocds_bandera_roja`.
- En la respuesta: la tabla, los años cargados, el período y las advertencias de
  `reference/indicadores.md` que apliquen (moneda, pagos de contratos fuera del período, tamaño autodeclarado).

## Reglas
- Comparar solo entidades resueltas por RUC (ver `dd-resolucion-entidades`); nunca por nombre.
- Un indicador alto no es una irregularidad: rubro, exclusividad o urgencia lo explican a menudo.
- Tamaño de empresa = lo que el proveedor declaró en la DNCP; no hay facturación ni empleados en
  fuentes abiertas de la DNCP. Si se usa otra fuente (balances en la BVA, IPS), es otra consulta con
  su propia evidencia.
