"""RUC paraguayo: normalización y dígito verificador (módulo 11, base máxima 11)."""

from __future__ import annotations

import re


def calcular_dv(numero: str, base_max: int = 11) -> int:
    """Dígito verificador del RUC según el algoritmo módulo 11 publicado por la SET/DNIT.

    Los caracteres no numéricos (RUC antiguos con letras) se reemplazan por su código ASCII.
    """
    numero = numero.strip().upper()
    digitos = "".join(c if c.isdigit() else str(ord(c)) for c in numero)
    if not digitos:
        raise ValueError("RUC vacío")
    total, k = 0, 2
    for c in reversed(digitos):
        if k > base_max:
            k = 2
        total += int(c) * k
        k += 1
    resto = total % 11
    return 11 - resto if resto > 1 else 0


def normalizar_ruc(ruc: str) -> str:
    """'80.012.345-6' → '80012345-6'; quita prefijos de esquema OCDS como 'PY-RUC-'."""
    ruc = ruc.strip().upper()
    ruc = re.sub(r"^PY-RUC-", "", ruc)
    ruc = re.sub(r"[\s.]", "", ruc)
    return ruc


def separar(ruc: str) -> tuple[str, int | None]:
    ruc = normalizar_ruc(ruc)
    if "-" in ruc:
        base, dv = ruc.rsplit("-", 1)
        return base, int(dv) if dv.isdigit() else None
    return ruc, None


def validar_ruc(ruc: str) -> bool:
    base, dv = separar(ruc)
    if dv is None or not base:
        return False
    try:
        return calcular_dv(base) == dv
    except ValueError:
        return False


def completar_ruc(ruc: str) -> str:
    """Devuelve el RUC con su DV calculado ('80012345' → '80012345-X')."""
    base, _ = separar(ruc)
    return f"{base}-{calcular_dv(base)}"
