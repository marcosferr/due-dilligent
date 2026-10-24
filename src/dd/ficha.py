"""Ficha del proveedor en Markdown y HTML.

La ficha se arma solo desde la base: cada fila sale de un hallazgo con su id. El único texto
libre (el resumen) se valida: toda línea debe citar al menos un hallazgo existente con URL
o una consulta registrada; si no, se rechaza. Así una afirmación sin fuente no llega a la ficha.
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config, db, grafo, semaforo

CITA = re.compile(r"\[(H|C)-(\d+)\]")
COLORES = {"verde": "#1f8a4c", "amarillo": "#c79100", "rojo": "#c0392b"}


class ErrorFicha(ValueError):
    pass


def validar_texto(con: sqlite3.Connection, caso_id: int, texto: str) -> list[str]:
    """Errores del texto libre: líneas sin cita, o citas a hallazgos inexistentes o sin URL."""
    errores = []
    for n, linea in enumerate(texto.splitlines(), 1):
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue
        citas = CITA.findall(limpia)
        if not citas:
            errores.append(f"Línea {n} sin cita [H-n] o [C-n]: {limpia[:80]!r}")
            continue
        for tipo, ident in citas:
            if tipo == "H":
                h = db.obtener_hallazgo(con, int(ident))
                if h is None or h["caso_id"] != caso_id:
                    errores.append(f"Línea {n}: H-{ident} no existe en el caso {caso_id}")
                elif h["estado"] in ("encontrado", "parcial") and not h["url"]:
                    errores.append(f"Línea {n}: H-{ident} no tiene URL")
            else:
                fila = con.execute("SELECT caso_id FROM consulta WHERE id = ?", (int(ident),)).fetchone()
                if fila is None or fila["caso_id"] != caso_id:
                    errores.append(f"Línea {n}: C-{ident} no existe en el caso {caso_id}")
    return errores


# --- bloques intermedios -----------------------------------------------------------------

@dataclass
class Bloque:
    tipo: str  # titulo | sub | parrafo | aviso | lista | tabla | codigo | semaforo
    contenido: Any
    nivel: int = 2


def _enlace(texto: str, url: str | None) -> tuple[str, str | None]:
    return (texto, url)


def _ids(identificadores: dict[str, str]) -> str:
    return ", ".join(f"{k}: {v}" for k, v in identificadores.items()) or "— (sin identificador)"


def construir(con: sqlite3.Connection, caso_id: int, resumen: str | None = None) -> list[Bloque]:
    caso = db.obtener_caso(con, caso_id)
    entidades = db.listar_entidades(con, caso_id)
    personas = db.listar_personas(con, caso_id)
    hallazgos = db.listar_hallazgos(con, caso_id)
    consultas = db.listar_consultas(con, caso_id)
    sem = semaforo.calcular(con, caso_id)
    capturas = {c["id"]: c for c in db._filas(con.execute("SELECT * FROM captura WHERE caso_id = ?", (caso_id,)).fetchall())}
    hay_mock = caso["modo"] == "mock" or any(h["es_mock"] for h in hallazgos) or any(c["es_mock"] for c in consultas)

    b: list[Bloque] = [Bloque("titulo", f"Ficha de due diligence: {caso['consulta_inicial']}", 1)]
    b.append(Bloque("parrafo", (
        f"Caso {caso_id} · creado {caso['creado_utc']} · generado {db.ahora_utc()} · modo {caso['modo']} · "
        f"criterio {caso['criterio_version']} (SHA-256 {caso['criterio_sha256'][:12]}…)"
    )))
    b.append(Bloque("aviso", "Documento interno de trabajo. Solo afirma lo que dice cada fuente, con la etapa de "
                             "cada caso judicial. El semáforo es una sugerencia; la conclusión la firma una persona. "
                             "El proveedor debe poder responder antes de una decisión que lo afecte."))
    if hay_mock:
        b.append(Bloque("aviso", "⚠ CONTIENE DATOS FICTICIOS (modo mock). No usar para ninguna decisión."))
    if "EJEMPLO" in (sem["criterio"].get("estado") or "").upper():
        b.append(Bloque("aviso", "⚠ El criterio de semáforo es el EJEMPLO del documento de diseño: la UNI debe "
                                 "reemplazarlo antes de usar el sistema."))

    # Semáforo
    b.append(Bloque("sub", "Semáforo sugerido"))
    b.append(Bloque("semaforo", sem))
    razones = [
        [_enlace(f"H-{d['hallazgo_id']}", d["url"]), "Regla dura", d["regla"], d["dato"], "—"] for d in sem["reglas_duras"]
    ] + [
        [_enlace(f"H-{c['hallazgo_id']}", c["url"]), c["tipo"], c["categoria"], c["dato"],
         f"{c['severidad']:g} × {c['confianza']:g} = {c['aporte']:g}"]
        for c in sem["contribuciones"]
    ]
    if razones:
        b.append(Bloque("tabla", (["Hallazgo", "Tipo", "Regla / categoría", "Dato", "Aporte"], razones)))
    else:
        b.append(Bloque("parrafo", "Ninguna regla dura ni posible alerta con puntaje en las fuentes consultadas."))

    if resumen:
        errores = validar_texto(con, caso_id, resumen)
        if errores:
            raise ErrorFicha("El resumen tiene líneas sin respaldo:\n- " + "\n- ".join(errores))
        b.append(Bloque("sub", "Resumen (cada línea cita su hallazgo)"))
        b.append(Bloque("parrafo", resumen.strip()))

    # Entidades y personas
    b.append(Bloque("sub", "Entidades resueltas"))
    b.append(Bloque("tabla", (
        ["Id", "Razón social", "Tipo", "País", "Identificadores", "Dominio", "Rol"],
        [[f"E-{e['id']}", e["razon_social"], e["tipo"] or "", e["pais"] or "", _ids(e["identificadores"]),
          e["dominio"] or "", e["rol"]] for e in entidades],
    )))
    if personas:
        b.append(Bloque("sub", "Personas (solo rol público en la empresa o en contratos públicos)"))
        b.append(Bloque("tabla", (
            ["Id", "Nombre", "Cargos"],
            [[f"P-{p['id']}", p["nombre"], ", ".join(p["cargos"])] for p in personas],
        )))

    # Hallazgos por entidad
    b.append(Bloque("sub", "Hallazgos"))
    for e in entidades:
        filas = [h for h in hallazgos if h["entidad_id"] == e["id"] and h["estado"] in ("encontrado", "parcial")]
        if not filas:
            continue
        b.append(Bloque("sub", f"{e['razon_social']} ({_ids(e['identificadores'])})", 3))
        b.append(Bloque("tabla", (
            ["Id", "Dato", "Tipo", "Estado", "Conf.", "Etapa", "Fuente", "Fecha (UTC)", "Captura"],
            [[_enlace(f"H-{h['id']}", h["url"]), h["dato"], h["tipo"], h["estado"], h["confiabilidad"],
              h["etapa_judicial"] or "", f"{h['fuente']} ({h['modo_acceso']})", h["fecha_utc"],
              _texto_captura(capturas.get(h["captura_id"]))] for h in filas],
        )))

    # No encontrado auditable
    vacias = [c for c in consultas if c["estado"] == "no_encontrado"]
    vacios_h = [h for h in hallazgos if h["estado"] == "no_encontrado"]
    b.append(Bloque("sub", "Consultas sin resultado (el «no encontrado» también es un resultado)"))
    if vacias or vacios_h:
        b.append(Bloque("tabla", (
            ["Id", "Fuente", "Consulta exacta", "Fecha (UTC)"],
            [[_enlace(f"C-{c['id']}", c["url"]), c["fuente"], c["consulta"], c["fecha_utc"]] for c in vacias]
            + [[_enlace(f"H-{h['id']}", h["url"]), h["fuente"], h["dato"], h["fecha_utc"]] for h in vacios_h],
        )))
    else:
        b.append(Bloque("parrafo", "No hubo consultas sin resultado."))

    b.append(Bloque("sub", "Brechas de información (no se pudo consultar)"))
    if sem["brechas"]:
        b.append(Bloque("tabla", (
            ["Ref.", "Fuente", "Consulta", "Motivo"],
            [[f"C-{x['consulta_id']}" if "consulta_id" in x else f"H-{x['hallazgo_id']}", x["fuente"], x["consulta"],
              x["detalle"] or ""] for x in sem["brechas"]],
        )))
    else:
        b.append(Bloque("parrafo", "Sin brechas registradas."))

    # Cruces
    llaves = grafo.llaves_compartidas(con, caso_id)
    vinculos = db.listar_vinculos(con, caso_id)
    b.append(Bloque("sub", "Vínculos y llaves compartidas"))
    if vinculos:
        b.append(Bloque("tabla", (
            ["Desde", "Vínculo", "Hacia", "Respaldo"],
            [[_nodo(con, v["desde_tipo"], v["desde_id"]), v["tipo"], _nodo(con, v["hacia_tipo"], v["hacia_id"]),
              _enlace(f"H-{v['hallazgo_id']}", (db.obtener_hallazgo(con, v["hallazgo_id"]) or {}).get("url"))]
             for v in vinculos],
        )))
        b.append(Bloque("codigo", grafo.mapa_mermaid(con, caso_id)))
    if llaves:
        b.append(Bloque("tabla", (
            ["Llave", "Valor", "Entidades"],
            [[k["etiqueta"], k["valor"], "; ".join(f"E-{x['entidad_id']} {x['razon_social']}" for x in k["entidades"])]
             for k in llaves],
        )))
        b.append(Bloque("parrafo", "Una llave compartida es un dato a explicar; no implica irregularidad ni parentesco."))
    if not vinculos and not llaves:
        b.append(Bloque("parrafo", "Sin vínculos ni llaves compartidas registradas."))

    b.append(Bloque("sub", "Tareas de verificación"))
    b.append(Bloque("lista", [f"H-{t['hallazgo_id']}: {t['dato']} — {t['motivo']}" for t in sem["tareas_verificacion"]]
                     or ["Ninguna."]))
    b.append(Bloque("sub", "Qué cambiaría el resultado"))
    b.append(Bloque("lista", sem["que_cambiaria"]))

    # Calidad de la evidencia
    encontrados = [h for h in hallazgos if h["estado"] in ("encontrado", "parcial")]
    completos = [h for h in encontrados if h["url"] and h["fecha_utc"] and h["captura_id"]]
    b.append(Bloque("sub", "Calidad de la evidencia"))
    calidad = [
        f"Hallazgos con URL, fecha y captura: {len(completos)}/{len(encontrados)}",
        f"Consultas registradas: {len(consultas)} ({len(vacias)} sin resultado)",
        "Hallazgos por tipo: " + ", ".join(
            f"{t} {sum(1 for h in encontrados if h['tipo'] == t)}" for t in db.TIPOS_HALLAZGO),
    ]
    advertidos = [h for h in hallazgos if h["advertencias"]]
    calidad += [f"H-{h['id']}: {'; '.join(h['advertencias'])}" for h in advertidos[:20]]
    b.append(Bloque("lista", calidad))

    b.append(Bloque("sub", "Revisión humana"))
    b.append(Bloque("lista", ["Revisado por: ____________________", "Fecha: ____________________",
                              "Conclusión (verde / amarillo / rojo) y motivo: ____________________",
                              "¿Se dio al proveedor la oportunidad de responder? ____"]))
    return b


def _texto_captura(c: dict[str, Any] | None) -> str:
    if not c:
        return "sin captura"
    return f"{c['ruta_imagen'] or c['ruta_html']} (sha256 {c['sha256'][:12]}…)"


def _nodo(con: sqlite3.Connection, tipo: str, ident: int) -> str:
    if tipo == "entidad":
        return f"E-{ident} {db.obtener_entidad(con, ident)['razon_social']}"
    fila = con.execute("SELECT nombre FROM persona WHERE id = ?", (ident,)).fetchone()
    return f"P-{ident} {fila['nombre'] if fila else ''}"


# --- render ------------------------------------------------------------------------------

def _md_celda(v: Any) -> str:
    if isinstance(v, tuple):
        texto, url = v
        return f"[{texto}]({url})" if url else texto
    return str(v).replace("|", "\\|").replace("\n", " ")


def a_markdown(bloques: list[Bloque]) -> str:
    out: list[str] = []
    for bl in bloques:
        if bl.tipo == "titulo":
            out.append(f"# {bl.contenido}\n")
        elif bl.tipo == "sub":
            out.append(f"{'#' * bl.nivel} {bl.contenido}\n")
        elif bl.tipo == "parrafo":
            out.append(f"{bl.contenido}\n")
        elif bl.tipo == "aviso":
            out.append(f"> {bl.contenido}\n")
        elif bl.tipo == "lista":
            out.append("\n".join(f"- {x}" for x in bl.contenido) + "\n")
        elif bl.tipo == "codigo":
            out.append(f"```mermaid\n{bl.contenido}\n```\n")
        elif bl.tipo == "semaforo":
            s = bl.contenido
            out.append(f"**Color sugerido: {s['color_sugerido'].upper()}** · puntaje P = {s['puntaje']:g} "
                       f"(color por puntaje: {s['color_por_puntaje']}; reglas duras activadas: {len(s['reglas_duras'])})\n")
        elif bl.tipo == "tabla":
            cab, filas = bl.contenido
            out.append("| " + " | ".join(cab) + " |")
            out.append("|" + "---|" * len(cab))
            out.extend("| " + " | ".join(_md_celda(c) for c in f) + " |" for f in filas)
            out.append("")
    return "\n".join(out)


def _html_celda(v: Any) -> str:
    if isinstance(v, tuple):
        texto, url = v
        if url and re.match(r"^(https?|mock|demo)://", url):
            return f'<a href="{html.escape(url)}" rel="noopener noreferrer">{html.escape(texto)}</a>'
        return html.escape(texto)
    return html.escape(str(v))


CSS = """
:root{--fg:#1d1d1f;--bg:#fff;--mut:#6b6b70;--bd:#d9d9de;--av:#fff6e0}
@media (prefers-color-scheme:dark){:root{--fg:#ececf0;--bg:#16161a;--mut:#a0a0a8;--bd:#3a3a42;--av:#3a2f12}}
body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--fg);background:var(--bg);
max-width:1100px;margin:0 auto;padding:24px 16px}
h1{font-size:1.6em;margin:.2em 0}h2{margin-top:1.6em;border-bottom:1px solid var(--bd);padding-bottom:.2em}
.meta{color:var(--mut);font-size:.9em}.aviso{background:var(--av);border-left:4px solid #c79100;padding:8px 12px;margin:8px 0}
.tabla{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.88em}
th,td{border:1px solid var(--bd);padding:4px 6px;vertical-align:top;text-align:left}th{background:rgba(127,127,127,.12)}
.sem{display:inline-block;padding:6px 14px;border-radius:999px;color:#fff;font-weight:700;letter-spacing:.04em}
pre{background:rgba(127,127,127,.12);padding:10px;overflow-x:auto;font-size:.85em}
a{color:inherit}
"""


def a_html(bloques: list[Bloque]) -> str:
    titulo = next((bl.contenido for bl in bloques if bl.tipo == "titulo"), "Ficha")
    cabecera = ("<!doctype html><html lang='es'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>{html.escape(titulo)}</title><style>{CSS}</style></head><body>")
    out = [cabecera]
    primer_parrafo = True
    for bl in bloques:
        if bl.tipo == "titulo":
            out.append(f"<h1>{html.escape(bl.contenido)}</h1>")
        elif bl.tipo == "sub":
            out.append(f"<h{bl.nivel}>{html.escape(bl.contenido)}</h{bl.nivel}>")
        elif bl.tipo == "parrafo":
            clase = " class='meta'" if primer_parrafo else ""
            primer_parrafo = False
            texto = html.escape(bl.contenido).replace("\n", "<br>")
            out.append(f"<p{clase}>{texto}</p>")
        elif bl.tipo == "aviso":
            out.append(f"<div class='aviso'>{html.escape(bl.contenido)}</div>")
        elif bl.tipo == "lista":
            out.append("<ul>" + "".join(f"<li>{html.escape(str(x))}</li>" for x in bl.contenido) + "</ul>")
        elif bl.tipo == "codigo":
            out.append(f"<details><summary>Mapa de vínculos (Mermaid)</summary><pre>{html.escape(bl.contenido)}</pre></details>")
        elif bl.tipo == "semaforo":
            s = bl.contenido
            color = COLORES.get(s["color_sugerido"], "#555")
            out.append(f"<p><span class='sem' style='background:{color}'>{s['color_sugerido'].upper()}</span> "
                       f"&nbsp;Puntaje P = {s['puntaje']:g} · color por puntaje: {s['color_por_puntaje']} · "
                       f"reglas duras activadas: {len(s['reglas_duras'])} · <em>sugerencia, no conclusión</em></p>")
        elif bl.tipo == "tabla":
            cab, filas = bl.contenido
            out.append("<div class='tabla'><table><thead><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cab)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{_html_celda(c)}</td>" for c in f) + "</tr>" for f in filas)
                       + "</tbody></table></div>")
    out.append("</body></html>")
    return "\n".join(out)


def generar(caso_id: int, resumen: str | None = None) -> dict[str, Any]:
    with db.conectar() as con:
        bloques = construir(con, caso_id, resumen)
        sem = semaforo.calcular(con, caso_id)
        con.execute("UPDATE caso SET ficha_generada_utc = ? WHERE id = ?", (db.ahora_utc(), caso_id))
    carpeta = config.dir_casos() / f"caso-{caso_id}"
    carpeta.mkdir(parents=True, exist_ok=True)
    md, htm = carpeta / "ficha.md", carpeta / "ficha.html"
    md.write_text(a_markdown(bloques), encoding="utf-8")
    htm.write_text(a_html(bloques), encoding="utf-8")
    (carpeta / "semaforo.json").write_text(json.dumps(sem, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"markdown": str(md), "html": str(htm), "color_sugerido": sem["color_sugerido"], "puntaje": sem["puntaje"]}


def exportar_caso(caso_id: int) -> Path:
    """Vuelca todas las tablas del caso a JSON (para auditoría y evaluación)."""
    with db.conectar() as con:
        datos = {
            "caso": db.obtener_caso(con, caso_id),
            "entidades": db.listar_entidades(con, caso_id),
            "personas": db.listar_personas(con, caso_id),
            "consultas": db.listar_consultas(con, caso_id),
            "hallazgos": db.listar_hallazgos(con, caso_id),
            "vinculos": db.listar_vinculos(con, caso_id),
            "capturas": db._filas(con.execute("SELECT * FROM captura WHERE caso_id = ?", (caso_id,)).fetchall()),
        }
    ruta = config.dir_casos() / f"caso-{caso_id}" / "caso.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
