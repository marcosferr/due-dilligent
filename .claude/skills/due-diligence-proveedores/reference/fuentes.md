# Fuentes, modo de acceso y confiabilidad

## Escala de confiabilidad

| Nivel | Qué es | Ejemplos | Peso en el puntaje |
|---|---|---|---|
| A | Fuente oficial primaria sobre la propia entidad | DNCP API (proveedor por RUC, sanciones), DNIT, registro oficial de empresas, sentencia publicada | 1.0 |
| B | Fuente oficial secundaria o agregador reconocido que cita la fuente oficial | OpenSanctions, OFAC, SAM.gov, OpenCorporates, Contraloría (PDF) | 0.7 |
| C | Prensa, directorios, lo que dice la propia empresa | ABC Color, La Nación, AmCham, sitio de la empresa, LinkedIn | 0.4 |
| D | Sin verificar o de autoría desconocida | Foros, redes sociales anónimas, blogs sin firma | 0 (solo genera tarea de verificación) |

Los datos aportados por el equipo sin verificar (p. ej. el directorio de AmCham) entran como C
hasta confirmarlos en una fuente A o B.

## Fuentes y cómo se consultan

| Fuente | Herramienta | Modo | Límites y notas |
|---|---|---|---|
| DNCP API v3 (OCDS) | `dd-dncp.*` | api | Sin token: 15 llamadas/min. `buscar_proveedores(nombre=)` busca en el nombre de fantasía; la razón social se busca con `buscar_procesos(nombre_proveedor=)`. 404 = "No encontrado". |
| DNCP datos abiertos (CSV) | descarga manual | descarga | https://www.contrataciones.gov.py/datos/data para análisis masivo |
| DNIT listado de RUC | `dnit_buscar_ruc` | descarga | `uv run dd descargar-fuentes --dnit`. Estados: ACTIVO, CANCELADO, SUSPENSION TEMPORAL, BLOQUEADO. La constancia individual es solo web. |
| OpenSanctions (sanctions + debarment, incluye Banco Mundial y SAM) | `screen_entidad`, `screen_persona` | descarga | CC BY-NC 4.0: uso no comercial. API con clave solo para periodismo/ONG/academia. |
| OFAC SDN | `screen_entidad`, `screen_persona` | descarga | Gratis. |
| SAM.gov Exclusions | `sam_exclusiones` | api | Requiere `SAM_API_KEY`; 10 consultas/día. Solo si la entidad contrata con el gobierno de EE. UU. |
| OpenCorporates | `registro_extranjero` | api | Requiere `OPENCORPORATES_API_TOKEN` (gratis solo con licencia abierta share-alike). |
| Registro de Nevada | `registro_solo_web("us_nv")` + `capturar(usar_navegador=True)` | navegador | Solo web; portal en transición: verificar URL. Agente registrado ≠ dueño. |
| Registros Públicos (PY) | `registro_solo_web("py_registros_publicos")` | brecha | Trámite presencial o con usuario. |
| Poder Judicial | `registro_solo_web("py_poder_judicial")` | navegador / brecha | Sin API. Navegador solo si los términos lo permiten. |
| Contraloría (declaraciones juradas) | web + `capturar` | web | PDF: extraer texto, citar página. |
| Prensa y web | WebSearch / WebFetch + `registrar_consulta` + `capturar` | web | Respetar términos de uso. Una nota de prensa es C. |
| Directorios con JavaScript (AmCham) | `capturar(url, usar_navegador=True)` | navegador | El listado de AmCham no se lee sin navegador. |
| RDAP/WHOIS del dominio | WebFetch a `https://rdap.org/domain/<dominio>` + `registrar_consulta` | web | Muchos registros ocultan al titular: anotar como brecha si es así. |
