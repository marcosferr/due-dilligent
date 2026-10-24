"""Variantes de nombre y normalización para búsquedas y comparación de entidades.

Lección de la ronda manual: `"Integralis" site:contrataciones.gov.py` no devolvió nada y
`"Integralis S.A"` sí podía hacerlo. Los buscadores no normalizan; por eso se prueba cada
variante en cada fuente.
"""

from __future__ import annotations

import re
import unicodedata

# Formas jurídicas: canónica → maneras en que aparece escrita.
FORMAS_JURIDICAS: dict[str, list[str]] = {
    "S.A.": ["S.A.", "S.A", "S. A.", "S A", "SA", "Sociedad Anónima", "Sociedad Anonima"],
    "S.R.L.": ["S.R.L.", "S.R.L", "SRL", "S. R. L.", "Sociedad de Responsabilidad Limitada"],
    "S.A.E.C.A.": ["S.A.E.C.A.", "SAECA", "S.A.E.C.A", "Sociedad Anónima Emisora de Capital Abierto"],
    "S.A.E.": ["S.A.E.", "S.A.E", "SAE", "S. A. E.", "Sociedad Anónima Emisora"],
    "E.A.S.": ["E.A.S.", "EAS", "Empresa por Acciones Simplificadas"],
    "LLC": ["LLC", "L.L.C.", "Limited Liability Company"],
    "INC": ["Inc.", "Inc", "Incorporated"],
    "CORP": ["Corp.", "Corp", "Corporation"],
    "LTDA": ["Ltda.", "Ltda", "Limitada"],
}



def quitar_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def detectar_forma(nombre: str) -> tuple[str, str | None]:
    """Separa 'Integralis S. A.' en ('Integralis', 'S.A.')."""
    limpio = nombre.strip().rstrip(",")
    for canonica, escrituras in FORMAS_JURIDICAS.items():
        for escritura in sorted(escrituras, key=len, reverse=True):
            patron = r"[\s,]+" + r"\s*".join(re.escape(p) for p in escritura.replace(" ", "")) + r"\.?$"
            m = re.search(patron, limpio, flags=re.IGNORECASE)
            if m:
                return limpio[: m.start()].strip(" ,"), canonica
    return limpio, None


def normalizar(nombre: str, quitar_forma: bool = True) -> str:
    """Clave de comparación: sin acentos, mayúsculas, sin puntuación ni forma jurídica."""
    base, _ = detectar_forma(nombre) if quitar_forma else (nombre, None)
    texto = quitar_acentos(base).upper()
    texto = re.sub(r"[^A-Z0-9&]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def generar_variantes(
    nombre: str,
    nombre_comercial: str | None = None,
    dominio: str | None = None,
    formas_extra: list[str] | None = None,
) -> list[str]:
    """Todas las variantes a probar en cada fuente, sin duplicados y en orden estable.

    Incluye el nombre base sin forma jurídica, cada escritura de su forma (o de las formas
    extra pedidas, p. ej. LLC para una entidad hermana), el nombre comercial y el dominio.
    """
    base, forma = detectar_forma(nombre)
    formas = [forma] if forma else []
    for extra in formas_extra or []:
        _, canon = detectar_forma(f"x {extra}")
        formas.append(canon or extra)

    variantes: list[str] = [nombre.strip(), base]
    for canonica in formas:
        for escritura in FORMAS_JURIDICAS.get(canonica, [canonica]):
            variantes.append(f"{base} {escritura}")
    sin_acentos = quitar_acentos(base)
    if sin_acentos != base:
        variantes.append(sin_acentos)
    variantes.append(base.upper())
    if nombre_comercial:
        variantes.append(nombre_comercial.strip())
    if dominio:
        dominio = re.sub(r"^(https?://)?(www\.)?", "", dominio.strip().lower()).split("/")[0]
        variantes.append(dominio)
        variantes.append(dominio.split(".")[0])

    vistos: set[str] = set()
    salida: list[str] = []
    for v in variantes:
        clave = v.strip().lower()
        if clave and clave not in vistos:
            vistos.add(clave)
            salida.append(v.strip())
    return salida


def tokens(nombre: str) -> set[str]:
    return {t for t in normalizar(nombre).split() if len(t) > 1}


def similitud(a: str, b: str) -> float:
    """Similitud 0–1 entre dos nombres normalizados (mezcla de tokens y secuencia)."""
    from difflib import SequenceMatcher

    na, nb = normalizar(a), normalizar(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb)
    contencion = len(ta & tb) / min(len(ta), len(tb))
    secuencia = SequenceMatcher(None, na, nb).ratio()
    # Mismo nombre en otro orden ("CARTES JARA, Horacio Manuel", como escribe OFAC)
    ordenada = SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    return round(max(secuencia, ordenada, 0.5 * jaccard + 0.5 * contencion * secuencia), 4)
