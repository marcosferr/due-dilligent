"""Servidor MCP `dd-dncp`: API v3 (OCDS) de la DNCP, solo lectura, con límite de velocidad."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from ..dncp import FUENTE, ClienteDNCP
from ..http import ErrorFuente
from ._comun import SOLO_LECTURA, consulta_fallida, consulta_ok

servidor = MCPServer(
    "dd-dncp",
    instructions=(
        "Contrataciones públicas de Paraguay (DNCP, API v3 OCDS). Todas las herramientas piden caso_id "
        "y registran la consulta, aunque no haya resultados. `nombre` en buscar_proveedores busca en el "
        "nombre de fantasía; para la razón social usar buscar_procesos(nombre_proveedor=...). "
        "Sin token hay 15 llamadas por minuto: preferir RUC a nombre y no repetir consultas."
    ),
)
_cliente: ClienteDNCP | None = None


def cliente() -> ClienteDNCP:
    global _cliente
    if _cliente is None:
        _cliente = ClienteDNCP()
    return _cliente


def _ejecutar(caso_id: int, texto: str, llamada, contar) -> dict[str, Any]:
    c = cliente()
    try:
        resp, datos = llamada(c)
    except ErrorFuente as e:
        return consulta_fallida(caso_id, FUENTE, texto, f"Fuente no accesible: {e}")
    return consulta_ok(caso_id, FUENTE, texto, resp, contar(datos), datos, modo_acceso=c.modo_acceso)


@servidor.tool(annotations=SOLO_LECTURA)
def buscar_proveedores(
    caso_id: int,
    nombre: str | None = None,
    ruc: str | None = None,
    categoria_id: str | None = None,
    tipo_sancion: str | None = None,
    pagina: int = 1,
) -> dict[str, Any]:
    """Busca proveedores por nombre de fantasía (subcadena), RUC, categoría o tipo de sanción
    (p. ej. INHABILITACION, AMONESTACION). Devuelve razón social, contacto, dirección y sanciones con
    `vigente`. Hasta 10 por página."""
    texto = f"search/suppliers name={nombre!r} ruc={ruc!r} categoria={categoria_id!r} sancion={tipo_sancion!r} p{pagina}"
    return _ejecutar(caso_id, texto,
                     lambda c: c.buscar_proveedores(nombre, ruc, categoria_id, tipo_sancion, pagina),
                     lambda d: len(d["proveedores"]))


@servidor.tool(annotations=SOLO_LECTURA)
def obtener_proveedor(caso_id: int, ruc: str) -> dict[str, Any]:
    """Ficha del proveedor por RUC (con o sin DV): razón social, contacto, dirección, categorías,
    sanciones (con vigencia calculada por fechas) y cantidad de adjudicaciones."""
    return _ejecutar(caso_id, f"suppliers/{ruc}", lambda c: c.obtener_proveedor(ruc), lambda d: 1 if d else 0)


@servidor.tool(annotations=SOLO_LECTURA)
def buscar_procesos(
    caso_id: int,
    ruc_proveedor: str | None = None,
    nombre_proveedor: str | None = None,
    ocid: str | None = None,
    titulo: str | None = None,
    convocante: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    pagina: int = 1,
) -> dict[str, Any]:
    """Procesos de contratación donde el proveedor fue adjudicado (por RUC o por subcadena de la
    razón social), o por ocid/título/convocante. Resumen por proceso: modalidad, convocante,
    adjudicaciones con montos y contratos. Hasta 10 por página; `total` indica cuántos hay."""
    texto = (f"search/processes ruc={ruc_proveedor!r} nombre={nombre_proveedor!r} ocid={ocid!r} "
             f"titulo={titulo!r} convocante={convocante!r} desde={fecha_desde!r} hasta={fecha_hasta!r} p{pagina}")
    return _ejecutar(caso_id, texto,
                     lambda c: c.buscar_procesos(ruc_proveedor, nombre_proveedor, ocid, titulo, convocante,
                                                 fecha_desde, fecha_hasta, pagina),
                     lambda d: len(d["procesos"]))


@servidor.tool(annotations=SOLO_LECTURA)
def obtener_record_ocds(caso_id: int, ocid: str) -> dict[str, Any]:
    """Record OCDS compilado de un proceso: partes con roles (oferentes = competidores),
    cantidad de oferentes, adjudicaciones, contratos, protestas y monto estimado."""
    return _ejecutar(caso_id, f"ocds/record/{ocid}", lambda c: c.obtener_record(ocid), lambda d: 1 if d else 0)


@servidor.tool(annotations=SOLO_LECTURA)
def obtener_recurso(caso_id: int, tipo: str, id: str) -> dict[str, Any]:
    """Detalle de un recurso por id. tipo: contrato | adjudicacion | protesta | licitacion | convocante.
    Respuestas grandes se recortan."""
    return _ejecutar(caso_id, f"{tipo}/{id}", lambda c: c.obtener_recurso(tipo, id), lambda d: 1 if d else 0)


@servidor.tool(annotations=SOLO_LECTURA)
def buscar_convocantes(caso_id: int, nombre: str, pagina: int = 1) -> dict[str, Any]:
    """Busca entidades convocantes (organismos del Estado) por nombre."""
    return _ejecutar(caso_id, f"search/procuringEntities name={nombre!r} p{pagina}",
                     lambda c: c.buscar_convocantes(nombre, pagina), lambda d: len(d["convocantes"]))


def main() -> None:
    servidor.run("stdio")


if __name__ == "__main__":
    main()
