"""Datos masivos de la DNCP (descargas OCDS por año) para comparar proveedores.

La DNCP publica por año `awa-masivo.zip` (adjudicaciones, ~80 MB) y `con-masivo.zip` (contratos y
pagos, ~40 MB) en https://www.contrataciones.gov.py/images/opendata-v3/final/ocds/<año>/. Cada zip
trae varios CSV (OCDS aplanado con Flatten Tool). Con peticiones HTTP de rango se baja solo el
índice del zip y los CSV necesarios (~4 MB por año), no el archivo entero.

Detalles comprobados (oct. 2026):
- Las tablas se unen por `compiledRelease/id`; adjudicación ↔ contrato por `awards/0/id` = `contracts/0/awardID`.
- Un paquete anual trae registros de años anteriores (el de 2026 tiene adjudicaciones de 2024):
  se deduplica por id de adjudicación, contrato y pago.
- Los montos vienen en la moneda de origen (casi siempre PYG); los indicadores solo suman PYG.
"""

from __future__ import annotations

import csv
import io
import sqlite3
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Iterable, Iterator

import httpx

from . import config
from .ruc import normalizar_ruc

BASE = "https://www.contrataciones.gov.py/images/opendata-v3/final/ocds"
P = "compiledRelease/"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS proceso (
    release_id TEXT PRIMARY KEY, ocid TEXT, titulo TEXT, convocante_id TEXT, convocante TEXT,
    modalidad TEXT, metodo TEXT, categoria TEXT, estimado REAL, moneda_estimado TEXT,
    oferentes INTEGER, inicio_ofertas TEXT, dias_ofertas INTEGER, estado TEXT, anio_paquete INTEGER
);
CREATE TABLE IF NOT EXISTS adjudicacion (
    award_id TEXT PRIMARY KEY, release_id TEXT, fecha TEXT, monto REAL, moneda TEXT, estado TEXT,
    anio_paquete INTEGER
);
CREATE TABLE IF NOT EXISTS adjudicado (
    award_id TEXT, release_id TEXT, ruc TEXT, nombre TEXT, PRIMARY KEY (award_id, ruc)
);
CREATE TABLE IF NOT EXISTS contrato (
    contrato_id TEXT PRIMARY KEY, award_id TEXT, release_id TEXT, firmado TEXT, inicio TEXT, fin TEXT,
    monto REAL, moneda TEXT, estado TEXT
);
CREATE TABLE IF NOT EXISTS pago (
    pago_id TEXT PRIMARY KEY, contrato_id TEXT, fecha TEXT, solicitud TEXT, monto REAL, moneda TEXT,
    pagador_id TEXT, pagador TEXT, ruc TEXT, sistema TEXT
);
CREATE TABLE IF NOT EXISTS item (
    award_id TEXT, n INTEGER, descripcion TEXT, catalogo TEXT, catalogo_desc TEXT, cantidad REAL,
    unidad TEXT, precio_unitario REAL, moneda TEXT, PRIMARY KEY (award_id, n)
);
CREATE TABLE IF NOT EXISTS carga (
    anio INTEGER, paquete TEXT, tabla TEXT, filas INTEGER, fecha_utc TEXT, origen TEXT,
    PRIMARY KEY (anio, paquete, tabla)
);
CREATE INDEX IF NOT EXISTS ix_adjudicado_ruc ON adjudicado(ruc);
CREATE INDEX IF NOT EXISTS ix_adjudicacion_release ON adjudicacion(release_id);
CREATE INDEX IF NOT EXISTS ix_contrato_award ON contrato(award_id);
CREATE INDEX IF NOT EXISTS ix_pago_ruc ON pago(ruc);
CREATE INDEX IF NOT EXISTS ix_item_catalogo ON item(catalogo);
"""


def ruta_base() -> Path:
    return config.dir_fuentes() / "dncp_masivo.sqlite"


def conectar(ruta: Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(ruta or ruta_base(), timeout=60)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


# --- lectura de zips (remotos por rango, o locales) ---------------------------------------

class ZipRemoto:
    """Lee CSV sueltos de un zip remoto con peticiones HTTP de rango."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.cliente = httpx.Client(timeout=180, follow_redirects=True, headers={"User-Agent": config.USER_AGENT})
        self.indice = self._indice()

    def _rango(self, desde: int, hasta: int | None = None) -> bytes:
        r = self.cliente.get(self.url, headers={"Range": f"bytes={desde}-{'' if hasta is None else hasta}"})
        if r.status_code not in (200, 206):
            raise RuntimeError(f"{self.url}: HTTP {r.status_code}")
        return r.content

    def _indice(self) -> dict[str, tuple[int, int, int]]:
        r = self.cliente.get(self.url, headers={"Range": "bytes=-65536"})
        if r.status_code not in (200, 206):
            raise RuntimeError(f"{self.url}: HTTP {r.status_code}")
        cola = r.content
        i = cola.rfind(b"PK\x05\x06")
        if i < 0:
            raise RuntimeError(f"{self.url}: no es un zip o usa ZIP64")
        tam, inicio = struct.unpack("<II", cola[i + 12:i + 20])
        cd, j, indice = self._rango(inicio, inicio + tam - 1), 0, {}
        while cd[j:j + 4] == b"PK\x01\x02":
            metodo, = struct.unpack("<H", cd[j + 10:j + 12])
            comprimido, = struct.unpack("<I", cd[j + 20:j + 24])
            ln, le, lc = struct.unpack("<HHH", cd[j + 28:j + 34])
            local, = struct.unpack("<I", cd[j + 42:j + 46])
            indice[cd[j + 46:j + 46 + ln].decode("utf-8", "replace")] = (metodo, comprimido, local)
            j += 46 + ln + le + lc
        return indice

    def lineas(self, nombre: str, trozo: int = 8 << 20) -> Iterator[str]:
        """Descomprime en streaming (sirve para CSV de cientos de MB)."""
        metodo, comprimido, local = self.indice[nombre]
        cab = self._rango(local, local + 29)
        ln, le = struct.unpack("<HH", cab[26:30])
        desde, fin = local + 30 + ln + le, local + 30 + ln + le + comprimido
        d = zlib.decompressobj(-15) if metodo == 8 else None
        resto = ""
        while desde < fin:
            datos = self._rango(desde, min(desde + trozo, fin) - 1)
            desde += len(datos)
            texto = (d.decompress(datos) if d else datos).decode("utf-8", "replace")
            texto = resto + texto
            partes = texto.split("\n")
            resto = partes.pop()
            yield from (parte + "\n" for parte in partes)
        cola = resto + (d.flush().decode("utf-8", "replace") if d else "")
        if cola:
            yield cola


class ZipLocal:
    def __init__(self, ruta: Path) -> None:
        self.zip = zipfile.ZipFile(ruta)
        self.indice = {n: None for n in self.zip.namelist()}
        self.url = str(ruta)

    def lineas(self, nombre: str) -> Iterator[str]:
        with self.zip.open(nombre) as f:
            yield from io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline="")


def abrir(origen: str | Path) -> ZipRemoto | ZipLocal:
    return ZipRemoto(str(origen)) if str(origen).startswith("http") else ZipLocal(Path(origen))


def filas(z: ZipRemoto | ZipLocal, nombre: str) -> Iterator[dict[str, str]]:
    """CSV como diccionarios (las comillas pueden abarcar varias líneas: csv lo resuelve)."""
    yield from csv.DictReader(z.lineas(nombre))


# --- carga ---------------------------------------------------------------------------------

def _num(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def _int(v: str | None) -> int | None:
    n = _num(v)
    return int(n) if n is not None else None


def _registrar(con: sqlite3.Connection, anio: int, paquete: str, tabla: str, n: int, origen: str) -> None:
    from .db import ahora_utc

    con.execute("INSERT OR REPLACE INTO carga VALUES (?,?,?,?,?,?)", (anio, paquete, tabla, n, ahora_utc(), origen))


def cargar_adjudicaciones(con: sqlite3.Connection, z, anio: int) -> dict[str, int]:
    conteo = {}
    lote = []
    for f in filas(z, "records.csv"):
        lote.append((
            f.get(P + "id"), f.get(P + "ocid"), f.get(P + "tender/title"),
            f.get(P + "tender/procuringEntity/id") or f.get(P + "buyer/id"),
            f.get(P + "tender/procuringEntity/name") or f.get(P + "buyer/name"),
            f.get(P + "tender/procurementMethodDetails"), f.get(P + "tender/procurementMethod"),
            f.get(P + "tender/mainProcurementCategoryDetails"), _num(f.get(P + "tender/value/amount")),
            f.get(P + "tender/value/currency"), _int(f.get(P + "tender/numberOfTenderers")),
            f.get(P + "tender/tenderPeriod/startDate"), _int(f.get(P + "tender/tenderPeriod/durationInDays")),
            f.get(P + "tender/statusDetails"), anio,
        ))
    con.executemany("INSERT OR REPLACE INTO proceso VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", lote)
    conteo["proceso"] = len(lote)

    a = P + "awards/0/"
    lote = [(f.get(a + "id"), f.get(P + "id"), f.get(a + "date"), _num(f.get(a + "value/amount")),
             f.get(a + "value/currency"), f.get(a + "statusDetails") or f.get(a + "status"), anio)
            for f in filas(z, "awards.csv") if f.get(a + "id")]
    con.executemany("INSERT OR REPLACE INTO adjudicacion VALUES (?,?,?,?,?,?,?)", lote)
    conteo["adjudicacion"] = len(lote)

    s = a + "suppliers/0/"
    lote = [(f.get(a + "id"), f.get(P + "id"), normalizar_ruc(f.get(s + "id") or ""), f.get(s + "name"))
            for f in filas(z, "awa_suppliers.csv") if f.get(a + "id")]
    con.executemany("INSERT OR REPLACE INTO adjudicado VALUES (?,?,?,?)", lote)
    conteo["adjudicado"] = len(lote)
    for tabla, n in conteo.items():
        _registrar(con, anio, "awa", tabla, n, z.url)
    return conteo


def cargar_contratos(con: sqlite3.Connection, z, anio: int) -> dict[str, int]:
    c = P + "contracts/0/"
    lote = [(f.get(c + "id"), f.get(c + "awardID"), f.get(P + "id"), f.get(c + "dateSigned"),
             f.get(c + "period/startDate"), f.get(c + "period/endDate"), _num(f.get(c + "value/amount")),
             f.get(c + "value/currency"), f.get(c + "statusDetails") or f.get(c + "status"))
            for f in filas(z, "contracts.csv") if f.get(c + "id")]
    con.executemany("INSERT OR REPLACE INTO contrato VALUES (?,?,?,?,?,?,?,?,?)", lote)
    conteo = {"contrato": len(lote)}
    t = c + "implementation/transactions/0/"
    lote = [(f.get(t + "id"), f.get(c + "id"), f.get(t + "date"), f.get(t + "requestDate"),
             _num(f.get(t + "value/amount")), f.get(t + "value/currency"), f.get(t + "payer/id"),
             f.get(t + "payer/name"), normalizar_ruc(f.get(t + "payee/id") or ""), f.get(t + "sourceSystem"))
            for f in filas(z, "con_imp_transactions.csv") if f.get(t + "id")]
    con.executemany("INSERT OR REPLACE INTO pago VALUES (?,?,?,?,?,?,?,?,?,?)", lote)
    conteo["pago"] = len(lote)
    for tabla, n in conteo.items():
        _registrar(con, anio, "con", tabla, n, z.url)
    return conteo


def cargar_items(con: sqlite3.Connection, z, anio: int, rucs: Iterable[str] | None = None) -> int:
    """Ítems adjudicados con precio unitario. Son ~230 MB por año: se filtra por RUC si se indica."""
    award_ids = None
    if rucs:
        rucs = [normalizar_ruc(r) for r in rucs]
        award_ids = {r[0] for r in con.execute(
            f"SELECT award_id FROM adjudicado WHERE ruc IN ({','.join('?' * len(rucs))})", rucs)}
    a = P + "awards/0/"
    i = a + "items/0/"
    lote, n = [], 0
    for f in filas(z, "awa_items.csv"):
        aid = f.get(a + "id")
        if not aid or (award_ids is not None and aid not in award_ids):
            continue
        lote.append((aid, n, f.get(i + "description"), f.get(i + "classification/id"),
                     f.get(i + "classification/description"), _num(f.get(i + "quantity")),
                     f.get(i + "unit/name"), _num(f.get(i + "unit/value/amount")), f.get(i + "unit/value/currency")))
        n += 1
        if len(lote) >= 5000:
            con.executemany("INSERT OR REPLACE INTO item VALUES (?,?,?,?,?,?,?,?,?)", lote)
            lote = []
    con.executemany("INSERT OR REPLACE INTO item VALUES (?,?,?,?,?,?,?,?,?)", lote)
    _registrar(con, anio, "awa", "item", n, z.url)
    return n


def cargar_anio(anio: int, contratos: bool = True, items_rucs: list[str] | None = None,
                origen_awa: str | Path | None = None, origen_con: str | Path | None = None) -> dict[str, int]:
    con = conectar()
    try:
        z = abrir(origen_awa or f"{BASE}/{anio}/awa-masivo.zip")
        conteo = cargar_adjudicaciones(con, z, anio)
        if items_rucs:
            conteo["item"] = cargar_items(con, z, anio, items_rucs)
        if contratos:
            conteo.update(cargar_contratos(con, abrir(origen_con or f"{BASE}/{anio}/con-masivo.zip"), anio))
        con.commit()
        return conteo
    finally:
        con.close()


def estado() -> dict:
    if not ruta_base().exists():
        return {"disponible": False, "detalle": "Correr `uv run dd descargar-fuentes --dncp-masivo 2020-2026`"}
    con = conectar()
    cargas = [dict(r) for r in con.execute("SELECT * FROM carga ORDER BY anio, paquete, tabla")]
    totales = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
               for t in ("proceso", "adjudicacion", "adjudicado", "contrato", "pago", "item")}
    con.close()
    return {"disponible": True, "anios": sorted({c["anio"] for c in cargas}), "totales": totales, "cargas": cargas}
