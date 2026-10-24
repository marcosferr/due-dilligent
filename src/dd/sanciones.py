"""Índice local de sanciones, PEP e inhabilitaciones para screening por nombre e identificador.

Fuentes (descarga en bloque con `dd descargar-fuentes`):
- OpenSanctions `targets.simple.csv` de las colecciones `sanctions` y `debarment`
  (incluye Banco Mundial, SAM.gov y más). Uso no comercial, CC BY-NC 4.0.
- OFAC `SDN.CSV` (Sanctions List Service).

Una coincidencia solo por nombre es una posible alerta, nunca un hecho: hace falta que un
identificador (RUC, registro, documento) coincida para confirmarla.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

from . import config
from .variantes import normalizar, similitud

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS registro (
    id INTEGER PRIMARY KEY,
    fuente TEXT NOT NULL,
    ref TEXT NOT NULL,
    dataset TEXT,
    esquema TEXT,
    nombre TEXT NOT NULL,
    alias TEXT,
    paises TEXT,
    identificadores TEXT,
    sanciones TEXT,
    fecha_nacimiento TEXT,
    ultima_modificacion TEXT
);
CREATE TABLE IF NOT EXISTS token (tok TEXT NOT NULL, registro_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor TEXT);
"""

# Palabras demasiado comunes para usarlas como llave de búsqueda.
VACIAS = {"DE", "DEL", "LA", "EL", "LOS", "LAS", "Y", "AND", "THE", "OF", "CO", "COMPANY", "GROUP", "GRUPO",
          "INTERNATIONAL", "SERVICIOS", "SERVICES", "TRADING", "HOLDING", "HOLDINGS", "PARAGUAY", "BANK"}

PERSONAS = {"Person"}


def ruta_indice(demo: bool = False) -> Path:
    return config.dir_fuentes() / ("sanciones-demo.sqlite" if demo else "sanciones.sqlite")


def _tokens(nombre: str) -> set[str]:
    return {t for t in normalizar(nombre).split() if len(t) > 2 and t not in VACIAS}


def _solo_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def _filas_opensanctions(ruta: Path) -> Iterable[dict[str, str]]:
    with open(ruta, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            yield {
                "fuente": "OpenSanctions",
                "ref": fila.get("id", ""),
                "dataset": fila.get("dataset", ""),
                "esquema": fila.get("schema", ""),
                "nombre": fila.get("name", ""),
                "alias": fila.get("aliases", ""),
                "paises": fila.get("countries", ""),
                "identificadores": fila.get("identifiers", ""),
                "sanciones": fila.get("sanctions", ""),
                "fecha_nacimiento": fila.get("birth_date", ""),
                "ultima_modificacion": fila.get("last_change", ""),
            }


def _filas_ofac(ruta: Path) -> Iterable[dict[str, str]]:
    """SDN.CSV no trae encabezado: ent_num, nombre, tipo, programa, ..., observaciones (12 columnas)."""
    with open(ruta, encoding="latin-1", newline="") as f:
        for fila in csv.reader(f):
            if len(fila) < 4:
                continue
            limpio = [("" if c.strip() == "-0-" else c.strip()) for c in fila]
            observaciones = limpio[11] if len(limpio) > 11 else ""
            alias = ";".join(re.findall(r"a\.k\.a\. '([^']+)'", observaciones))
            yield {
                "fuente": "OFAC SDN",
                "ref": limpio[0],
                "dataset": "us_ofac_sdn",
                "esquema": "Person" if limpio[2].lower() == "individual" else "LegalEntity",
                "nombre": limpio[1],
                "alias": alias,
                "paises": "",
                "identificadores": observaciones[:500],
                "sanciones": limpio[3],
                "fecha_nacimiento": "",
                "ultima_modificacion": "",
            }


def construir_indice(archivos: list[tuple[str, Path]], destino: Path) -> dict[str, int]:
    """archivos: [("opensanctions" | "ofac", ruta)]. Reconstruye el índice desde cero."""
    if destino.exists():
        destino.unlink()
    con = sqlite3.connect(destino)
    con.executescript(ESQUEMA)
    conteo: dict[str, int] = {}
    for formato, ruta in archivos:
        lector = _filas_opensanctions if formato == "opensanctions" else _filas_ofac
        n = 0
        for fila in lector(ruta):
            if not fila["nombre"]:
                continue
            cur = con.execute(
                "INSERT INTO registro (fuente, ref, dataset, esquema, nombre, alias, paises, identificadores,"
                " sanciones, fecha_nacimiento, ultima_modificacion) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                tuple(fila[k] for k in ("fuente", "ref", "dataset", "esquema", "nombre", "alias", "paises",
                                        "identificadores", "sanciones", "fecha_nacimiento", "ultima_modificacion")),
            )
            toks: set[str] = set()
            for nombre in [fila["nombre"], *fila["alias"].split(";")]:
                toks |= _tokens(nombre)
            con.executemany("INSERT INTO token (tok, registro_id) VALUES (?, ?)", [(t, cur.lastrowid) for t in toks])
            n += 1
        conteo[f"{formato}:{ruta.name}"] = n
    con.execute("CREATE INDEX IF NOT EXISTS ix_token ON token(tok)")
    from .db import ahora_utc

    con.execute("INSERT OR REPLACE INTO meta VALUES ('construido_utc', ?)", (ahora_utc(),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('archivos', ?)", (json.dumps(conteo),))
    con.commit()
    con.close()
    return conteo


def indice_disponible(demo: bool) -> Path | None:
    ruta = ruta_indice(demo)
    if demo and not ruta.exists():
        construir_indice([("opensanctions", config.DIR_MUESTRAS / "sanciones_demo.csv")], ruta)
    return ruta if ruta.exists() else None


def estado_indice(demo: bool) -> dict[str, Any]:
    ruta = indice_disponible(demo)
    if not ruta:
        return {"disponible": False, "detalle": "Índice no construido: correr `uv run dd descargar-fuentes`"}
    con = sqlite3.connect(ruta)
    meta = dict(con.execute("SELECT clave, valor FROM meta").fetchall())
    total = con.execute("SELECT COUNT(*) FROM registro").fetchone()[0]
    por_fuente = dict(con.execute("SELECT fuente, COUNT(*) FROM registro GROUP BY fuente").fetchall())
    con.close()
    return {"disponible": True, "demo": demo, "registros": total, "por_fuente": por_fuente,
            "construido_utc": meta.get("construido_utc"), "archivos": json.loads(meta.get("archivos", "{}"))}


def screen(
    nombre: str,
    *,
    persona: bool = False,
    identificadores: list[str] | None = None,
    fecha_nacimiento: str | None = None,
    umbral: float = 0.82,
    limite: int = 10,
    demo: bool = False,
) -> dict[str, Any]:
    """Busca candidatos en el índice y devuelve puntaje y campos coincidentes de cada uno."""
    ruta = indice_disponible(demo)
    if not ruta:
        raise FileNotFoundError("Índice de sanciones no construido: correr `uv run dd descargar-fuentes`")
    toks = _tokens(nombre)
    if not toks:
        return {"consulta": nombre, "candidatos": [], "nota": "Nombre sin términos distintivos para buscar"}
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    marcas = ",".join("?" * len(toks))
    ids = [r[0] for r in con.execute(
        f"SELECT registro_id, COUNT(*) c FROM token WHERE tok IN ({marcas}) GROUP BY registro_id"
        " ORDER BY c DESC LIMIT 2000",
        list(toks),
    ).fetchall()]
    buscados = [_solo_digitos(i) for i in identificadores or [] if len(_solo_digitos(i)) >= 5]
    candidatos = []
    for i in range(0, len(ids), 500):
        lote = ids[i:i + 500]
        filas = con.execute(f"SELECT * FROM registro WHERE id IN ({','.join('?' * len(lote))})", lote).fetchall()
        for r in filas:
            es_persona = r["esquema"] in PERSONAS
            if persona != es_persona and r["esquema"] not in ("", "Thing", "LegalEntity"):
                continue
            nombres = [r["nombre"], *[a for a in (r["alias"] or "").split(";") if a]]
            mejor, mejor_nombre = 0.0, r["nombre"]
            for n in nombres:
                s = similitud(nombre, n)
                if s > mejor:
                    mejor, mejor_nombre = s, n
            if mejor < umbral:
                continue
            ids_registro = _solo_digitos(r["identificadores"] or "")
            coincide_id = any(b in ids_registro for b in buscados) if buscados else False
            campos = ["nombre" if mejor_nombre == r["nombre"] else "alias"]
            if coincide_id:
                campos.append("identificador")
            if fecha_nacimiento and r["fecha_nacimiento"] and fecha_nacimiento[:4] in r["fecha_nacimiento"]:
                campos.append("fecha_nacimiento")
            candidatos.append({
                "puntaje": mejor,
                "nombre_coincidente": mejor_nombre,
                "campos_coincidentes": campos,
                "coincide_identificador": coincide_id,
                "fuente": "DEMO (ficticio)" if demo else r["fuente"],
                "dataset": r["dataset"],
                "ref": r["ref"],
                "url": f"demo://sanciones/{r['ref']}" if demo else url_registro(r["fuente"], r["ref"]),
                "esquema": r["esquema"],
                "paises": r["paises"],
                "sanciones": (r["sanciones"] or "")[:300],
                "identificadores_registro": (r["identificadores"] or "")[:200],
                "es_demo": demo,
            })
    con.close()
    candidatos.sort(key=lambda c: (c["coincide_identificador"], c["puntaje"]), reverse=True)
    return {
        "consulta": nombre,
        "tokens": sorted(toks),
        "umbral": umbral,
        "candidatos": candidatos[:limite],
        "regla": "Sin coincide_identificador = posible_alerta (homónimo posible), nunca hecho",
    }


def url_registro(fuente: str, ref: str) -> str:
    if fuente == "OpenSanctions":
        return f"https://www.opensanctions.org/entities/{ref}/"
    if fuente == "OFAC SDN":
        return f"https://sanctionssearch.ofac.treas.gov/Details.aspx?id={ref}"
    return f"demo://sanciones/{ref}"
