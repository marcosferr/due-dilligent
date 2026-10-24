#!/usr/bin/env python3
"""Genera las variantes de nombre a probar en cada fuente.

Autocontenido (sin dependencias). Versión portátil de `src/dd/variantes.py`;
`tests/test_skills_scripts.py` verifica que den lo mismo.

    python variantes.py "Integralis S. A." --dominio integraliscorp.com --formas LLC
"""

import argparse
import json
import re
import unicodedata

FORMAS = {
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


def sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def detectar_forma(nombre: str):
    limpio = nombre.strip().rstrip(",")
    for canonica, escrituras in FORMAS.items():
        for e in sorted(escrituras, key=len, reverse=True):
            patron = r"[\s,]+" + r"\s*".join(re.escape(p) for p in e.replace(" ", "")) + r"\.?$"
            m = re.search(patron, limpio, flags=re.IGNORECASE)
            if m:
                return limpio[: m.start()].strip(" ,"), canonica
    return limpio, None


def generar(nombre, comercial=None, dominio=None, formas_extra=None):
    base, forma = detectar_forma(nombre)
    formas = [forma] if forma else []
    for extra in formas_extra or []:
        formas.append(detectar_forma(f"x {extra}")[1] or extra)
    out = [nombre.strip(), base]
    for f in formas:
        out += [f"{base} {e}" for e in FORMAS.get(f, [f])]
    if sin_acentos(base) != base:
        out.append(sin_acentos(base))
    out.append(base.upper())
    if comercial:
        out.append(comercial.strip())
    if dominio:
        d = re.sub(r"^(https?://)?(www\.)?", "", dominio.strip().lower()).split("/")[0]
        out += [d, d.split(".")[0]]
    vistos, salida = set(), []
    for v in out:
        if v.strip() and v.strip().lower() not in vistos:
            vistos.add(v.strip().lower())
            salida.append(v.strip())
    return salida


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("nombre")
    p.add_argument("--comercial")
    p.add_argument("--dominio")
    p.add_argument("--formas", nargs="*", default=[], help="Formas extra a probar, p. ej. LLC")
    a = p.parse_args()
    base, forma = detectar_forma(a.nombre)
    print(json.dumps({"base": base, "forma_juridica": forma,
                      "variantes": generar(a.nombre, a.comercial, a.dominio, a.formas)}, ensure_ascii=False, indent=2))
