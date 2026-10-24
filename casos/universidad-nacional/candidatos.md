# Casos candidatos relacionados con la Universidad Nacional de Itapúa (UNI)

Exploración del 24/10/2026 en la API pública de la DNCP (sin abrir caso todavía). Sirve para elegir
los casos de prueba de `eval/casos.json`: control positivo, caso trampa y proveedor recurrente.

> Documento interno de trabajo. Las sanciones son datos públicos de la DNCP sobre proveedores del
> Estado; no implican conclusión sobre la conducta de nadie. Antes de usar un caso para una
> decisión, correr el due diligence completo y dar al proveedor la posibilidad de responder.

## Cómo se buscó

1. Convocante: **Universidad Nacional de Itapúa (UNI)**, `DNCP-SICP-CODE-237`, con 895 procesos en la DNCP.
   (Hay 47 convocantes con "Universidad Nacional": UNA, UNE, Pilar, Caaguazú y sus facultades.)
2. Muestra: 200 procesos de la UNI → 107 proveedores adjudicados distintos.
3. Sanciones de cada proveedor (`/suppliers/{ruc}`): **39 de 107 tienen alguna sanción**; 3 con
   inhabilitación vigente por fechas.
4. Fechas de adjudicación de los procesos clave (record OCDS) contra los períodos de inhabilitación:
   **no se encontraron adjudicaciones de la UNI dentro de un período de inhabilitación** en lo revisado.

Fuente base: https://www.contrataciones.gov.py/datos/api/v3/doc/search/processes?tender.procuringEntity.name=Universidad+Nacional+de+Itap%C3%BAa

## Candidatos

### 1. Control positivo con empresa: GRUPO BRIO S.A. (RUC 80105432-0) ⭐ recomendado

| Dato | Valor | Fuente |
|---|---|---|
| Contrato con la UNI | Servicio integral de limpieza FACEA, plurianual 2024; adjudicado el 01/07/2024 por 186.000.000 PYG (5 oferentes; estimado 212.490.000) | [record 440131](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-440131-1) |
| Sanción | INHABILITACIÓN de 5 meses, del 02/06/2026 al 02/11/2026, **vigente** | [proveedor](https://www.contrataciones.gov.py/datos/api/v3/doc/suppliers/80105432-0) |
| Esperado con el criterio de ejemplo | **Rojo por regla dura** (`inhabilitacion_dncp_vigente`) | |
| A revisar | Qué convocante la sancionó y por qué (el API no lo dice); si el contrato con la UNI seguía en ejecución durante la inhabilitación | portal DNCP, sección sanciones |

Es persona jurídica, el control positivo más limpio. **Urgente: la inhabilitación vence el
02/11/2026**; después de esa fecha deja de ser control positivo.

### 2. Control positivo de mayor monto: JOSE ANIBAL RIVAS MARTINEZ ("RG Ingeniería y Servicios", RUC 1814281-8)

| Dato | Valor | Fuente |
|---|---|---|
| Contrato con la UNI | Construcción de aulas y escaleras para una filial; licitación, adjudicada el 18/11/2024 por 781.259.532 PYG (4 oferentes; estimado 930.070.424) y una adenda en 2025 (AC-28004-25-260519) | [record 440141](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-440141-1) |
| Sanción | INHABILITACIÓN de **15 meses**, del 04/08/2026 al 04/11/2027, vigente | [proveedor](https://www.contrataciones.gov.py/datos/api/v3/doc/suppliers/1814281-8) |
| A revisar | **Si la sanción proviene de esta obra de la UNI** (incumplimiento) o de otro convocante; estado de la obra y de la adenda | portal DNCP, sanciones y contrato LP-28004-24-247925 |

Es persona física que opera con nombre de fantasía: tratar solo su rol de proveedor.

### 3. Caso trampa: EDGAR BERNARDINO RODRIGUEZ BARRIOS ("Nempre Producciones", RUC 2515412-5)

| Dato | Valor | Fuente |
|---|---|---|
| Contrato con la UNI | Equipos educativos y de comunicación; contratación directa, adjudicada el 27/09/2023 por 32.669.000 PYG (6 oferentes) | [record 425323](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-425323-1) |
| Sanción | INHABILITACIÓN de 2 años por "mala fe", del 16/09/2025 al 16/09/2027: **vigente por fechas pero suspendida**. El Tribunal de Cuentas, 2ª Sala, dictó el A.I. N° 728/25, que suspende los efectos de las Res. DNCP 1908/25 y 2599/25, y la DNCP lo rehabilitó en el SICP el 26/11/2025 | [proveedor](https://www.contrataciones.gov.py/datos/api/v3/doc/suppliers/2515412-5) |
| Esperado | **No** debe dar rojo por regla dura: la sanción está suspendida por una medida cautelar. El juicio contencioso sigue abierto (etapa a verificar) | |

Este caso destapó un defecto: la versión anterior de la herramienta solo miraba fechas y le habría
aplicado la regla dura. Desde este commit `obtener_proveedor` lee los eventos y expone `vigente`
(falso si hubo suspensión o rehabilitación); la prueba está en `tests/test_dncp_mock.py`.

### 4. Proveedor recurrente con historial: HUGO FELIX BENITEZ PERALTA (RUC 4022404-0)

| Dato | Valor | Fuente |
|---|---|---|
| Actividad total | **381 procesos adjudicados** en la DNCP con decenas de convocantes (universidades, ministerios, INC, SENAVE, INTN, etc.) | [procesos por RUC](https://www.contrataciones.gov.py/datos/api/v3/doc/search/processes?awards.suppliers.id=4022404-0) |
| Contratos con la UNI | **9 adjudicaciones entre 2017 y 2026, unos 354 M PYG en total**: 2017 (24,5 M y 6,9 M), 2018 (18,0 M), 2023 (3,0 M), 08/11/2024 (76,0 M), 06/10/2025 (40,8 M), 15/10/2025 (106,0 M), 16/10/2025 (67,7 M), 13/08/2026 (11,0 M) | `datos/benitez-peralta-cruce.json` |
| Sanciones | 5 inhabilitaciones: 19/05–19/08/2020, 29/10/2020–28/02/2021, 08/09–08/12/2022, 29/09/2022–29/01/2023 ("Incumplimiento Contractual") y 10/12/2024–10/08/2025 (8 meses). 3 amonestaciones: 2016, 2021 y 13/02/2026 ("inasistencia sin justificación") | [proveedor](https://www.contrataciones.gov.py/datos/api/v3/doc/suppliers/4022404-0) |
| **Cruce con las inhabilitaciones** | **Ninguna adjudicación cae dentro de un período de inhabilitación.** Se revisó la fecha real de adjudicación (record OCDS) de 59 procesos con 60 adjudicaciones: los 9 de la UNI y todos los de cualquier convocante con período de ofertas entre 270 días antes y el fin de cada inhabilitación | `datos/benitez-peralta-cruce.json` |
| Esperado con el criterio de ejemplo | Sin regla dura (ninguna inhabilitación vigente hoy); **rojo por puntaje** si se registra cada sanción histórica (8 × severidad 2 = 16 ≥ 5) | |

Límites del cruce: quedaron sin revisar 322 procesos, cuyo período de ofertas está lejos de las
inhabilitaciones. Solo podrían caer dentro si tardaron más de 9 meses en adjudicarse. Tampoco se
revisó si había contratos en **ejecución** durante una inhabilitación: la inhabilitación impide
contratar de nuevo, no necesariamente cumplir lo ya firmado. Qué convocante impuso cada sanción no
figura en la API: hay que verlo en el portal de la DNCP.

Sirve para probar el puntaje y cómo se presenta un historial sin afirmar irregularidades.

## Otros datos de la muestra

- Proveedores con más adjudicaciones de la UNI: COMPUGRAF INFORMATICA (12; inhabilitación cumplida en 2014),
  ITAPUA COMUNICACIONES S.A. (10), MUEBLES KT S.R.L. (10), AMADEO VIDAL VINADER RUOTI (10),
  SAN BLAS CONSTRUCCIONES S.R.L. (9; inhabilitación en 2012 y amonestaciones).
- DATA SYSTEMS SAECA (7 adjudicaciones; 5 amonestaciones) también compitió contra ITTI S.A.E. en el caso Itti.
- La muestra cubre 200 de 895 procesos: falta recorrer el resto (unas 45 llamadas más) para completar el cruce.

## Datos crudos (en `datos/`)

| Archivo | Contenido |
|---|---|
| `uni-procesos-muestra.json` | 200 de los 895 procesos de la UNI (resumen compacto de cada uno) |
| `uni-proveedores.json` | Los 107 proveedores adjudicados de la muestra, con cantidad de adjudicaciones |
| `uni-proveedores-sancionados.json` | Los 39 proveedores con sanciones. Se bajó **antes** de la corrección de las cautelares: solo trae `vigente_por_fechas`; para el estado real, volver a consultar con `obtener_proveedor` (que ahora expone `vigente` y los eventos) |
| `benitez-peralta-cruce.json` | Caso 4: sanciones, 60 adjudicaciones con fecha y cruce con las inhabilitaciones |

## Siguiente paso sugerido

Abrir con `/due-diligence-proveedores` los casos 1 (control positivo) y 3 (caso trampa), y cargar sus
referencias en `eval/referencia/` con el color esperado: rojo para el 1; para el 3, sin regla dura y
con la medida cautelar registrada.
