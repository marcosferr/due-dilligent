"""Captura de evidencia: HTML (y captura de pantalla si hay navegador), hora UTC y SHA-256."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

from . import config, db


def _carpeta(caso_id: int) -> Path:
    ruta = config.dir_casos() / f"caso-{caso_id}" / "capturas"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _nombre(url: str, n: int) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", re.sub(r"^https?://", "", url)).strip("-")[:80]
    return f"{n:04d}-{base}"


def _con_navegador(url: str, html: Path, png: Path) -> dict[str, Any] | None:
    """Intenta Playwright de Python y, si no está, el de Node (scripts/captura.cjs)."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page(user_agent=config.USER_AGENT)
            resp = pagina.goto(url, wait_until="networkidle", timeout=45000)
            pagina.wait_for_timeout(1500)
            html.write_text(pagina.content(), encoding="utf-8")
            pagina.screenshot(path=str(png), full_page=True)
            estado = resp.status if resp else None
            navegador.close()
            return {"estado": estado, "metodo": "navegador-python"}
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001 - se informa y se intenta la siguiente vía
        return {"error": f"playwright-python: {e}"}
    if shutil.which("node"):
        script = config.RAIZ / "scripts" / "captura.cjs"
        r = subprocess.run(["node", str(script), url, str(html), str(png)], capture_output=True, text=True,
                           timeout=90, cwd=config.RAIZ)
        if r.returncode == 0:
            datos = json.loads(r.stdout.strip().splitlines()[-1])
            return {"estado": datos.get("estado"), "metodo": "navegador-node"}
        return {"error": f"playwright-node: {r.stderr.strip()[:300]}"}
    return None


def capturar(caso_id: int, url: str, usar_navegador: bool = False) -> dict[str, Any]:
    """Guarda la página como evidencia y la registra en la tabla `captura`.

    Con `usar_navegador` se renderiza JavaScript y se guarda también una imagen PNG.
    El hash se calcula sobre el HTML guardado (y la imagen, si existe).
    """
    with db.conectar() as con:
        db.obtener_caso(con, caso_id)
        n = con.execute("SELECT COUNT(*) FROM captura WHERE caso_id = ?", (caso_id,)).fetchone()[0] + 1
    carpeta = _carpeta(caso_id)
    html, png = carpeta / f"{_nombre(url, n)}.html", carpeta / f"{_nombre(url, n)}.png"
    metodo, estado, error = "http", None, None

    if url.startswith(("mock://", "demo://")):
        html.write_text(f"<html><body>Respuesta MOCK (datos ficticios) para {url}</body></html>", encoding="utf-8")
        metodo = "mock"
    elif usar_navegador:
        r = _con_navegador(url, html, png)
        if r and "error" not in r:
            metodo, estado = r["metodo"], r["estado"]
        else:
            error = (r or {}).get("error", "sin navegador disponible")
    if not html.exists():
        try:
            resp = httpx.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=30, follow_redirects=True)
            html.write_bytes(resp.content)
            estado = resp.status_code
        except httpx.HTTPError as e:
            return {"ok": False, "url": url, "error": f"No se pudo capturar: {e}", "estado": "no_accesible"}

    h = hashlib.sha256(html.read_bytes())
    if png.exists():
        h.update(png.read_bytes())
    sha = h.hexdigest()
    with db.conectar() as con:
        captura_id = db.registrar_captura(
            con, caso_id, url, sha, metodo,
            ruta_html=str(html.relative_to(config.home())),
            ruta_imagen=str(png.relative_to(config.home())) if png.exists() else None,
            estado_http=estado,
        )
    salida = {
        "ok": True,
        "captura_id": captura_id,
        "url": url,
        "sha256": sha,
        "metodo": metodo,
        "estado_http": estado,
        "html": str(html),
        "imagen": str(png) if png.exists() else None,
    }
    if error:
        salida["aviso"] = f"Captura sin navegador ({error}); el HTML puede no incluir contenido cargado con JavaScript"
    return salida
