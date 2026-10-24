#!/usr/bin/env python3
"""Valida o calcula el dígito verificador de un RUC paraguayo (módulo 11, base máxima 11).

Autocontenido (sin dependencias) para que la skill funcione fuera del repositorio.
Copia de `src/dd/ruc.py`; `tests/test_skills_scripts.py` verifica que den lo mismo.

    python ruc_dv.py 4873598-1     → válido
    python ruc_dv.py 4873598       → 4873598-1
"""

import json
import re
import sys


def calcular_dv(numero: str, base_max: int = 11) -> int:
    digitos = "".join(c if c.isdigit() else str(ord(c)) for c in numero.strip().upper())
    total, k = 0, 2
    for c in reversed(digitos):
        if k > base_max:
            k = 2
        total += int(c) * k
        k += 1
    resto = total % 11
    return 11 - resto if resto > 1 else 0


def analizar(ruc: str) -> dict:
    ruc = re.sub(r"[\s.]", "", re.sub(r"^PY-RUC-", "", ruc.strip().upper()))
    base, _, dv = ruc.partition("-")
    esperado = calcular_dv(base)
    return {
        "ruc": ruc,
        "dv_informado": int(dv) if dv.isdigit() else None,
        "dv_calculado": esperado,
        "valido": dv.isdigit() and int(dv) == esperado,
        "ruc_completo": f"{base}-{esperado}",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps([analizar(r) for r in sys.argv[1:]], ensure_ascii=False, indent=2))
