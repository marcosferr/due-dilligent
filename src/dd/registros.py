"""Registros de identidad: DNIT (RUC), OpenCorporates, SAM.gov y registros solo web.

Regla de la guía: lo que pide pago, usuario o trámite presencial se registra como brecha
con lo que pidió; no se pagan servicios ni se crean cuentas.
"""

from __future__ import annotations

import io
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

from . import config
from .http import get
from .ruc import calcular_dv, normalizar_ruc, separar
from .variantes import normalizar

URL_DNIT_LISTADO = "https://www.dnit.gov.py/web/portal-institucional/listado-de-ruc-con-sus-equivalencias"
URL_OPENCORPORATES = "https://api.opencorporates.com/v0.4"
URL_SAM_EXCLUSIONES = "https://api.sam.gov/entity-information/v4/exclusions"

# Registros sin API: siempre brecha, con instrucciones para la consulta manual o por navegador.
REGISTROS_SOLO_WEB = {
    "us_nv": {
        "nombre": "Nevada Secretary of State – Business Search",
        "url": "https://esos.nv.gov/EntitySearch/OnlineEntitySearch",
        "nota": "Solo web. El portal está en transición (SilverFlume → ORION según guías de terceros):"
                " verificar la URL vigente. Agente registrado ≠ dueño.",
    },
    "py_registros_publicos": {
        "nombre": "Dirección General de los Registros Públicos (Paraguay)",
        "url": "https://www.pj.gov.py/",
        "nota": "Inscripción de sociedades y sucursales extranjeras: trámite presencial o con usuario.",
    },
    "py_poder_judicial": {
        "nombre": "Poder Judicial – consulta de expedientes",
        "url": "https://www.csj.gov.py/",
        "nota": "Sin API conocida. Navegador solo si los términos de uso lo permiten.",
    },
}


def ruta_dnit() -> Path:
    return config.dir_fuentes() / "dnit_ruc.sqlite"


def descargar_dnit(destino: Path | None = None) -> int:
    """Baja ruc0.zip … ruc9.zip (enlaces leídos de la página, porque cambian) y arma el índice."""
    pagina = get(URL_DNIT_LISTADO, cache_horas=0)
    enlaces = sorted(set(re.findall(r'href="(/documents/[^"]*ruc\d\.zip[^"]*)"', pagina.cuerpo)))
    if not enlaces:
        raise RuntimeError("No se encontraron los archivos ruc*.zip en la página de la DNIT")
    destino = destino or ruta_dnit()
    if destino.exists():
        destino.unlink()
    con = sqlite3.connect(destino)
    con.execute("CREATE TABLE ruc (ruc TEXT, dv TEXT, razon TEXT, razon_norm TEXT, anterior TEXT, estado TEXT)")
    total = 0
    import httpx

    for enlace in enlaces:
        r = httpx.get("https://www.dnit.gov.py" + enlace, timeout=120, follow_redirects=True,
                      headers={"User-Agent": config.USER_AGENT})
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for nombre in z.namelist():
                filas = []
                for linea in z.open(nombre).read().decode("utf-8", "replace").splitlines():
                    partes = linea.split("|")
                    if len(partes) >= 5:
                        filas.append((partes[0], partes[2], partes[1], normalizar(partes[1], quitar_forma=False),
                                      partes[3], partes[4]))
                con.executemany("INSERT INTO ruc VALUES (?,?,?,?,?,?)", filas)
                total += len(filas)
    con.execute("CREATE INDEX ix_ruc ON ruc(ruc)")
    con.commit()
    con.close()
    return total


def dnit_buscar(nombre: str | None = None, ruc: str | None = None, limite: int = 20) -> dict[str, Any]:
    ruta = ruta_dnit()
    if not ruta.exists():
        raise FileNotFoundError("Listado DNIT no descargado: correr `uv run dd descargar-fuentes --dnit`")
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    if ruc:
        base, _ = separar(ruc)
        filas = con.execute("SELECT * FROM ruc WHERE ruc = ?", (base,)).fetchall()
    elif nombre:
        patron = "%" + normalizar(nombre, quitar_forma=True) + "%"
        filas = con.execute("SELECT * FROM ruc WHERE razon_norm LIKE ? LIMIT ?", (patron, limite)).fetchall()
    else:
        raise ValueError("Indicar nombre o ruc")
    con.close()
    return {
        "resultados": [
            {"ruc": f"{f['ruc']}-{f['dv']}", "razon_social": f["razon"], "estado": f["estado"],
             "ruc_anterior": f["anterior"]}
            for f in filas
        ]
    }


def validar(ruc: str) -> dict[str, Any]:
    base, dv = separar(ruc)
    esperado = calcular_dv(base)
    return {
        "ruc": normalizar_ruc(ruc),
        "dv_informado": dv,
        "dv_calculado": esperado,
        "valido": dv == esperado,
        "ruc_completo": f"{base}-{esperado}",
    }


def opencorporates_buscar(nombre: str, jurisdiccion: str | None = None) -> dict[str, Any]:
    token = config.env("OPENCORPORATES_API_TOKEN")
    if not token:
        raise PermissionError(
            "OpenCorporates exige token (gratis solo para proyectos con licencia abierta share-alike)."
        )
    r = get(f"{URL_OPENCORPORATES}/companies/search",
            params={"q": nombre, "jurisdiction_code": jurisdiccion, "api_token": token, "per_page": 10})
    if r.estado != 200:
        raise RuntimeError(f"OpenCorporates HTTP {r.estado}")
    empresas = (r.json().get("results") or {}).get("companies") or []
    return {
        "url": r.url.replace(token, "***"),
        "empresas": [
            {
                "nombre": c["company"].get("name"),
                "numero": c["company"].get("company_number"),
                "jurisdiccion": c["company"].get("jurisdiction_code"),
                "estado": c["company"].get("current_status"),
                "constitucion": c["company"].get("incorporation_date"),
                "agente_registrado": c["company"].get("agent_name"),
                "url": c["company"].get("opencorporates_url"),
            }
            for c in empresas
        ],
    }


def sam_exclusiones(nombre: str) -> dict[str, Any]:
    clave = config.env("SAM_API_KEY")
    if not clave:
        raise PermissionError("SAM.gov exige api_key personal (10 consultas por día sin rol federal).")
    r = get(URL_SAM_EXCLUSIONES, params={"api_key": clave, "exclusionName": nombre}, cache_horas=72)
    if r.estado != 200:
        raise RuntimeError(f"SAM.gov HTTP {r.estado}")
    datos = r.json()
    return {
        "url": r.url.replace(clave, "***"),
        "total": datos.get("totalRecords"),
        "exclusiones": [
            {
                "nombre": (e.get("exclusionIdentification") or {}).get("name"),
                "uei": (e.get("exclusionIdentification") or {}).get("ueiSAM"),
                "tipo": (e.get("exclusionDetails") or {}).get("exclusionType"),
                "agencia": (e.get("exclusionDetails") or {}).get("excludingAgencyName"),
                "activa": (e.get("exclusionActions") or {}).get("listOfActions"),
            }
            for e in (datos.get("excludedEntity") or [])[:10]
        ],
    }
