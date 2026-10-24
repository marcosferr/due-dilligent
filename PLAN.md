# Plan de implementación: sistema agéntico de due diligence de proveedores

Hackatón UNI · Desafío 3 · Oct 2026

Este plan baja a tareas el documento de diseño ("Sistema agéntico de Due Diligence de proveedores")
y deja registro de lo que ya está construido en el repositorio, lo que falta y lo que necesita una
decisión o un insumo del equipo.

## 1. Decisiones de alcance (confirmadas)

| Tema | Decisión |
|---|---|
| Interfaz de la demo | **Claude Code + skills**: el repositorio trae `.mcp.json`, `.claude/skills/` y `.claude/agents/`; se corre `/due-diligence-proveedores <proveedor>` en la terminal. Sin API key de Anthropic por ahora. |
| Formato de la ficha | **Markdown + HTML** generados desde la base (Word queda para después). |
| Criterio del semáforo | El **ejemplo** del documento de diseño como placeholder (`config/criterio_semaforo.json`, versión `ejemplo-0.1`). La UNI lo reemplaza. |
| DNCP | API pública v3 **sin token** (15 llamadas/min, con limitador propio) y **modo mock** con datos ficticios para demos sin red. |
| Insumos del equipo | Todavía no hay token DNCP, guía con la ronda manual ni criterio UNI: todo queda parametrizado para cargarlo después. |

## 2. Arquitectura

```text
Usuario en Claude Code
  └─ skill due-diligence-proveedores (orquestador)
       ├─ 1. crear_caso → congela el criterio (versión + SHA-256)
       ├─ 2. dd-resolucion-entidades → una entidad legal por identificador (S.A. ≠ LLC)
       ├─ 3. subagentes en paralelo
       │     ├─ dd-identidad            → dd-registros (DNIT, OpenCorporates, SAM, registros solo web) + web
       │     ├─ dd-contrataciones       → dd-dncp (API v3 OCDS, 15/min, caché 24 h)
       │     └─ dd-judicial-reputacion  → dd-sanciones (índice local OpenSanctions + OFAC) + web
       │     (todos registran en dd-evidencia: consultas, capturas con SHA-256, hallazgos)
       ├─ 4. dd-cruces → dd-grafo (vínculos con respaldo, llaves compartidas)
       └─ 5. dd-ficha → generar_ficha: ficha.md / ficha.html / semaforo.json / caso.json

Base: SQLite en var/dd.sqlite (caso, entidad, persona, vinculo, consulta, captura, hallazgo, cache_http)
Evidencia: var/casos/caso-N/capturas/ (HTML + PNG con navegador, hash SHA-256)
```

Las reglas de oro se aplican **en el código**, no solo en el prompt:

| Regla del documento | Dónde se hace cumplir |
|---|---|
| Un dato sin identificador que lo ate es posible alerta | `db.registrar_hallazgo` rebaja `hecho` → `posible_alerta` si falta `identificador_que_ata` (o si la fuente es D) |
| La unidad de análisis es la entidad legal | `hallazgo.entidad_id` obligatorio; RUC validado con su dígito verificador al registrar la entidad |
| "No encontrado" también es un resultado | Cada herramienta dd-* registra su consulta sola, aunque no haya resultados; la ficha las lista |
| Fuentes pagas, con usuario o presenciales son brecha | Estado `no_accesible`; `registro_solo_web`; la ficha tiene sección de brechas |
| Denuncia ≠ imputación ≠ condena | `etapa_judicial` obligatoria en categorías `caso_judicial_*` |
| No inferir parentesco | No existe el tipo de vínculo "parentesco"; todo vínculo exige un hallazgo de respaldo |
| El criterio se fija antes y queda versionado | Copia + SHA-256 del criterio en `caso` al crearlo; la ficha muestra versión y hash |
| El modelo no afirma sin fuente | La ficha solo se arma desde la base; el resumen libre se rechaza si una línea no cita `[H-n]`/`[C-n]` existente con URL |
| Reglas duras solo con evidencia fuerte | Una `regla_dura` exige `hecho` con confiabilidad A o B; si no, queda como `regla_dura_sin_confirmar` |
| Solo lectura | Las herramientas de fuentes solo hacen GET; lo único que se escribe es la base local |

## 3. Estado por fase

### Fase 0 · Preparación — ✅ hecha (falta el token DNCP)
- [x] Repositorio con `pyproject.toml` (uv), `.mcp.json` (5 servidores stdio), `.claude/settings.json` (permisos), `.env.example`.
- [x] Descargador de fuentes: `uv run dd descargar-fuentes [--dnit]` (OpenSanctions `sanctions` + `debarment`, OFAC SDN, listado de RUC de la DNIT).
- [x] Prueba de salud por fuente: `uv run dd salud`.
- [x] Verificado: los 5 servidores arrancan por stdio y exponen 30 herramientas; la API pública de la DNCP responde sin token.
- [ ] **Registrar la aplicación en el portal de datos de la DNCP** y cargar `DNCP_REQUEST_TOKEN` (el cliente ya hace el `POST /oauth/token` y renueva el access token de 15 min).
- [ ] Correr `claude mcp list` en una máquina del equipo y aprobar los servidores del proyecto.

### Fase 1 · Contrataciones — ✅ construida, ⏳ falta validar contra la guía
- [x] Servidor `dd-dncp`: `buscar_proveedores`, `obtener_proveedor`, `buscar_procesos`, `obtener_record_ocds`, `obtener_recurso`, `buscar_convocantes`. Respuestas compactas (< 6.000 caracteres), caché 24 h, reintentos, limitador de 15/min compartido entre procesos.
- [x] Skill `dd-contrataciones-py` con campos OCDS y banderas rojas seleccionadas.
- [x] Subagente `dd-contrataciones`.
- [ ] Reproducir A-01 a A-07 de la guía (necesita la guía).
- [ ] Revisar la selección de banderas rojas contra la guía de OCP con el equipo.

### Fase 2 · Entidades y sanciones — ✅ construida
- [x] Skill `dd-resolucion-entidades` + scripts autocontenidos `variantes.py` y `ruc_dv.py` (con prueba de paridad contra la librería).
- [x] Servidor `dd-sanciones`: índice local con búsqueda por tokens y puntaje, prueba variantes, distingue coincidencia por nombre de coincidencia por identificador. Probado con OFAC real (19.471 registros).
- [x] Servidor `dd-registros`: validación de RUC, búsqueda en el listado DNIT, OpenCorporates (con token), SAM.gov (con clave), registros solo web como brecha.
- [x] Subagentes `dd-identidad` y `dd-judicial-reputacion`.
- [ ] Construir el índice completo (OpenSanctions pesa ~165 MB) en la máquina de la demo.
- [ ] Correr Integralis S.A. / Integralis LLC de punta a punta con Claude Code.

### Fase 3 · Evidencia y ficha — ✅ construida
- [x] Servidor `dd-evidencia`: casos, entidades, personas, consultas, capturas (HTML + PNG con Playwright, SHA-256), hallazgos validados, resumen del caso, ficha.
- [x] Semáforo explicable (`src/dd/semaforo.py`): reglas duras, puntaje, umbrales, tareas de verificación, brechas y "qué cambiaría el resultado".
- [x] Ficha Markdown + HTML con avisos (documento interno, datos ficticios, criterio de ejemplo) y bloque de firma humana. Ejemplo en `docs/ejemplo-mock/`.
- [x] Skill `dd-ficha`.

### Fase 4 · Cruces — ✅ construida
- [x] Servidor `dd-grafo`: `agregar_vinculo` (con hallazgo obligatorio), `vecinos`, `llaves_compartidas` (también entre casos), `mapa_vinculos` (Mermaid con `[H-n]` en cada arista).
- [x] Skill `dd-cruces` + script autocontenido `llaves_compartidas.py`.
- [ ] Probar con competidores reales de la DNCP (cuidar el cupo de 15/min o usar el token).

### Fase 5 · Demo y evaluación — ⏳ pendiente de insumos
- [x] `uv run dd evaluar <caso> <referencia.json>`: cobertura, entidad correcta, evidencia completa, "no encontrado" auditable, homónimos guardados como hecho, semáforo y tiempo.
- [x] Demo determinista sin red ni LLM: `uv run python scripts/demo_mock.py` (caso ficticio "Beta Ficticia": rojo por dos reglas duras, 100 % en todas las métricas contra `eval/referencia/mock-beta.json`).
- [ ] Cargar la referencia de Integralis (`eval/referencia/integralis.json`) con la ronda manual.
- [ ] Elegir el control positivo (inhabilitación vigente en la DNCP), un proveedor sin antecedentes y uno con homónimo (`eval/casos.json`).
- [ ] Ensayo de la demo con tiempos medidos (manual vs. agente).

## 4. Cronograma sugerido para lo que falta

| Paso | Qué | Quién | Depende de |
|---|---|---|---|
| 1 | Token DNCP + `dd descargar-fuentes --dnit` en la máquina de la demo | Equipo | Registro en el portal |
| 2 | Corrida en modo mock con Claude Code (`DD_MODO=mock claude`) para ajustar las skills | Desarrollo | — |
| 3 | Corrida real de Integralis; revisar la ficha con Guillermo, Ariel y Lázaro | Desarrollo + equipo manual | 1 |
| 4 | Cargar la referencia y ajustar skills donde el agente falle | Desarrollo | Guía y ronda manual |
| 5 | Control positivo, sin antecedentes y homónimo | Desarrollo | 1 |
| 6 | Reemplazar el criterio de ejemplo por el de la UNI (nueva `version`) | UNI | — |
| 7 | Ensayo final y medición de tiempos | Todos | 3–6 |

## 5. Desvíos respecto del documento de diseño (y por qué)

| Documento | Implementación | Motivo |
|---|---|---|
| Reutilizar `mcp-contrataciones-py` (comunitario) | Servidor propio `dd-dncp` (6 herramientas) | Había que revisar ese código antes de usarlo y no estaba en PyPI. El propio cubre lo necesario, registra cada consulta en la base, aplica el límite de velocidad y tiene modo mock. Si el equipo revisa y prefiere el comunitario, se puede sumar en `.mcp.json` en paralelo. |
| Ficha en Word | Markdown + HTML | Decisión del equipo; Word queda para después. |
| Cinco tablas | Cinco + `caso` (congela el criterio por corrida), `captura` (evidencia en disco) y `cache_http` | Auditabilidad y límite de la API. |
| Puntaje solo sobre posibles alertas | También sobre hechos con categoría de riesgo | Un hecho confirmado (p. ej. una imputación atada al RUC) debe pesar al menos tanto como una alerta. |
| SDK de MCP `FastMCP` | `MCPServer` del SDK 2.x | La versión 2 del SDK renombró la clase. |

## 6. Lo que aprendimos de la API de la DNCP al construir

- `search/suppliers?name=` busca por subcadena en el **nombre de fantasía**, no en la razón social;
  `search/processes?awards.suppliers.name=` sí busca en la razón social de los adjudicados. Es la
  misma lección del `site:` de la ronda manual: hay que probar variantes **y** campos.
- "Sin resultados" vuelve como HTTP 404 con `{"message": "No encontrado"}`.
- Una sanción puede tener `status: "Activo"` con `endDate` vencida: la vigencia se calcula por fechas.
- En una prueba exploratoria, `integralis` no devolvió resultados ni como nombre de fantasía ni como
  razón social de adjudicado. **No es una conclusión**: falta probar las demás variantes y la entidad
  LLC, y es justamente el tipo de dato que el agente debe registrar y el equipo revisar.

## 7. Decisiones o insumos que necesito del equipo

1. **Guía y ronda manual** de Integralis (A-01 a A-07 y hallazgos): sin esto no hay métrica de cobertura.
2. **Criterio de semáforo de la UNI**: severidades, umbrales y reglas duras definitivas (y quién lo aprueba).
3. **Token de la DNCP**: quién registra la aplicación en el portal de datos.
4. **Casos de prueba**: ¿el control positivo lo elegimos del listado público de inhabilitados o lo propone el equipo? ¿Hay un homónimo conocido?
5. **Claves opcionales**: ¿se gestiona `SAM_API_KEY` (gratis, 10 consultas/día)? ¿OpenCorporates (gratis solo con licencia abierta share-alike)?
6. **Navegador sobre portales**: ¿el equipo revisó los términos de uso del Poder Judicial y del registro de Nevada para automatizar consultas? Mientras no, quedan como brecha.
7. **Revisión legal** (Ley 7593/2025): finalidad declarada, plazo de conservación de `var/` y licencias (OpenSanctions no comercial) antes de cualquier uso fuera del hackatón.

## 8. Riesgos detectados durante la construcción

| Riesgo | Mitigación actual | Pendiente |
|---|---|---|
| El validador de la ficha comprueba que cada línea cite un hallazgo existente, pero no que la línea diga lo mismo que el hallazgo | La ficha muestra el dato literal de cada hallazgo junto al resumen; revisión humana obligatoria | Evaluar un chequeo adicional (otro modelo o reglas) antes de producción |
| Cupo de 15 llamadas/min en la DNCP con tres subagentes | Limitador compartido entre procesos + caché 24 h | Token para la demo |
| Datos mock confundidos con reales | URL `mock://` y `demo://`, marca `es_mock`, aviso en la ficha, RUC ficticios | — |
| Respuestas grandes (> 10.000 tokens) | Respuestas compactas y paginadas; recorte de JSON grandes | — |
| Prompt injection desde páginas | Herramientas de solo lectura; instrucciones explícitas en skills y subagentes; revisión humana | — |

## 9. Después del hackatón

- Backend con Claude Agent SDK que corra el mismo flujo (misma configuración de MCP; sin OAuth interactivo, con tokens).
- Transporte HTTP en los servidores (`servidor.run("streamable-http")`) para usarlos como conector en claude.ai o con el MCP connector de la Messages API.
- Ficha en Word con la skill de documentos.
- Puente con el Desafío 8: los servidores, la base de evidencia y las reglas en Markdown son reutilizables con otro modelo vía MCP.
