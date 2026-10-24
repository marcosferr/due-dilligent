"""Prueba de punta a punta de las herramientas MCP en modo mock (sin red)."""

import asyncio
import json

from dd.servers import dncp, evidencia, grafo, registros, sanciones


def llamar(servidor, herramienta, **args):
    r = asyncio.run(servidor.call_tool(herramienta, args))
    return json.loads(r.content[0].text)


def test_flujo_completo_mock():
    caso = llamar(evidencia.servidor, "crear_caso", consulta_inicial="Beta Ficticia")["caso_id"]

    vacia = llamar(dncp.servidor, "buscar_proveedores", caso_id=caso, nombre="Beta Ficticia S.R.L.")
    assert vacia["estado"] == "no_encontrado" and "MOCK" in vacia

    prov = llamar(dncp.servidor, "buscar_proveedores", caso_id=caso, nombre="Beta")
    p = prov["resultado"]["proveedores"][0]
    assert p["sanciones"][0]["vigente_por_fechas"]

    ent = llamar(evidencia.servidor, "registrar_entidad", caso_id=caso, razon_social=p["razon_social"],
                 tipo="S.R.L.", pais="PY", identificadores={"RUC": p["ruc"]}, telefonos=[p["contacto"]["telefono"]])
    cap = llamar(evidencia.servidor, "capturar", caso_id=caso, url=prov["evidencia"]["url"])
    assert cap["ok"] and len(cap["sha256"]) == 64

    h = llamar(evidencia.servidor, "registrar_hallazgo", caso_id=caso, entidad_id=ent["entidad_id"],
               dato="Inhabilitación vigente en la DNCP", fuente="DNCP API v3", confiabilidad="A", tipo="hecho",
               estado="encontrado", modo_acceso="mock", url=prov["evidencia"]["url"],
               identificador_que_ata=f"RUC {p['ruc']}", regla_dura="inhabilitacion_dncp_vigente",
               consulta_id=prov["consulta_id"], captura_id=cap["captura_id"])
    assert h["ok"] and h["tipo_guardado"] == "hecho"

    scr = llamar(sanciones.servidor, "screen_entidad", caso_id=caso, nombre=p["razon_social"],
                 identificadores=[p["ruc"]])
    assert scr["resultado"]["candidatos"][0]["coincide_identificador"]

    brecha = llamar(registros.servidor, "registro_extranjero", caso_id=caso, nombre="Beta Ficticia LLC",
                    jurisdiccion="us_nv")
    assert brecha["estado"] == "no_accesible" and "registro_oficial" in brecha

    assert llamar(registros.servidor, "dnit_validar_ruc", ruc="80900002")["ruc_completo"] == "80900002-4"
    assert "Integralis LLC" in llamar(registros.servidor, "variantes_nombre", nombre="Integralis S.A.",
                                      formas_extra=["LLC"])["variantes"]

    v = llamar(grafo.servidor, "agregar_vinculo", caso_id=caso, desde_tipo="entidad", desde_id=ent["entidad_id"],
               tipo="parentesco", hacia_tipo="entidad", hacia_id=ent["entidad_id"], hallazgo_id=h["hallazgo_id"])
    assert v["ok"] is False

    resumen = llamar(evidencia.servidor, "resumen_caso", caso_id=caso)
    assert resumen["semaforo"]["color_sugerido"] == "rojo"
    assert resumen["consultas"]["sin_resultado"] >= 1 and resumen["consultas"]["no_accesibles"] >= 1

    f = llamar(evidencia.servidor, "generar_ficha", caso_id=caso,
               resumen=f"Inhabilitación vigente en la DNCP [H-{h['hallazgo_id']}].")
    assert f["ok"] and f["color_sugerido"] == "rojo"


def test_herramientas_declaradas():
    nombres = {t.name for t in asyncio.run(dncp.servidor.list_tools())}
    assert {"buscar_proveedores", "obtener_proveedor", "buscar_procesos", "obtener_record_ocds"} <= nombres
