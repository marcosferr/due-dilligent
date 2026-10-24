"""Servidor MCP `dd-registros`: identidad de las entidades (DNIT, registros extranjeros, SAM.gov)."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .. import config, registros
from ._comun import SOLO_LECTURA, consulta_fallida, consulta_ok

servidor = MCPServer(
    "dd-registros",
    instructions=(
        "Identidad de entidades: RUC y estado en la DNIT (listado descargado), registros de empresas "
        "extranjeras (OpenCorporates) y exclusiones federales de EE. UU. (SAM.gov). Lo que pide pago, "
        "usuario o trámite presencial vuelve como brecha. Agente registrado ≠ dueño."
    ),
)


@servidor.tool(annotations=SOLO_LECTURA)
def variantes_nombre(
    nombre: str,
    nombre_comercial: str | None = None,
    dominio: str | None = None,
    formas_extra: list[str] | None = None,
) -> dict[str, Any]:
    """Variantes de nombre a probar en cada fuente: forma jurídica escrita de todas las maneras
    (S.A., S.A, S. A., SA, Sociedad Anónima…), sin acentos, nombre comercial y dominio.
    formas_extra: otras formas a probar, p. ej. ["LLC"] para una entidad hermana extranjera."""
    from ..variantes import detectar_forma, generar_variantes, normalizar

    base, forma = detectar_forma(nombre)
    return {"base": base, "forma_juridica": forma, "clave_normalizada": normalizar(nombre),
            "variantes": generar_variantes(nombre, nombre_comercial, dominio, formas_extra)}


@servidor.tool(annotations=SOLO_LECTURA)
def dnit_validar_ruc(ruc: str) -> dict[str, Any]:
    """Valida el dígito verificador de un RUC (módulo 11) o lo calcula si falta. Cálculo local."""
    return registros.validar(ruc)


@servidor.tool(annotations=SOLO_LECTURA)
def dnit_buscar_ruc(caso_id: int, nombre: str | None = None, ruc: str | None = None) -> dict[str, Any]:
    """Busca en el listado de RUC de la DNIT por razón social (subcadena normalizada) o por RUC.
    Devuelve RUC con DV, razón social, estado (ACTIVO, CANCELADO, SUSPENSION TEMPORAL, BLOQUEADO…)."""
    fuente = "DNIT – Listado de RUC con equivalencias"
    texto = f"dnit ruc={ruc!r} nombre={nombre!r}"
    if config.modo() == "mock":
        return consulta_fallida(caso_id, fuente, texto, "Modo mock: el listado DNIT no tiene datos ficticios",
                                modo_acceso="mock")
    try:
        datos = registros.dnit_buscar(nombre=nombre, ruc=ruc)
    except FileNotFoundError as e:
        return consulta_fallida(caso_id, fuente, texto, str(e), url=registros.URL_DNIT_LISTADO)
    return consulta_ok(caso_id, fuente, texto, None, len(datos["resultados"]), datos, modo_acceso="descarga",
                       url=registros.URL_DNIT_LISTADO)


@servidor.tool(annotations=SOLO_LECTURA)
def registro_extranjero(caso_id: int, nombre: str, jurisdiccion: str | None = None) -> dict[str, Any]:
    """Busca una empresa extranjera en OpenCorporates (jurisdiccion p. ej. 'us_nv' para Nevada).
    Devuelve número de registro, estado, fecha de constitución y agente registrado. Además indica
    el registro oficial (solo web) a consultar con navegador o a mano."""
    fuente = "OpenCorporates"
    texto = f"opencorporates q={nombre!r} jurisdiccion={jurisdiccion!r}"
    oficial = registros.REGISTROS_SOLO_WEB.get(jurisdiccion or "")
    try:
        datos = registros.opencorporates_buscar(nombre, jurisdiccion)
    except (PermissionError, RuntimeError) as e:
        salida = consulta_fallida(caso_id, fuente, texto, str(e), url="https://opencorporates.com/")
        if oficial:
            salida["registro_oficial"] = oficial
        return salida
    if oficial:
        datos["registro_oficial"] = oficial
    return consulta_ok(caso_id, fuente, texto, None, len(datos["empresas"]), datos, url=datos["url"])


@servidor.tool(annotations=SOLO_LECTURA)
def registro_solo_web(caso_id: int, registro: str, consulta: str) -> dict[str, Any]:
    """Registra como brecha un registro sin API (us_nv, py_registros_publicos, py_poder_judicial) y
    devuelve su URL para consultarlo con capturar(usar_navegador=True) si sus términos lo permiten."""
    info = registros.REGISTROS_SOLO_WEB.get(registro)
    if not info:
        return {"error": f"Registro desconocido. Opciones: {', '.join(registros.REGISTROS_SOLO_WEB)}"}
    salida = consulta_fallida(caso_id, info["nombre"], consulta, info["nota"], url=info["url"], modo_acceso="web")
    salida["siguiente_paso"] = ("Si los términos de uso lo permiten, consultar con capturar(url, usar_navegador=True) "
                                "y registrar lo visto como hallazgo con su captura; si no, queda como brecha.")
    return salida


@servidor.tool(annotations=SOLO_LECTURA)
def sam_exclusiones(caso_id: int, nombre: str) -> dict[str, Any]:
    """Exclusiones federales de EE. UU. en SAM.gov (relevante para entidades estadounidenses).
    Requiere SAM_API_KEY (10 consultas por día): usar solo con la razón social exacta."""
    fuente = "SAM.gov Exclusions API"
    texto = f"sam exclusions name={nombre!r}"
    try:
        datos = registros.sam_exclusiones(nombre)
    except (PermissionError, RuntimeError) as e:
        return consulta_fallida(caso_id, fuente, texto, str(e), url="https://sam.gov/search/?index=ex")
    return consulta_ok(caso_id, fuente, texto, None, len(datos["exclusiones"]), datos, url=datos["url"])


def main() -> None:
    servidor.run("stdio")


if __name__ == "__main__":
    main()
