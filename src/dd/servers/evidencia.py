"""Servidor MCP `dd-evidencia`: casos, entidades, hallazgos, capturas y ficha.

Escribe solo en la base local del proyecto; nunca en sistemas de terceros.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from .. import db, evidencia, ficha, semaforo
from ._comun import ESCRITURA_LOCAL, SOLO_LECTURA

servidor = MCPServer(
    "dd-evidencia",
    instructions=(
        "Registro de evidencia del caso. Flujo: crear_caso → registrar_entidad (una por entidad legal, con "
        "identificador) → consultas en las fuentes → capturar(url) → registrar_hallazgo → generar_ficha. "
        "Un hallazgo sin identificador que lo ate se guarda como posible_alerta. Las respuestas traen "
        "advertencias: leerlas y corregir."
    ),
)


def _error(e: Exception) -> dict[str, Any]:
    return {"ok": False, "error": str(e)}


@servidor.tool(annotations=ESCRITURA_LOCAL)
def crear_caso(consulta_inicial: str) -> dict[str, Any]:
    """Crea un caso para un proveedor (nombre o RUC tal como llegó) y congela el criterio de semáforo
    vigente (versión + SHA-256). Devuelve caso_id, que piden todas las demás herramientas."""
    with db.conectar() as con:
        caso_id = db.crear_caso(con, consulta_inicial)
        caso = db.obtener_caso(con, caso_id)
    return {"ok": True, "caso_id": caso_id, "criterio_version": caso["criterio_version"],
            "criterio_sha256": caso["criterio_sha256"], "modo": caso["modo"]}


@servidor.tool(annotations=ESCRITURA_LOCAL)
def registrar_entidad(
    caso_id: int,
    razon_social: str,
    tipo: str | None = None,
    pais: str | None = None,
    identificadores: dict[str, str] | None = None,
    variantes: list[str] | None = None,
    dominio: str | None = None,
    telefonos: list[str] | None = None,
    correos: list[str] | None = None,
    direcciones: list[str] | None = None,
    rol: str = "investigada",
    notas: str | None = None,
) -> dict[str, Any]:
    """Registra una entidad legal (la unidad de análisis; una marca puede ser varias entidades).
    identificadores: {"RUC": "80012345-6"} o {"US-NV": "E0123..."}; el RUC se valida con su DV.
    rol: investigada | relacionada | competidor | convocante."""
    try:
        with db.conectar() as con:
            ent_id, adv = db.registrar_entidad(
                con, caso_id, razon_social, tipo=tipo, pais=pais, identificadores=identificadores,
                variantes=variantes, dominio=dominio, telefonos=telefonos, correos=correos,
                direcciones=direcciones, rol=rol, notas=notas,
            )
    except db.ErrorValidacion as e:
        return _error(e)
    return {"ok": True, "entidad_id": ent_id, "advertencias": adv}


@servidor.tool(annotations=ESCRITURA_LOCAL)
def actualizar_entidad(
    caso_id: int,
    entidad_id: int,
    identificadores: dict[str, str] | None = None,
    variantes: list[str] | None = None,
    dominio: str | None = None,
    telefonos: list[str] | None = None,
    correos: list[str] | None = None,
    direcciones: list[str] | None = None,
    notas: str | None = None,
) -> dict[str, Any]:
    """Agrega identificadores o datos de contacto (llaves de cruce) a una entidad sin borrar los anteriores."""
    try:
        with db.conectar() as con:
            if db.obtener_entidad(con, entidad_id)["caso_id"] != caso_id:
                raise db.ErrorValidacion("La entidad no pertenece al caso")
            db.actualizar_entidad(con, entidad_id, identificadores=identificadores, variantes=variantes,
                                  dominio=dominio, telefonos=telefonos, correos=correos, direcciones=direcciones,
                                  notas=notas)
            return {"ok": True, "entidad": db.obtener_entidad(con, entidad_id)}
    except db.ErrorValidacion as e:
        return _error(e)


@servidor.tool(annotations=ESCRITURA_LOCAL)
def registrar_persona(caso_id: int, nombre: str, documento: str | None = None,
                      cargos: list[str] | None = None) -> dict[str, Any]:
    """Registra una persona con rol público en una entidad (directivo, accionista, representante,
    gestor). Nunca datos de vida privada. Para ligarla a una entidad usar agregar_vinculo (dd-grafo)."""
    try:
        with db.conectar() as con:
            return {"ok": True, "persona_id": db.registrar_persona(con, caso_id, nombre, documento, cargos)}
    except db.ErrorValidacion as e:
        return _error(e)


@servidor.tool(annotations=ESCRITURA_LOCAL)
def registrar_consulta(
    caso_id: int,
    fuente: str,
    consulta: str,
    n_resultados: int,
    url: str | None = None,
    modo_acceso: str = "web",
    estado: str | None = None,
    detalle: str | None = None,
) -> dict[str, Any]:
    """Registra una consulta hecha fuera de los servidores dd-* (búsqueda web, lectura de una página,
    portal con navegador). Obligatorio también cuando no hubo resultados: anotar el texto exacto.
    estado: encontrado | parcial | no_encontrado | no_accesible (pago, usuario, presencial, caído)."""
    try:
        with db.conectar() as con:
            cid = db.registrar_consulta(con, caso_id, fuente, consulta, url=url, n_resultados=n_resultados,
                                        modo_acceso=modo_acceso, estado=estado, detalle=detalle)
        return {"ok": True, "consulta_id": cid}
    except db.ErrorValidacion as e:
        return _error(e)


@servidor.tool(annotations=ESCRITURA_LOCAL)
def capturar(caso_id: int, url: str, usar_navegador: bool = False) -> dict[str, Any]:
    """Guarda la página como evidencia: HTML, captura PNG (con navegador), hora UTC y SHA-256.
    Usar usar_navegador=True para páginas que cargan con JavaScript (p. ej. directorios como AmCham).
    No evade CAPTCHAs ni bloqueos. Devuelve captura_id para registrar_hallazgo."""
    try:
        return evidencia.capturar(caso_id, url, usar_navegador)
    except db.ErrorValidacion as e:
        return _error(e)


@servidor.tool(annotations=ESCRITURA_LOCAL)
def registrar_hallazgo(
    caso_id: int,
    entidad_id: int,
    dato: str,
    fuente: str,
    confiabilidad: str,
    tipo: str,
    estado: str,
    modo_acceso: str,
    url: str | None = None,
    extracto: str | None = None,
    identificador_que_ata: str | None = None,
    etapa_judicial: str | None = None,
    categoria_alerta: str | None = None,
    regla_dura: str | None = None,
    consulta_id: int | None = None,
    captura_id: int | None = None,
    persona_id: int | None = None,
) -> dict[str, Any]:
    """Guarda un hallazgo atado a una entidad concreta (nunca a la marca).
    confiabilidad: A (oficial primaria) | B (oficial secundaria o registro reconocido) | C (prensa,
    directorio, dicho de la empresa) | D (sin verificar). tipo: hecho | posible_alerta | contexto.
    estado: encontrado | parcial | no_encontrado | no_accesible. modo_acceso: api | descarga | web |
    navegador | manual | mock. identificador_que_ata: qué dato liga el hallazgo a la entidad (RUC X,
    registro Y, dominio Z) — sin él un "hecho" se guarda como posible_alerta. etapa_judicial obligatoria
    en casos judiciales. categoria_alerta y regla_dura: claves del criterio de semáforo del caso
    (ver criterio_del_caso). extracto: el texto o campo exacto de la fuente que respalda el dato."""
    try:
        with db.conectar() as con:
            hid, adv = db.registrar_hallazgo(
                con, caso_id, entidad_id, dato, fuente, confiabilidad, tipo, estado, modo_acceso,
                url=url, extracto=extracto, identificador_que_ata=identificador_que_ata,
                etapa_judicial=etapa_judicial, categoria_alerta=categoria_alerta, regla_dura=regla_dura,
                consulta_id=consulta_id, captura_id=captura_id, persona_id=persona_id,
            )
            h = db.obtener_hallazgo(con, hid)
    except db.ErrorValidacion as e:
        return _error(e)
    return {"ok": True, "hallazgo_id": hid, "tipo_guardado": h["tipo"], "advertencias": adv}


@servidor.tool(annotations=SOLO_LECTURA)
def criterio_del_caso(caso_id: int) -> dict[str, Any]:
    """Criterio de semáforo congelado en el caso: reglas duras, categorías de alerta y severidades."""
    import json

    with db.conectar() as con:
        caso = db.obtener_caso(con, caso_id)
    return {"version": caso["criterio_version"], "sha256": caso["criterio_sha256"],
            "criterio": json.loads(caso["criterio_json"])}


@servidor.tool(annotations=SOLO_LECTURA)
def listar_hallazgos(caso_id: int, entidad_id: int | None = None, tipo: str | None = None) -> dict[str, Any]:
    """Hallazgos del caso (opcionalmente de una entidad o de un tipo), en forma compacta."""
    with db.conectar() as con:
        hs = db.listar_hallazgos(con, caso_id, entidad_id, tipo)
    campos = ("id", "entidad_id", "dato", "tipo", "estado", "confiabilidad", "fuente", "url", "categoria_alerta",
              "regla_dura", "etapa_judicial", "captura_id", "advertencias")
    return {"total": len(hs), "hallazgos": [{k: h[k] for k in campos} for h in hs]}


@servidor.tool(annotations=SOLO_LECTURA)
def resumen_caso(caso_id: int) -> dict[str, Any]:
    """Estado del caso: entidades, personas, conteos de consultas y hallazgos, semáforo sugerido actual
    y pendientes (hallazgos sin captura, posibles alertas a verificar, brechas)."""
    with db.conectar() as con:
        caso = db.obtener_caso(con, caso_id)
        hs = db.listar_hallazgos(con, caso_id)
        cs = db.listar_consultas(con, caso_id)
        sem = semaforo.calcular(con, caso_id)
        return {
            "caso": {k: caso[k] for k in ("id", "consulta_inicial", "creado_utc", "criterio_version", "modo")},
            "entidades": [{k: e[k] for k in ("id", "razon_social", "tipo", "pais", "identificadores", "rol")}
                          for e in db.listar_entidades(con, caso_id)],
            "personas": [{k: p[k] for k in ("id", "nombre", "cargos")} for p in db.listar_personas(con, caso_id)],
            "consultas": {"total": len(cs), "sin_resultado": sum(c["estado"] == "no_encontrado" for c in cs),
                          "no_accesibles": sum(c["estado"] == "no_accesible" for c in cs)},
            "hallazgos": {t: sum(h["tipo"] == t for h in hs) for t in db.TIPOS_HALLAZGO},
            "sin_captura": [h["id"] for h in hs if h["estado"] in ("encontrado", "parcial") and not h["captura_id"]],
            "semaforo": {"color_sugerido": sem["color_sugerido"], "puntaje": sem["puntaje"],
                         "reglas_duras": len(sem["reglas_duras"]), "tareas": len(sem["tareas_verificacion"]),
                         "brechas": len(sem["brechas"])},
        }


@servidor.tool(annotations=ESCRITURA_LOCAL)
def generar_ficha(caso_id: int, resumen: str | None = None) -> dict[str, Any]:
    """Genera la ficha (Markdown + HTML) y el semáforo sugerido desde la base. `resumen` es opcional y
    cada línea debe citar [H-n] o [C-n]; si alguna no cita un hallazgo existente con URL, se rechaza."""
    try:
        salida = ficha.generar(caso_id, resumen)
        salida["caso_json"] = str(ficha.exportar_caso(caso_id))
        return {"ok": True, **salida}
    except (ficha.ErrorFicha, db.ErrorValidacion) as e:
        return _error(e)


def main() -> None:
    servidor.run("stdio")


if __name__ == "__main__":
    main()
