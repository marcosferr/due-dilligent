"""Rutas y variables de entorno compartidas por todos los módulos."""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _cargar_env() -> None:
    """Carga `.env` de la raíz sin pisar variables ya exportadas."""
    archivo = RAIZ / ".env"
    if not archivo.exists():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()


def env(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, defecto).strip()


def modo() -> str:
    """`real` consulta las fuentes; `mock` usa datos ficticios de `data/mocks/`."""
    return "mock" if env("DD_MODO", "real").lower() == "mock" else "real"


def home() -> Path:
    ruta = Path(env("DD_HOME", str(RAIZ / "var")))
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_db() -> Path:
    return home() / "dd.sqlite"


def dir_casos() -> Path:
    ruta = home() / "casos"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def dir_fuentes() -> Path:
    """Descargas en bloque (OpenSanctions, OFAC, DNIT)."""
    ruta = home() / "fuentes"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


DIR_MOCKS = RAIZ / "data" / "mocks"
DIR_MUESTRAS = RAIZ / "data" / "samples"
CRITERIO_SEMAFORO = RAIZ / "config" / "criterio_semaforo.json"
USER_AGENT = "due-dilligent/0.1 (hackaton UNI; solo lectura)"
