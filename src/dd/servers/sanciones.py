"""Servidor MCP `dd-sanciones`: screening contra el índice local (OpenSanctions + OFAC)."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .. import config, sanciones
from ..variantes import generar_variantes
from ._comun import SOLO_LECTURA, consulta_fallida, consulta_ok

servidor = MCPServer(
    "dd-sanciones",
    instructions=(
        "Screening de entidades y personas en listas de sanciones, PEP e inhabilitaciones (índice local). "
        "Una coincidencia sin `coincide_identificador` es posible alerta (homónimo posible), nunca hecho. "
        "Solo una coincidencia confirmada por identificador puede activar la regla dura."
    ),
)
FUENTE = "Índice local de sanciones (OpenSanctions + OFAC)"


def _demo() -> bool:
    return config.modo() == "mock"


def _screen(caso_id: int, nombre: str, persona: bool, identificadores: list[str], fecha_nacimiento: str | None,
            con_variantes: bool, umbral: float) -> dict[str, Any]:
    fuente = FUENTE + (" [DEMO FICTICIO]" if _demo() else "")
    nombres = generar_variantes(nombre) if con_variantes and not persona else [nombre]
    texto = f"screen_{'persona' if persona else 'entidad'} {nombre!r} ids={identificadores} variantes={len(nombres)}"
    try:
        vistos: dict[str, dict[str, Any]] = {}
        for n in nombres:
            r = sanciones.screen(n, persona=persona, identificadores=identificadores,
                                 fecha_nacimiento=fecha_nacimiento, umbral=umbral, demo=_demo())
            for c in r["candidatos"]:
                previo = vistos.get(c["ref"])
                if previo is None or c["puntaje"] > previo["puntaje"]:
                    vistos[c["ref"]] = {**c, "variante": n}
    except FileNotFoundError as e:
        return consulta_fallida(caso_id, fuente, texto, str(e))
    candidatos = sorted(vistos.values(), key=lambda c: (c["coincide_identificador"], c["puntaje"]), reverse=True)[:10]
    estado = sanciones.estado_indice(_demo())
    resultado = {
        "candidatos": candidatos,
        "variantes_probadas": nombres,
        "indice": {k: estado.get(k) for k in ("construido_utc", "registros", "por_fuente")},
        "regla": "Sin coincide_identificador → posible_alerta (categoria coincidencia_sancion_solo_nombre). "
                 "Con identificador → hecho con regla_dura sancion_confirmada_por_identificador.",
    }
    return consulta_ok(caso_id, fuente, texto, None, len(candidatos), resultado,
                       modo_acceso="mock" if _demo() else "descarga",
                       url=candidatos[0]["url"] if candidatos else "local://indice-sanciones")


@servidor.tool(annotations=SOLO_LECTURA)
def screen_entidad(
    caso_id: int,
    nombre: str,
    identificadores: list[str] | None = None,
    con_variantes: bool = True,
    umbral: float = 0.82,
) -> dict[str, Any]:
    """Busca una empresa (y sus variantes de nombre y forma jurídica) en el índice de sanciones.
    `identificadores`: RUC, número de registro extranjero, UEI, etc., para confirmar coincidencias.
    Devuelve candidatos con puntaje, campos coincidentes y URL del registro."""
    return _screen(caso_id, nombre, False, identificadores or [], None, con_variantes, umbral)


@servidor.tool(annotations=SOLO_LECTURA)
def screen_persona(
    caso_id: int,
    nombre: str,
    documento: str | None = None,
    fecha_nacimiento: str | None = None,
    umbral: float = 0.85,
) -> dict[str, Any]:
    """Busca una persona (directivo, accionista, representante) en sanciones y PEP.
    Solo personas con rol público en la empresa o en contratos públicos."""
    return _screen(caso_id, nombre, True, [documento] if documento else [], fecha_nacimiento, False, umbral)


@servidor.tool(annotations=SOLO_LECTURA)
def estado_indice() -> dict[str, Any]:
    """Fuentes cargadas en el índice, cantidad de registros y fecha de construcción."""
    return sanciones.estado_indice(_demo())


def main() -> None:
    servidor.run("stdio")


if __name__ == "__main__":
    main()
