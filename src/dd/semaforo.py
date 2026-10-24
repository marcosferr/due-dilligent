"""Semáforo sugerido y explicable, con el criterio congelado en el caso.

1. Reglas duras: un hecho (con identificador, confiabilidad A o B) que active una regla
   decide solo el color.
2. Puntaje: P = Σ severidad(categoría) × confianza(fuente) sobre hechos y posibles alertas
   con categoría de riesgo.
3. Umbrales del criterio.

El agente solo aplica las reglas; la conclusión la firma una persona.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from . import db

ORDEN = {"verde": 0, "amarillo": 1, "rojo": 2}


def color_por_puntaje(p: float, umbrales: dict[str, float]) -> str:
    if p <= umbrales.get("verde_si_puntaje_igual_a", 0):
        return "verde"
    if p >= umbrales.get("rojo_desde", 5):
        return "rojo"
    return "amarillo"


def calcular(con: sqlite3.Connection, caso_id: int) -> dict[str, Any]:
    caso = db.obtener_caso(con, caso_id)
    criterio = json.loads(caso["criterio_json"])
    confianza = criterio["confianza"]
    severidades = criterio["severidades"]
    umbrales = criterio["umbrales"]
    reglas = {r["id"]: r for r in criterio.get("reglas_duras", [])}
    hallazgos = db.listar_hallazgos(con, caso_id)
    vigentes = [h for h in hallazgos if h["estado"] in ("encontrado", "parcial")]

    duras = []
    for h in vigentes:
        if h["regla_dura"] and h["tipo"] == "hecho" and h["confiabilidad"] in ("A", "B"):
            regla = reglas.get(h["regla_dura"], {})
            duras.append({
                "regla": h["regla_dura"],
                "descripcion": regla.get("descripcion"),
                "color": regla.get("color", "rojo"),
                "hallazgo_id": h["id"],
                "entidad_id": h["entidad_id"],
                "dato": h["dato"],
                "url": h["url"],
            })

    contribuciones = []
    for h in vigentes:
        if not h["categoria_alerta"] or h["regla_dura"]:
            continue
        sev = float(severidades.get(h["categoria_alerta"], severidades.get("otra", 1)))
        conf = float(confianza.get(h["confiabilidad"], 0))
        contribuciones.append({
            "hallazgo_id": h["id"],
            "entidad_id": h["entidad_id"],
            "tipo": h["tipo"],
            "categoria": h["categoria_alerta"],
            "severidad": sev,
            "confiabilidad": h["confiabilidad"],
            "confianza": conf,
            "aporte": round(sev * conf, 2),
            "dato": h["dato"],
            "url": h["url"],
        })
    puntaje = round(sum(c["aporte"] for c in contribuciones), 2)
    color_puntaje = color_por_puntaje(puntaje, umbrales)
    color = max([color_puntaje, *[d["color"] for d in duras]], key=lambda c: ORDEN.get(c, 0))

    tareas = [
        {"hallazgo_id": h["id"], "dato": h["dato"], "motivo": "Fuente D: no mueve el color, verificar con otra fuente"}
        for h in vigentes if h["confiabilidad"] == "D"
    ] + [
        {"hallazgo_id": h["id"], "dato": h["dato"], "motivo": "Posible alerta sin identificador: confirmar o descartar"}
        for h in vigentes if h["tipo"] == "posible_alerta" and h["confiabilidad"] != "D"
    ]

    brechas = [
        {"consulta_id": c["id"], "fuente": c["fuente"], "consulta": c["consulta"], "detalle": c["detalle"]}
        for c in db.listar_consultas(con, caso_id) if c["estado"] == "no_accesible"
    ] + [
        {"hallazgo_id": h["id"], "fuente": h["fuente"], "consulta": h["dato"], "detalle": h["extracto"]}
        for h in hallazgos if h["estado"] == "no_accesible"
    ]

    return {
        "color_sugerido": color,
        "puntaje": puntaje,
        "color_por_puntaje": color_puntaje,
        "reglas_duras": duras,
        "contribuciones": sorted(contribuciones, key=lambda c: -c["aporte"]),
        "tareas_verificacion": tareas,
        "brechas": brechas,
        "que_cambiaria": que_cambiaria(color, puntaje, duras, contribuciones, brechas, criterio),
        "criterio": {"version": caso["criterio_version"], "sha256": caso["criterio_sha256"],
                     "estado": criterio.get("estado")},
    }


def que_cambiaria(
    color: str,
    puntaje: float,
    duras: list[dict[str, Any]],
    contribuciones: list[dict[str, Any]],
    brechas: list[dict[str, Any]],
    criterio: dict[str, Any],
) -> list[str]:
    """Lo que cambiaría el resultado si apareciera (o si se descartara)."""
    rojo = criterio["umbrales"].get("rojo_desde", 5)
    conf = criterio["confianza"]
    salida: list[str] = []
    if duras:
        salida.append("El rojo viene de una regla dura: solo cambia si el hecho que la activa se desmiente en la fuente.")
    else:
        nombres = ", ".join(r["id"] for r in criterio.get("reglas_duras", []))
        salida.append(f"Cualquier hecho confirmado de una regla dura ({nombres}) llevaría a rojo.")
        if puntaje < rojo:
            salida.append(f"Faltan {round(rojo - puntaje, 2)} puntos para rojo (umbral {rojo}).")
    for c in contribuciones:
        if c["confiabilidad"] in ("B", "C"):
            nuevo = round(c["severidad"] * conf["A"], 2)
            salida.append(
                f"Si H-{c['hallazgo_id']} ({c['categoria']}) se confirmara con una fuente A, su aporte pasaría "
                f"de {c['aporte']} a {nuevo}; si se descartara, el puntaje bajaría a {round(puntaje - c['aporte'], 2)}."
            )
    for b in brechas[:10]:
        salida.append(f"Brecha: {b['fuente']} no fue accesible ({b['consulta']}); un resultado ahí podría cambiar el color.")
    if color == "verde":
        salida.append("Verde no certifica ausencia de riesgo: solo que en las fuentes consultadas no apareció nada.")
    return salida
