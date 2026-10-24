"""Cliente HTTP de solo lectura con caché en SQLite, reintentos y evidencia de cada llamada."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from . import config, db
from .ratelimit import LimiteVelocidad


@dataclass
class Respuesta:
    url: str
    estado: int
    cuerpo: str
    fecha_utc: str
    desde_cache: bool = False
    datos: Any = field(default=None)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.cuerpo.encode("utf-8")).hexdigest()

    def json(self) -> Any:
        if self.datos is None:
            self.datos = json.loads(self.cuerpo) if self.cuerpo else None
        return self.datos


class ErrorFuente(RuntimeError):
    """La fuente no respondió: se registra como "no accesible", nunca como "no encontrado"."""


def _clave(url: str, params: dict[str, Any] | None) -> str:
    return url + "?" + json.dumps(params or {}, sort_keys=True, ensure_ascii=False)


def get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    limite: LimiteVelocidad | None = None,
    cache_horas: float = 24,
    reintentos: int = 3,
    timeout: float = 30,
) -> Respuesta:
    """GET con caché (las respuestas 200 y 404 se cachean: "no encontrado" también es dato)."""
    params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    clave = _clave(url, params)
    with db.conectar() as con:
        fila = con.execute("SELECT * FROM cache_http WHERE clave = ?", (clave,)).fetchone()
    if fila and cache_horas > 0:
        fecha = datetime.fromisoformat(fila["fecha_utc"])
        if datetime.now(timezone.utc) - fecha < timedelta(hours=cache_horas):
            url_final = str(httpx.URL(url, params=params))
            return Respuesta(url_final, fila["estado"], fila["cuerpo"], fila["fecha_utc"], desde_cache=True)

    cabeceras = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}
    cabeceras.update(headers or {})
    ultimo_error: Exception | None = None
    for intento in range(reintentos):
        if limite:
            limite.adquirir()
        try:
            r = httpx.get(url, params=params, headers=cabeceras, timeout=timeout, follow_redirects=True)
        except httpx.HTTPError as e:
            ultimo_error = e
            time.sleep(2**intento)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            ultimo_error = ErrorFuente(f"HTTP {r.status_code}")
            time.sleep(2**intento * (5 if r.status_code == 429 else 1))
            continue
        resp = Respuesta(str(r.url), r.status_code, r.text, db.ahora_utc())
        if r.status_code in (200, 404):
            with db.conectar() as con:
                con.execute(
                    "INSERT OR REPLACE INTO cache_http (clave, fecha_utc, estado, cuerpo) VALUES (?,?,?,?)",
                    (clave, resp.fecha_utc, resp.estado, resp.cuerpo),
                )
        return resp
    raise ErrorFuente(f"{url}: {ultimo_error}")


def post_json(url: str, cuerpo: dict[str, Any], timeout: float = 30) -> Respuesta:
    r = httpx.post(
        url,
        json=cuerpo,
        headers={"User-Agent": config.USER_AGENT, "Accept": "application/json"},
        timeout=timeout,
    )
    return Respuesta(str(r.url), r.status_code, r.text, db.ahora_utc())
