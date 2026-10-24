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

## Demo determinista (sin LLM ni red)

```bash
uv run python scripts/demo_mock.py                     # caso ficticio de punta a punta
uv run dd evaluar 1 eval/referencia/mock-beta.json     # métricas contra la referencia
```

## Piezas

| Pieza | Dónde |
|---|---|
| Servidores MCP | `src/dd/servers/`: `dd-dncp`, `dd-sanciones`, `dd-registros`, `dd-evidencia`, `dd-grafo` (declarados en `.mcp.json`) |
| Skills (el método) | `.claude/skills/`: `due-diligence-proveedores` (orquestador), `dd-resolucion-entidades`, `dd-contrataciones-py`, `dd-cruces`, `dd-ficha` |
| Subagentes | `.claude/agents/`: `dd-identidad`, `dd-contrataciones`, `dd-judicial-reputacion` |
| Criterio del semáforo | `config/criterio_semaforo.json` (**ejemplo a reemplazar por la UNI**) |
| Modelo de datos | `src/dd/db.py` (SQLite en `var/dd.sqlite`) |
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
