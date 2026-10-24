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
| Contratos con la UNI | 6 en la muestra (2023–2026): equipos, laboratorio, maquinarias, informática; p. ej. 76.000.000 PYG (08/11/2024), 67.650.000 PYG (16/10/2025), 11.046.000 PYG (13/08/2026) | [444854](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-444854-1) · [462750](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-462750-1) · [484024](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-484024-1) |
| Sanciones | 5 inhabilitaciones (2020–2025, la última del 10/12/2024 al 10/08/2025, incluida una por "incumplimiento contractual") y 3 amonestaciones (la última el 13/02/2026, por inasistencia injustificada) | [proveedor](https://www.contrataciones.gov.py/datos/api/v3/doc/suppliers/4022404-0) |
| Revisado | Las adjudicaciones de la UNI revisadas son **anteriores o posteriores** a cada inhabilitación, no durante | |
| Esperado con el criterio de ejemplo | Sin regla dura; **amarillo o rojo por puntaje**, según cuántas sanciones históricas se registren (severidad 2 cada una) | |

Sirve para probar el puntaje y cómo se presenta un historial sin afirmar irregularidades.

## Otros datos de la muestra

- Proveedores con más adjudicaciones de la UNI: COMPUGRAF INFORMATICA (12; inhabilitación cumplida en 2014),
  ITAPUA COMUNICACIONES S.A. (10), MUEBLES KT S.R.L. (10), AMADEO VIDAL VINADER RUOTI (10),
  SAN BLAS CONSTRUCCIONES S.R.L. (9; inhabilitación en 2012 y amonestaciones).
- DATA SYSTEMS SAECA (7 adjudicaciones; 5 amonestaciones) también compitió contra ITTI S.A.E. en el caso Itti.
- La muestra cubre 200 de 895 procesos: falta recorrer el resto (unas 45 llamadas más) para completar el cruce.

## Siguiente paso sugerido

Abrir con `/due-diligence-proveedores` los casos 1 (control positivo) y 3 (caso trampa), y cargar sus
referencias en `eval/referencia/` con el color esperado: rojo para el 1; para el 3, sin regla dura y
con la medida cautelar registrada.
