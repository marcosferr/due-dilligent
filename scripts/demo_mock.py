"""Demo determinista del flujo completo con datos FICTICIOS (sin LLM y sin red).

Recorre lo que haría el agente para "Beta Ficticia" llamando a las mismas herramientas MCP:
resolución de entidad, DNCP, competidores, sanciones, brechas, cruces y ficha.

    DD_MODO=mock uv run python scripts/demo_mock.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

os.environ["DD_MODO"] = "mock"

from dd.servers import dncp, evidencia, grafo, registros, sanciones  # noqa: E402


def t(servidor, herramienta, **args):
    r = asyncio.run(servidor.call_tool(herramienta, args))
    datos = json.loads(r.content[0].text)
    if isinstance(datos, dict) and datos.get("ok") is False:
        sys.exit(f"{herramienta}: {datos['error']}")
    return datos


def hallazgo(caso, ent, consulta, url, **kw):
    cap = t(evidencia.servidor, "capturar", caso_id=caso, url=url)
    return t(evidencia.servidor, "registrar_hallazgo", caso_id=caso, entidad_id=ent, url=url,
             consulta_id=consulta, captura_id=cap["captura_id"], modo_acceso="mock", **kw)["hallazgo_id"]


def main() -> None:
    caso = t(evidencia.servidor, "crear_caso", consulta_inicial="Beta Ficticia")["caso_id"]
    print(f"Caso {caso}")

    # 1. Resolución de entidad: variantes en la DNCP (nombre de fantasía y razón social)
    variantes = t(registros.servidor, "variantes_nombre", nombre="Beta Ficticia S.R.L.")["variantes"]
    for v in variantes[:3]:
        t(dncp.servidor, "buscar_proveedores", caso_id=caso, nombre=v)
        t(dncp.servidor, "buscar_procesos", caso_id=caso, nombre_proveedor=v)
    prov = t(dncp.servidor, "buscar_proveedores", caso_id=caso, nombre="Beta")
    p = prov["resultado"]["proveedores"][0]
    beta = t(evidencia.servidor, "registrar_entidad", caso_id=caso, razon_social=p["razon_social"], tipo="S.R.L.",
             pais="PY", identificadores={"RUC": p["ruc"]}, variantes=variantes,
             telefonos=[p["contacto"]["telefono"]], correos=[p["contacto"]["correo"]],
             direcciones=[p["direccion"]])["entidad_id"]

    # 2. Contrataciones
    det = t(dncp.servidor, "obtener_proveedor", caso_id=caso, ruc=p["ruc"])
    url = det["evidencia"]["url"]
    h_id = hallazgo(caso, beta, det["consulta_id"], url, dato=f"Proveedor DNCP {p['razon_social']} (RUC {p['ruc']})",
                    fuente="DNCP API v3", confiabilidad="A", tipo="hecho", estado="encontrado",
                    identificador_que_ata=f"RUC {p['ruc']}")
    s = det["resultado"]["sanciones"][0]
    h_inh = hallazgo(caso, beta, det["consulta_id"], url, dato=f"Inhabilitación vigente en la DNCP ({s['inicio'][:10]} a {s['fin'][:10]})",
                     extracto=s["descripcion"], fuente="DNCP API v3", confiabilidad="A", tipo="hecho",
                     estado="encontrado", identificador_que_ata=f"RUC {p['ruc']}",
                     regla_dura="inhabilitacion_dncp_vigente")
    procs = t(dncp.servidor, "buscar_procesos", caso_id=caso, ruc_proveedor=p["ruc"])
    hallazgo(caso, beta, procs["consulta_id"], procs["evidencia"]["url"],
             dato=f"{procs['resultado']['total']} proceso(s) adjudicado(s) en la DNCP", fuente="DNCP API v3",
             confiabilidad="A", tipo="contexto", estado="encontrado", identificador_que_ata=f"RUC {p['ruc']}")

    # 3. Competidores: Alfa compitió contra Beta en ocds-mock-1001 y 1002
    rec = t(dncp.servidor, "obtener_record_ocds", caso_id=caso, ocid="ocds-mock-1002")
    alfa_ruc = next(x["id"] for x in rec["resultado"]["partes"] if x["nombre"].startswith("ALFA")).replace("PY-RUC-", "")
    alfa_det = t(dncp.servidor, "obtener_proveedor", caso_id=caso, ruc=alfa_ruc)
    a = alfa_det["resultado"]
    alfa = t(evidencia.servidor, "registrar_entidad", caso_id=caso, razon_social=a["razon_social"], tipo="S.A.",
             pais="PY", identificadores={"RUC": a["ruc"]}, telefonos=[a["contacto"]["telefono"]],
             correos=[a["contacto"]["correo"]], direcciones=[a["direccion"]], rol="competidor")["entidad_id"]
    h_comp = hallazgo(caso, beta, rec["consulta_id"], rec["evidencia"]["url"],
                      dato=f"Compitió contra {a['razon_social']} en ocds-mock-1002 (3 oferentes)",
                      fuente="DNCP API v3", confiabilidad="A", tipo="contexto", estado="encontrado",
                      identificador_que_ata=f"RUC {p['ruc']} y RUC {a['ruc']}")
    t(grafo.servidor, "agregar_vinculo", caso_id=caso, desde_tipo="entidad", desde_id=beta, tipo="compitio_contra",
      hacia_tipo="entidad", hacia_id=alfa, hallazgo_id=h_comp)

    # 4. Cruces: llave compartida
    llaves = t(grafo.servidor, "llaves_compartidas", caso_id=caso)["llaves"]
    for k in llaves:
        h_tel = hallazgo(caso, beta, alfa_det["consulta_id"], alfa_det["evidencia"]["url"],
                         dato=f"Mismo {k['etiqueta']} ({k['valor']}) que {a['razon_social']}, competidora en los mismos procesos",
                         fuente="DNCP API v3", confiabilidad="A", tipo="hecho", estado="encontrado",
                         identificador_que_ata=f"RUC {p['ruc']} y RUC {a['ruc']}",
                         categoria_alerta="llave_compartida_competidor")
        t(grafo.servidor, "agregar_vinculo", caso_id=caso, desde_tipo="entidad", desde_id=beta,
          tipo="mismo_telefono", hacia_tipo="entidad", hacia_id=alfa, hallazgo_id=h_tel)

    # 5. Sanciones
    scr = t(sanciones.servidor, "screen_entidad", caso_id=caso, nombre=p["razon_social"], identificadores=[p["ruc"]])
    c = scr["resultado"]["candidatos"][0]
    h_scr = hallazgo(caso, beta, scr["consulta_id"], c["url"], dato=f"Figura en lista de sanciones ({c['dataset']}): {c['sanciones']}",
             extracto=f"Coincide identificador {c['identificadores_registro']}", fuente=c["fuente"],
             confiabilidad="B", tipo="hecho", estado="encontrado", identificador_que_ata=f"RUC {p['ruc']}",
             regla_dura="sancion_confirmada_por_identificador")
    t(sanciones.servidor, "screen_entidad", caso_id=caso, nombre=a["razon_social"], identificadores=[a["ruc"]])

    # 6. Brechas
    t(registros.servidor, "registro_solo_web", caso_id=caso, registro="py_poder_judicial",
      consulta=f"Expedientes de {p['razon_social']}")
    t(registros.servidor, "dnit_buscar_ruc", caso_id=caso, ruc=p["ruc"])
    prensa = t(evidencia.servidor, "registrar_consulta", caso_id=caso, fuente="Búsqueda web",
               consulta='"Beta Ficticia" site:abc.com.py', n_resultados=0, modo_acceso="mock")["consulta_id"]

    # 7. Ficha
    resumen = "\n".join([
        f"{p['razon_social']} (RUC {p['ruc']}) figura como proveedora en la DNCP [H-{h_id}].",
        f"Tiene una inhabilitación vigente por fechas en la DNCP [H-{h_inh}].",
        f"Compitió contra {a['razon_social']} [H-{h_comp}] y comparte con ella un teléfono [H-{h_tel}].",
        f"Figura en la lista de sanciones de demo con su RUC [H-{h_scr}].",
        f"La búsqueda de prensa no devolvió resultados [C-{prensa}].",
    ])
    f = t(evidencia.servidor, "generar_ficha", caso_id=caso, resumen=resumen)
    print(json.dumps(f, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
