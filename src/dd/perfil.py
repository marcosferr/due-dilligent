"""Perfil comparativo de proveedores a partir de los datos masivos de la DNCP.

Cada indicador es contexto para comparar, no una conclusión: un porcentaje alto de contratación
directa o de oferente único se explica muchas veces por el rubro (proveedor exclusivo, urgencia).
Los indicadores no entran al semáforo salvo que el criterio del caso lo diga.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from statistics import median
from typing import Any

from . import masivo
from .ruc import normalizar_ruc

NO_COMPETITIVAS = ("directa", "excepci", "vía de la excepción", "via de la excepcion")


def _anio(fecha: str | None) -> int | None:
    return int(fecha[:4]) if fecha and fecha[:4].isdigit() else None


def _pct(a: float, b: float) -> float | None:
    return round(100 * a / b, 1) if b else None


def _dias(desde: str | None, hasta: str | None) -> int | None:
    from datetime import date

    try:
        return (date.fromisoformat(hasta[:10]) - date.fromisoformat(desde[:10])).days
    except (TypeError, ValueError):
        return None


def adjudicaciones(con: sqlite3.Connection, ruc: str, desde: int | None = None, hasta: int | None = None):
    filas = [dict(r) for r in con.execute(
        """SELECT j.award_id, j.release_id, j.fecha, j.monto, j.moneda, j.estado,
                  p.ocid, p.titulo, p.convocante_id, p.convocante, p.modalidad, p.categoria, p.estimado,
                  p.moneda_estimado, p.oferentes,
                  (SELECT COUNT(*) FROM adjudicacion k WHERE k.release_id = j.release_id) AS adjudicaciones_en_proceso
           FROM adjudicado a JOIN adjudicacion j ON j.award_id = a.award_id
           LEFT JOIN proceso p ON p.release_id = j.release_id
           WHERE a.ruc = ?""", (normalizar_ruc(ruc),))]
    return [f for f in filas if (desde is None or (_anio(f["fecha"]) or 0) >= desde)
            and (hasta is None or (_anio(f["fecha"]) or 9999) <= hasta)]


def perfil(con: sqlite3.Connection, ruc: str, desde: int | None = None, hasta: int | None = None,
           proveedor_api: dict[str, Any] | None = None) -> dict[str, Any]:
    ruc = normalizar_ruc(ruc)
    adj = adjudicaciones(con, ruc, desde, hasta)
    pyg = [a for a in adj if (a["moneda"] or "PYG") == "PYG" and a["monto"] is not None]
    total = sum(a["monto"] for a in pyg)
    nombre = con.execute("SELECT nombre FROM adjudicado WHERE ruc = ? LIMIT 1", (ruc,)).fetchone()

    por_anio: dict[int, dict[str, float]] = defaultdict(lambda: {"adjudicaciones": 0, "monto_pyg": 0.0})
    for a in adj:
        y = _anio(a["fecha"])
        if y:
            por_anio[y]["adjudicaciones"] += 1
            if a in pyg:
                por_anio[y]["monto_pyg"] += a["monto"]

    por_conv: dict[str, float] = defaultdict(float)
    for a in pyg:
        por_conv[a["convocante"] or "(sin dato)"] += a["monto"]
    top = max(por_conv.items(), key=lambda x: x[1]) if por_conv else (None, 0)

    por_mod: dict[str, dict[str, float]] = defaultdict(lambda: {"adjudicaciones": 0, "monto_pyg": 0.0})
    for a in adj:
        m = a["modalidad"] or "(sin dato)"
        por_mod[m]["adjudicaciones"] += 1
        if a in pyg:
            por_mod[m]["monto_pyg"] += a["monto"]
    no_comp = sum(v["monto_pyg"] for k, v in por_mod.items() if any(t in k.lower() for t in NO_COMPETITIVAS))

    procesos = {a["release_id"]: a for a in adj}
    competitivos = [a for a in procesos.values() if a["oferentes"] is not None
                    and not any(t in (a["modalidad"] or "").lower() for t in NO_COMPETITIVAS)]
    unicos = [a for a in competitivos if a["oferentes"] == 1]

    ratios = [a["monto"] / a["estimado"] for a in pyg if a["adjudicaciones_en_proceso"] == 1 and a["estimado"]
              and (a["moneda_estimado"] or "PYG") == "PYG"]

    award_ids = [a["award_id"] for a in adj]
    contratos = []
    for i in range(0, len(award_ids), 500):
        lote = award_ids[i:i + 500]
        contratos += [dict(r) for r in con.execute(
            f"SELECT * FROM contrato WHERE award_id IN ({','.join('?' * len(lote))})", lote)]
    contratado = sum(c["monto"] or 0 for c in contratos if (c["moneda"] or "PYG") == "PYG")
    ids_contrato = {c["contrato_id"] for c in contratos}
    pagos = [dict(r) for r in con.execute("SELECT * FROM pago WHERE ruc = ?", (ruc,))]
    pagos = [p for p in pagos if (desde is None or (_anio(p["fecha"]) or 0) >= desde)
             and (hasta is None or (_anio(p["fecha"]) or 9999) <= hasta)]
    pagado = sum(p["monto"] or 0 for p in pagos if (p["moneda"] or "PYG") == "PYG")
    pagado_de_contratos = sum(p["monto"] or 0 for p in pagos if p["contrato_id"] in ids_contrato
                              and (p["moneda"] or "PYG") == "PYG")
    demoras = [d for d in (_dias(p["solicitud"], p["fecha"]) for p in pagos) if d is not None and d >= 0]

    anios = sorted(por_anio)
    salida = {
        "ruc": ruc,
        "nombre": nombre["nombre"] if nombre else None,
        "periodo": {"desde": desde, "hasta": hasta},
        "escala": {
            "adjudicaciones": len(adj),
            "procesos": len(procesos),
            "monto_adjudicado_pyg": round(total),
            "monto_medio_por_adjudicacion_pyg": round(total / len(pyg)) if pyg else None,
            "por_anio": {y: {"adjudicaciones": v["adjudicaciones"], "monto_pyg": round(v["monto_pyg"])}
                         for y, v in sorted(por_anio.items())},
            "primer_anio": anios[0] if anios else None,
            "ultimo_anio": anios[-1] if anios else None,
            "anios_con_adjudicaciones": len(anios),
        },
        "dependencia": {
            "convocantes_distintos": len(por_conv),
            "principal_convocante": top[0],
            "pct_monto_principal_convocante": _pct(top[1], total),
        },
        "modalidad": {
            "pct_monto_no_competitivo": _pct(no_comp, total),
            "detalle": {k: {"adjudicaciones": v["adjudicaciones"], "monto_pyg": round(v["monto_pyg"])}
                        for k, v in sorted(por_mod.items(), key=lambda x: -x[1]["monto_pyg"])},
        },
        "competencia": {
            "procesos_competitivos_con_dato": len(competitivos),
            "pct_oferente_unico": _pct(len(unicos), len(competitivos)),
            "oferente_unico_ocids": [a["ocid"] for a in unicos][:20],
        },
        "precio": {
            "procesos_comparables": len(ratios),
            "mediana_adjudicado_sobre_estimado": round(median(ratios), 3) if ratios else None,
            "pct_por_encima_del_estimado": _pct(sum(r > 1.0001 for r in ratios), len(ratios)),
        },
        "ejecucion": {
            "contratos": len(contratos),
            "monto_contratado_pyg": round(contratado),
            "pagos": len(pagos),
            "monto_pagado_pyg": round(pagado),
            "pct_pagado_de_lo_contratado": _pct(pagado_de_contratos, contratado),
            "mediana_dias_solicitud_a_pago": float(median(demoras)) if demoras else None,
        },
    }
    if proveedor_api:
        salida["perfil_dncp"] = {
            "razon_social": proveedor_api.get("razon_social"),
            "tamano_declarado": proveedor_api.get("tamano"),
            "tipo_persona": proveedor_api.get("tipo_persona"),
            "categorias": proveedor_api.get("categorias"),
            "sanciones": len(proveedor_api.get("sanciones") or []),
            "inhabilitaciones": sum(s["tipo"] == "INHABILITACION" for s in proveedor_api.get("sanciones") or []),
            "inhabilitacion_vigente": any(s["tipo"] == "INHABILITACION" and s.get("vigente")
                                          for s in proveedor_api.get("sanciones") or []),
        }
    return salida


def precios_vs_mercado(con: sqlite3.Connection, ruc: str, minimo_comparables: int = 5) -> list[dict[str, Any]]:
    """Precio unitario del proveedor frente a la mediana del mismo ítem de catálogo y unidad.

    La mediana usa todos los ítems cargados: si se cargaron filtrados por RUC, la comparación es solo
    entre esos proveedores (se informa `comparables`).
    """
    propios = [dict(r) for r in con.execute(
        """SELECT i.* FROM item i JOIN adjudicado a ON a.award_id = i.award_id
           WHERE a.ruc = ? AND i.precio_unitario > 0 AND i.catalogo != ''""", (normalizar_ruc(ruc),))]
    salida = []
    for it in propios:
        otros = [r[0] for r in con.execute(
            "SELECT precio_unitario FROM item WHERE catalogo = ? AND unidad = ? AND precio_unitario > 0 AND moneda = ?",
            (it["catalogo"], it["unidad"], it["moneda"]))]
        if len(otros) < minimo_comparables:
            continue
        m = median(otros)
        salida.append({"award_id": it["award_id"], "catalogo": it["catalogo"], "descripcion": it["catalogo_desc"],
                       "unidad": it["unidad"], "precio_unitario": it["precio_unitario"], "mediana_mercado": m,
                       "relacion": round(it["precio_unitario"] / m, 2), "comparables": len(otros)})
    return sorted(salida, key=lambda x: -x["relacion"])


FILAS_TABLA = [
    ("Nombre", lambda p: p["nombre"]),
    ("Tamaño declarado (DNCP)", lambda p: (p.get("perfil_dncp") or {}).get("tamano_declarado")),
    ("Adjudicaciones", lambda p: p["escala"]["adjudicaciones"]),
    ("Monto adjudicado (M PYG)", lambda p: round(p["escala"]["monto_adjudicado_pyg"] / 1e6, 1)),
    ("Monto medio por adjudicación (M PYG)", lambda p: round((p["escala"]["monto_medio_por_adjudicacion_pyg"] or 0) / 1e6, 1)),
    ("Años con adjudicaciones", lambda p: p["escala"]["anios_con_adjudicaciones"]),
    ("Primer / último año", lambda p: f"{p['escala']['primer_anio']} / {p['escala']['ultimo_anio']}"),
    ("Convocantes distintos", lambda p: p["dependencia"]["convocantes_distintos"]),
    ("% del monto con el principal convocante", lambda p: p["dependencia"]["pct_monto_principal_convocante"]),
    ("Principal convocante", lambda p: p["dependencia"]["principal_convocante"]),
    ("% del monto en modalidades no competitivas", lambda p: p["modalidad"]["pct_monto_no_competitivo"]),
    ("% de procesos competitivos con oferente único", lambda p: p["competencia"]["pct_oferente_unico"]),
    ("Mediana adjudicado / estimado", lambda p: p["precio"]["mediana_adjudicado_sobre_estimado"]),
    ("% adjudicado por encima del estimado", lambda p: p["precio"]["pct_por_encima_del_estimado"]),
    ("Monto contratado (M PYG)", lambda p: round(p["ejecucion"]["monto_contratado_pyg"] / 1e6, 1)),
    ("Monto pagado (M PYG)", lambda p: round(p["ejecucion"]["monto_pagado_pyg"] / 1e6, 1)),
    ("% pagado de lo contratado", lambda p: p["ejecucion"]["pct_pagado_de_lo_contratado"]),
    ("Mediana de días solicitud → pago", lambda p: p["ejecucion"]["mediana_dias_solicitud_a_pago"]),
    ("Sanciones DNCP (inhabilitaciones)", lambda p: (f"{p['perfil_dncp']['sanciones']} ({p['perfil_dncp']['inhabilitaciones']})"
                                                     if p.get("perfil_dncp") else None)),
    ("Inhabilitación vigente", lambda p: (p.get("perfil_dncp") or {}).get("inhabilitacion_vigente")),
]


def comparar(rucs: list[str], desde: int | None = None, hasta: int | None = None,
             con_api: bool = True) -> dict[str, Any]:
    con = masivo.conectar()
    try:
        cargados = sorted({r[0] for r in con.execute("SELECT DISTINCT anio FROM carga")})
        api = {}
        if con_api:
            from .dncp import ClienteDNCP
            from .http import ErrorFuente

            cliente = ClienteDNCP()
            for r in rucs:
                try:
                    api[r] = cliente.obtener_proveedor(r)[1]
                except ErrorFuente:
                    api[r] = None
        perfiles = [perfil(con, r, desde, hasta, api.get(r)) for r in rucs]
    finally:
        con.close()
    return {"anios_cargados": cargados, "periodo": {"desde": desde, "hasta": hasta}, "perfiles": perfiles,
            "tabla": [[nombre] + [_fmt(f(p)) for p in perfiles] for nombre, f in FILAS_TABLA],
            "rucs": [p["ruc"] for p in perfiles]}


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "sí" if v else "no"
    if isinstance(v, float):
        return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(v, int):
        return f"{v:,}".replace(",", ".")
    return str(v)


def a_markdown(comp: dict[str, Any]) -> str:
    rucs = comp["rucs"]
    lineas = [
        "# Comparación de proveedores",
        "",
        f"Fuente: datos masivos OCDS de la DNCP, años cargados {comp['anios_cargados']}; "
        f"período analizado {comp['periodo']['desde'] or 'todo'}–{comp['periodo']['hasta'] or 'todo'}. "
        "Montos en PYG (se excluyen otras monedas). Tamaño y sanciones: API de proveedores de la DNCP.",
        "",
        "> Los indicadores son contexto para comparar, no conclusiones: contratación directa u oferente único "
        "pueden explicarse por el rubro. Cada proveedor puede verificarse en "
        "https://www.contrataciones.gov.py/datos/api/v3/doc/search/processes?awards.suppliers.id=<RUC>.",
        "",
        "| Indicador | " + " | ".join(f"RUC {r}" for r in rucs) + " |",
        "|---|" + "---|" * len(rucs),
    ]
    lineas += ["| " + " | ".join(str(c).replace("|", "/") for c in fila) + " |" for fila in comp["tabla"]]
    lineas += ["", "## Monto adjudicado por año (M PYG)", ""]
    anios = sorted({y for p in comp["perfiles"] for y in p["escala"]["por_anio"]})
    lineas.append("| Año | " + " | ".join(f"RUC {r}" for r in rucs) + " |")
    lineas.append("|---|" + "---|" * len(rucs))
    for y in anios:
        lineas.append(f"| {y} | " + " | ".join(
            _fmt(round(p["escala"]["por_anio"].get(y, {}).get("monto_pyg", 0) / 1e6, 1)) for p in comp["perfiles"]) + " |")
    lineas += ["", "## Advertencias", "",
               "- Cobertura: solo los años cargados; un proveedor más antiguo aparece incompleto.",
               "- Monto pagado incluye pagos de contratos firmados antes del período o de años no cargados.",
               "- % pagado de lo contratado: contratos en curso dan valores bajos; adendas o reajustes pueden superar 100 %.",
               "- Mediana adjudicado/estimado = 1,0 suele indicar contratos abiertos con monto máximo.",
               "- Tamaño declarado: autodeclarado en la DNCP."]
    return "\n".join(lineas) + "\n"
