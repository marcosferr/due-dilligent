#!/usr/bin/env python3
"""Llaves compartidas entre entidades a partir de uno o más `caso.json` exportados.

Autocontenido (sin dependencias). Misma normalización que `src/dd/grafo.py`.

    python llaves_compartidas.py var/casos/caso-1/caso.json [var/casos/caso-2/caso.json ...]
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict

GENERICOS = {"gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "live.com", "icloud.com", "yahoo.com.ar",
             "hotmail.es", "tigo.com.py", "personal.com.py"}


def tel(t):
    d = re.sub(r"\D", "", t or "")
    return (d[3:] if d.startswith("595") else d).lstrip("0")


def dominio(v):
    v = (v or "").strip().lower()
    if "@" in v:
        v = v.split("@", 1)[1]
    return re.sub(r"^(https?://)?(www\.)?", "", v).split("/")[0]


def direccion(d):
    t = "".join(c for c in unicodedata.normalize("NFKD", d or "") if not unicodedata.combining(c)).upper()
    t = re.sub(r"\b(C/|CASI|ESQ\.?|ESQUINA|N[°º]|NRO\.?|NUMERO)\b", " ", t)
    return re.sub(r"[^A-Z0-9]+", " ", t).strip()


def llaves(e):
    out = defaultdict(set)
    for t in e.get("telefonos") or []:
        if len(tel(t)) >= 6:
            out["telefono"].add(tel(t))
    for c in e.get("correos") or []:
        if "@" in c:
            out["correo"].add(c.strip().lower())
            if dominio(c) not in GENERICOS:
                out["dominio"].add(dominio(c))
    if e.get("dominio"):
        out["dominio"].add(dominio(e["dominio"]))
    for d in e.get("direcciones") or []:
        if len(direccion(d)) >= 8:
            out["direccion"].add(direccion(d))
    return out


def main(rutas):
    indice = defaultdict(dict)
    for ruta in rutas:
        datos = json.load(open(ruta, encoding="utf-8"))
        for e in datos["entidades"]:
            for tipo, valores in llaves(e).items():
                for v in valores:
                    indice[(tipo, v)][(e["caso_id"], e["id"])] = e["razon_social"]
    salida = [
        {"llave": t, "valor": v, "entidades": [{"caso_id": c, "entidad_id": i, "razon_social": n}
                                                for (c, i), n in ents.items()]}
        for (t, v), ents in sorted(indice.items()) if len(ents) > 1
    ]
    print(json.dumps(salida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
