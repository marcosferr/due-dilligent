"""Límite de llamadas por minuto compartido entre procesos (ventana deslizante en archivo).

Los subagentes corren en paralelo y pueden lanzar varios servidores MCP; la DNCP sin token
admite 15 llamadas por minuto en total, así que el contador vive en disco con un lock.
"""

from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path
from typing import Callable

from . import config


class LimiteVelocidad:
    def __init__(
        self,
        nombre: str,
        llamadas_por_minuto: int,
        ventana: float = 60.0,
        reloj: Callable[[], float] = time.time,
        dormir: Callable[[float], None] = time.sleep,
        ruta: Path | None = None,
    ) -> None:
        self.maximo = max(1, llamadas_por_minuto)
        self.ventana = ventana
        self.reloj = reloj
        self.dormir = dormir
        self.ruta = ruta or (config.home() / f"ratelimit-{nombre}.json")

    def _leer(self, f) -> list[float]:
        f.seek(0)
        contenido = f.read()
        try:
            return [float(t) for t in json.loads(contenido)] if contenido else []
        except (ValueError, TypeError):
            return []

    def _escribir(self, f, marcas: list[float]) -> None:
        f.seek(0)
        f.truncate()
        f.write(json.dumps(marcas))
        f.flush()

    def adquirir(self, espera_maxima: float = 120.0) -> float:
        """Bloquea hasta que haya cupo. Devuelve los segundos esperados."""
        esperado = 0.0
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.touch(exist_ok=True)
        while True:
            with open(self.ruta, "r+", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    ahora = self.reloj()
                    marcas = [t for t in self._leer(f) if ahora - t < self.ventana]
                    if len(marcas) < self.maximo:
                        marcas.append(ahora)
                        self._escribir(f, marcas)
                        return esperado
                    pausa = self.ventana - (ahora - min(marcas)) + 0.05
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
            if esperado + pausa > espera_maxima:
                raise TimeoutError(
                    f"Sin cupo de llamadas tras {esperado:.0f}s (límite {self.maximo}/min)"
                )
            self.dormir(pausa)
            esperado += pausa
