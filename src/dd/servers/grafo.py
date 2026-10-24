"""Servidor MCP `dd-grafo`: vínculos con respaldo y llaves compartidas entre entidades."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .. import db, grafo
from ._comun import ESCRITURA_LOCAL, SOLO_LECTURA

servidor = MCPServer(
    "dd-grafo",
    instructions=(
        "Mapa de vínculos del caso. Todo vínculo necesita el hallazgo que lo respalda. No existe el tipo "
        "'parentesco': mismo apellido no es parentesco. Un vínculo o una llave compartida no es una "
        "irregularidad; se muestra con su fuente y no se califica."
    ),
)


@servidor.tool(annotations=ESCRITURA_LOCAL)
def agregar_vinculo(
    caso_id: int,
    desde_tipo: str,
    desde_id: int,
    tipo: str,
    hacia_tipo: str,
    hacia_id: int,
    hallazgo_id: int,
) -> dict[str, Any]:
    """Agrega un vínculo entre nodos ('entidad' o 'persona') respaldado por un hallazgo.
    tipo: accionista | representante | director | gestor | agente_registrado | misma_direccion |
    mismo_telefono | mismo_correo | mismo_dominio | funcionario_en | compitio_contra | contrato_con |
    sucesora_de | misma_marca. agente_registrado no cuenta como persona vinculada."""
    try:
        with db.conectar() as con:
            vid = db.registrar_vinculo(con, caso_id, desde_tipo, desde_id, tipo, hacia_tipo, hacia_id, hallazgo_id)
        return {"ok": True, "vinculo_id": vid}
    except db.ErrorValidacion as e:
        return {"ok": False, "error": str(e)}


@servidor.tool(annotations=SOLO_LECTURA)
def vecinos(caso_id: int, nodo_tipo: str, nodo_id: int) -> dict[str, Any]:
    """Vínculos que entran o salen de un nodo, con el hallazgo que respalda cada uno."""
    with db.conectar() as con:
        return {"vinculos": grafo.vecinos(con, caso_id, nodo_tipo, nodo_id)}


@servidor.tool(annotations=SOLO_LECTURA)
def llaves_compartidas(caso_id: int, entre_casos: bool = False) -> dict[str, Any]:
    """Teléfono, correo, dominio, dirección o persona repetidos entre entidades del caso (o, con
    entre_casos, contra entidades de casos anteriores). Cada llave es un dato a explicar."""
    with db.conectar() as con:
        llaves = grafo.llaves_compartidas(con, caso_id, entre_casos)
    return {"total": len(llaves), "llaves": llaves}


@servidor.tool(annotations=SOLO_LECTURA)
def mapa_vinculos(caso_id: int) -> dict[str, Any]:
    """Mapa de vínculos en Mermaid; cada arista lleva [H-n], el hallazgo que la respalda."""
    with db.conectar() as con:
        return {"mermaid": grafo.mapa_mermaid(con, caso_id)}


def main() -> None:
    servidor.run("stdio")


if __name__ == "__main__":
    main()
