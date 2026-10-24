"""Cruces: llaves compartidas entre entidades y mapa de vínculos.

Teléfonos, correos, dominios, direcciones y personas son llaves de cruce. Que dos entidades
compartan una llave es un dato a explicar, no una irregularidad: el sistema lo muestra con
su fuente y no lo califica.
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from typing import Any

from . import db
from .variantes import normalizar, quitar_acentos


def norm_telefono(t: str) -> str:
    digitos = re.sub(r"\D", "", t or "")
    if digitos.startswith("595"):
        digitos = digitos[3:]
    return digitos.lstrip("0")


def norm_correo(c: str) -> str:
    return (c or "").strip().lower()


def dominio_de(valor: str) -> str:
    valor = (valor or "").strip().lower()
    if "@" in valor:
        valor = valor.split("@", 1)[1]
    valor = re.sub(r"^(https?://)?(www\.)?", "", valor)
    return valor.split("/")[0]


ETIQUETAS = {"telefono": "teléfono", "correo": "correo", "dominio": "dominio", "direccion": "dirección",
             "persona": "persona"}

GENERICOS = {"gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "live.com", "icloud.com", "yahoo.com.ar",
             "hotmail.es", "tigo.com.py", "personal.com.py"}


def norm_direccion(d: str) -> str:
    texto = quitar_acentos(d or "").upper()
    texto = re.sub(r"\b(C/|CASI|ESQ\.?|ESQUINA|N[°º]|NRO\.?|NUMERO)\b", " ", texto)
    return re.sub(r"[^A-Z0-9]+", " ", texto).strip()


def llaves_de(entidad: dict[str, Any]) -> dict[str, set[str]]:
    llaves: dict[str, set[str]] = defaultdict(set)
    for t in entidad.get("telefonos") or []:
        if len(norm_telefono(t)) >= 6:
            llaves["telefono"].add(norm_telefono(t))
    for c in entidad.get("correos") or []:
        if "@" in c:
            llaves["correo"].add(norm_correo(c))
            dom = dominio_de(c)
            if dom not in GENERICOS:
                llaves["dominio"].add(dom)
    if entidad.get("dominio"):
        llaves["dominio"].add(dominio_de(entidad["dominio"]))
    for d in entidad.get("direcciones") or []:
        if len(norm_direccion(d)) >= 8:
            llaves["direccion"].add(norm_direccion(d))
    return llaves


def llaves_compartidas(con: sqlite3.Connection, caso_id: int, entre_casos: bool = False) -> list[dict[str, Any]]:
    """Llaves (teléfono, correo, dominio, dirección, persona) repetidas entre entidades distintas.

    Con `entre_casos` se compara contra entidades de todos los casos de la base, útil para
    detectar competidores o proveedores vistos antes que comparten datos de contacto.
    """
    if entre_casos:
        entidades = db._filas(con.execute("SELECT * FROM entidad").fetchall())
    else:
        entidades = db.listar_entidades(con, caso_id)
    indice: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for e in entidades:
        for tipo, valores in llaves_de(e).items():
            for v in valores:
                indice[(tipo, v)].append(e)

    personas = db._filas(con.execute(
        "SELECT p.nombre, v.hacia_id AS entidad_id, v.tipo AS rol, p.caso_id FROM vinculo v"
        " JOIN persona p ON v.desde_tipo = 'persona' AND v.desde_id = p.id WHERE v.hacia_tipo = 'entidad'"
        + ("" if entre_casos else " AND v.caso_id = ?"),
        () if entre_casos else (caso_id,),
    ).fetchall())
    por_id = {e["id"]: e for e in entidades}
    for p in personas:
        if p["rol"] == "agente_registrado":
            continue  # un agente de servicios corporativos no es persona vinculada
        if p["entidad_id"] in por_id:
            indice[("persona", normalizar(p["nombre"], quitar_forma=False))].append(por_id[p["entidad_id"]])

    salida = []
    for (tipo, valor), ents in sorted(indice.items()):
        distintas = {e["id"]: e for e in ents}
        if len(distintas) < 2:
            continue
        if not any(e["caso_id"] == caso_id for e in distintas.values()):
            continue
        salida.append({
            "llave": tipo,
            "etiqueta": ETIQUETAS.get(tipo, tipo),
            "valor": valor,
            "entidades": [
                {"entidad_id": e["id"], "caso_id": e["caso_id"], "razon_social": e["razon_social"],
                 "identificadores": e["identificadores"], "rol": e["rol"]}
                for e in distintas.values()
            ],
            "nota": "Llave compartida: dato a explicar, no implica irregularidad ni parentesco",
        })
    return salida


def vecinos(con: sqlite3.Connection, caso_id: int, nodo_tipo: str, nodo_id: int) -> list[dict[str, Any]]:
    filas = db._filas(con.execute(
        "SELECT * FROM vinculo WHERE caso_id = ? AND ((desde_tipo = ? AND desde_id = ?) OR (hacia_tipo = ? AND hacia_id = ?))",
        (caso_id, nodo_tipo, nodo_id, nodo_tipo, nodo_id),
    ).fetchall())
    return filas


def _etiqueta(con: sqlite3.Connection, tipo: str, ident: int) -> str:
    if tipo == "entidad":
        e = db.obtener_entidad(con, ident)
        ids = ", ".join(f"{k} {v}" for k, v in e["identificadores"].items())
        return f"{e['razon_social']}" + (f"<br/>{ids}" if ids else "")
    fila = con.execute("SELECT nombre FROM persona WHERE id = ?", (ident,)).fetchone()
    return fila["nombre"] if fila else f"persona {ident}"


def mapa_mermaid(con: sqlite3.Connection, caso_id: int) -> str:
    """Mapa de vínculos en Mermaid; cada arista lleva el id del hallazgo que la respalda."""
    vinculos = db.listar_vinculos(con, caso_id)
    if not vinculos:
        return ""
    lineas = ["graph LR"]
    nodos: set[tuple[str, int]] = set()
    for v in vinculos:
        nodos.add((v["desde_tipo"], v["desde_id"]))
        nodos.add((v["hacia_tipo"], v["hacia_id"]))
    for tipo, ident in sorted(nodos):
        etiqueta = _etiqueta(con, tipo, ident).replace('"', "'")
        forma = ('["', '"]') if tipo == "entidad" else ('(["', '"])')
        lineas.append(f'  {tipo[0].upper()}{ident}{forma[0]}{etiqueta}{forma[1]}')
    for v in vinculos:
        lineas.append(
            f'  {v["desde_tipo"][0].upper()}{v["desde_id"]} -- "{v["tipo"]} [H-{v["hallazgo_id"]}]" --> '
            f'{v["hacia_tipo"][0].upper()}{v["hacia_id"]}'
        )
    return "\n".join(lineas)
