# due-dilligent

Sistema agéntico de due diligence de proveedores (Hackatón UNI · Desafío 3).

A partir del nombre o RUC de un proveedor, un agente en Claude Code consulta fuentes públicas a
través de servidores MCP, guarda cada dato con su fuente, confiabilidad y captura, cruza personas y
empresas, y entrega una ficha con un semáforo **sugerido** que el equipo revisa y firma. El agente
propone; la conclusión sigue siendo humana.

- Plan de implementación y estado: [`PLAN.md`](PLAN.md)
- Ficha de ejemplo (datos ficticios): [`docs/ejemplo-mock/ficha.md`](docs/ejemplo-mock/ficha.md)

## Requisitos

- [uv](https://docs.astral.sh/uv/) y Python 3.11+
- [Claude Code](https://code.claude.com/)
- Opcional, para capturas de páginas con JavaScript: Playwright (`uv sync --extra captura && uv run playwright install chromium`, o Playwright de Node)

## Puesta en marcha

```bash
uv sync --extra dev
cp .env.example .env          # completar DNCP_REQUEST_TOKEN si lo hay
uv run dd descargar-fuentes   # OpenSanctions + OFAC → índice local de sanciones (~170 MB)
uv run dd descargar-fuentes --sin-opensanctions --sin-ofac --dnit   # listado de RUC de la DNIT
uv run dd descargar-fuentes --sin-opensanctions --sin-ofac --dncp-masivo 2020-2026   # base comparativa DNCP
uv run dd salud               # estado de cada fuente
```

## Uso con Claude Code

Abrir Claude Code **en la raíz del repositorio** (los servidores de `.mcp.json` se lanzan con `uv run`
desde ahí) y aprobar los servidores del proyecto la primera vez:

```bash
claude
> /due-diligence-proveedores Integralis S.A.
```

Para practicar sin red con datos ficticios:

```bash
DD_MODO=mock claude
> /due-diligence-proveedores Beta Ficticia
```

Las fichas quedan en `var/casos/caso-N/` (`ficha.md`, `ficha.html`, `semaforo.json`, `caso.json`
y `capturas/`).

## Comparar proveedores

```bash
uv run dd comparar 80028355-4 80027374-5 80089752-8 --desde 2022 --salida casos/comparaciones/ejemplo
```

Histórico de montos por año, tamaño declarado, dependencia de un convocante, oferente único,
adjudicado frente a estimado, contratado, pagado y demora de pago, desde las descargas masivas OCDS
de la DNCP (skill `dd-comparacion-proveedores`). Ejemplo real en `casos/comparaciones/itti-competidores/`.

## Habilidades (skills)

Las skills guardan el **método**; los servidores MCP traen los **datos**. Están en `.claude/skills/`
y Claude Code las activa solo según lo que se pida. También se pueden invocar con `/<nombre>`.

| Skill | Qué hace | Cuándo se activa | Herramientas principales |
|---|---|---|---|
| [`due-diligence-proveedores`](.claude/skills/due-diligence-proveedores/SKILL.md) | Orquestador: abre el caso, resuelve entidades, reparte el trabajo en tres subagentes, aplica las reglas de oro y cierra con la ficha | "due diligence", "antecedentes", "ficha" o "verificación" de un proveedor; RUC, DNCP, licitaciones | `dd-evidencia`, subagentes `dd-identidad`, `dd-contrataciones` y `dd-judicial-reputacion` |
| [`dd-resolucion-entidades`](.claude/skills/dd-resolucion-entidades/SKILL.md) | Separa la marca de las entidades legales (S.A. ≠ LLC), valida el RUC con su dígito verificador, genera variantes de nombre y descarta homónimos | Al empezar un caso, cuando un nombre puede ser varias empresas o hay que validar un RUC | `variantes_nombre`, `dnit_validar_ruc`, `dnit_buscar_ruc`, `registro_extranjero` |
| [`dd-contrataciones-py`](.claude/skills/dd-contrataciones-py/SKILL.md) | Contrataciones en la DNCP: adjudicaciones, contratos, sanciones (vigencia por fechas **y** sin cautelares), protestas, competidores y banderas rojas OCDS | Bloque de contrataciones de un caso; licitaciones, contratos o sanciones de un RUC | `buscar_proveedores`, `obtener_proveedor`, `buscar_procesos`, `obtener_record_ocds`, `obtener_recurso` |
| [`dd-cruces`](.claude/skills/dd-cruces/SKILL.md) | Cruza personas, teléfonos, correos, dominios y direcciones entre el proveedor, sus entidades hermanas y sus competidores, con reglas de prudencia (mismo apellido ≠ parentesco) | Después de recolectar los datos, o cuando preguntan por vínculos o conflictos de interés | `llaves_compartidas`, `agregar_vinculo`, `mapa_vinculos` |
| [`dd-ficha`](.claude/skills/dd-ficha/SKILL.md) | Genera la ficha en Markdown y HTML desde la base, con el semáforo sugerido y sus razones; rechaza las afirmaciones que no citan un hallazgo | Al cerrar un caso, o cuando piden la ficha, el informe o el semáforo | `resumen_caso`, `generar_ficha` |
| [`dd-comparacion-proveedores`](.claude/skills/dd-comparacion-proveedores/SKILL.md) **(nueva)** | Compara varios proveedores con datos oficiales: histórico de montos por año, tamaño declarado, dependencia de un convocante, modalidades no competitivas, oferente único, adjudicado frente a estimado, contratado, pagado, demora de pago y precios unitarios frente al mercado | Cuando piden comparar proveedores, un ranking, una base comparativa, el histórico de montos o el tamaño de una empresa | `estado_datos_masivos`, `perfil_proveedor`, `comparar_proveedores`, `precios_vs_mercado` (dd-dncp); CLI `dd comparar` |

Referencias de cada skill:
- Fuentes, escala de confiabilidad y criterio del semáforo: `due-diligence-proveedores/reference/`.
- Campos OCDS y banderas rojas: `dd-contrataciones-py/reference/`.
- Tablas y columnas de las descargas masivas de la DNCP, y definición y límites de cada indicador comparativo: `dd-comparacion-proveedores/reference/`.
- Scripts autocontenidos (funcionan fuera del repo): `dd-resolucion-entidades/scripts/` (`ruc_dv.py`, `variantes.py`) y `dd-cruces/scripts/llaves_compartidas.py`.

## Casos de ejemplo

| Carpeta | Contenido |
|---|---|
| [`casos/itti-sae/`](casos/itti-sae/fuentes-a-revisar.md) | Corrida real de Itti S.A.E.: ficha, semáforo y fuentes a revisar |
| [`casos/universidad-nacional/`](casos/universidad-nacional/candidatos.md) | Proveedores de la Universidad Nacional de Itapúa con sanciones: candidatos a casos de prueba y datos crudos |
| [`casos/comparaciones/itti-competidores/`](casos/comparaciones/itti-competidores/comparacion.md) | Comparación real de ITTI con J. Fleischman, Konecta, Roshka y Data Systems (2022–2026) |

## Demo determinista (sin LLM ni red)

```bash
uv run python scripts/demo_mock.py                     # caso ficticio de punta a punta
uv run dd evaluar 1 eval/referencia/mock-beta.json     # métricas contra la referencia
```

## Piezas

| Pieza | Dónde |
|---|---|
| Servidores MCP | `src/dd/servers/`: `dd-dncp` (incluye la comparación), `dd-sanciones`, `dd-registros`, `dd-evidencia`, `dd-grafo` (declarados en `.mcp.json`) |
| Skills (el método) | `.claude/skills/`: ver [Habilidades](#habilidades-skills) |
| Subagentes | `.claude/agents/`: `dd-identidad`, `dd-contrataciones`, `dd-judicial-reputacion` |
| Criterio del semáforo | `config/criterio_semaforo.json` (**ejemplo a reemplazar por la UNI**) |
| Modelo de datos | `src/dd/db.py` (SQLite en `var/dd.sqlite`); base comparativa en `src/dd/masivo.py` (`var/fuentes/dncp_masivo.sqlite`) |
| Evaluación | `eval/` y `uv run dd evaluar` |
| Datos ficticios | `data/mocks/dncp.json`, `data/samples/sanciones_demo.csv` |

## Pruebas

```bash
uv run pytest
```

## Licencias de datos

OpenSanctions en bloque es solo para uso no comercial (CC BY-NC 4.0). OpenCorporates gratis exige
publicar con licencia abierta share-alike. Los datos de la DNCP se publican bajo CC BY 4.0. Antes de
cualquier uso fuera del hackatón, revisar licencias y la Ley 7593/2025 de protección de datos personales.
