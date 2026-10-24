"""Evaluación de un caso contra la respuesta de referencia (la ronda manual del equipo).

Métricas del documento de diseño: cobertura, entidad correcta, evidencia completa,
"no encontrado" auditable, falsos positivos por homónimo, semáforo y tiempo.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from . import db, semaforo
from .ruc import normalizar_ruc
from .variantes import quitar_acentos


def _norm(t: str) -> str:
    return quitar_acentos(t or "").lower()


def _entidad_coincide(entidad: dict[str, Any], esperada: dict[str, str] | None) -> bool:
    if not esperada:
        return True
    ids = {k.upper(): normalizar_ruc(v) if k.upper() == "RUC" else v for k, v in entidad["identificadores"].items()}
    for k, v in esperada.items():
        k = k.upper()
        if k == "NOMBRE":
            if _norm(v) not in _norm(entidad["razon_social"]):
                return False
        elif ids.get(k) != (normalizar_ruc(v) if k == "RUC" else v):
            return False
    return True


def evaluar(caso_id: int, ruta_referencia: Path) -> dict[str, Any]:
    ref = json.loads(ruta_referencia.read_text(encoding="utf-8"))
    with db.conectar() as con:
        caso = db.obtener_caso(con, caso_id)
        entidades = {e["id"]: e for e in db.listar_entidades(con, caso_id)}
        hallazgos = db.listar_hallazgos(con, caso_id)
        consultas = db.listar_consultas(con, caso_id)
        sem = semaforo.calcular(con, caso_id)

    encontrados = [h for h in hallazgos if h["estado"] in ("encontrado", "parcial")]

    cobertura = []
    for hecho in ref.get("hechos", []):
        claves = [_norm(c) for c in hecho.get("palabras_clave", [])]
        match = [
            h["id"] for h in encontrados
            if claves and all(c in _norm(f"{h['dato']} {h['extracto'] or ''}") for c in claves)
            and _entidad_coincide(entidades[h["entidad_id"]], hecho.get("entidad"))
        ]
        cobertura.append({"id": hecho.get("id"), "descripcion": hecho.get("descripcion"), "encontrado": bool(match),
                          "hallazgos": match})

    sin_id = [h["id"] for h in encontrados if not entidades[h["entidad_id"]]["identificadores"]]
    completos = [h for h in encontrados if h["url"] and h["fecha_utc"] and h["captura_id"]]
    vacias = [c for c in consultas if c["estado"] == "no_encontrado"]
    auditables = [c for c in vacias if c["consulta"].strip() and c["fuente"].strip()]
    homonimos_como_hecho = [
        h["id"] for h in hallazgos
        if h["categoria_alerta"] == "coincidencia_sancion_solo_nombre" and h["tipo"] == "hecho"
    ]
    minutos = None
    if caso["ficha_generada_utc"]:
        minutos = round((datetime.fromisoformat(caso["ficha_generada_utc"])
                         - datetime.fromisoformat(caso["creado_utc"])).total_seconds() / 60, 1)

    def pct(a: int, b: int) -> float | None:
        return round(100 * a / b, 1) if b else None

    color_ref = ref.get("color_esperado")
    return {
        "caso_id": caso_id,
        "referencia": ref.get("caso"),
        "cobertura": {"pct": pct(sum(c["encontrado"] for c in cobertura), len(cobertura)), "detalle": cobertura},
        "entidad_correcta": {"hallazgos_sin_identificador": sin_id, "ok": not sin_id},
        "evidencia_completa": {"pct": pct(len(completos), len(encontrados)),
                               "sin_captura": [h["id"] for h in encontrados if not h["captura_id"]]},
        "no_encontrado_auditable": {"pct": pct(len(auditables), len(vacias)), "consultas_sin_resultado": len(vacias)},
        "falsos_positivos_homonimo": {"guardados_como_hecho": homonimos_como_hecho, "ok": not homonimos_como_hecho},
        "semaforo": {"agente": sem["color_sugerido"], "referencia": color_ref,
                     "coincide": (sem["color_sugerido"] == color_ref) if color_ref else None,
                     "puntaje": sem["puntaje"]},
        "tiempo": {"agente_minutos": minutos, "manual_horas": ref.get("tiempo_manual_horas")},
    }
