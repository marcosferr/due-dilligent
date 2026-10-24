"""CLI `dd`: preparación de fuentes, salud, fichas y evaluación.

    uv run dd descargar-fuentes [--dnit] [--sin-opensanctions] [--sin-ofac]
    uv run dd salud
    uv run dd caso nuevo "Integralis S.A."
    uv run dd caso resumen 1
    uv run dd ficha 1
    uv run dd evaluar 1 eval/referencia/integralis.json
    uv run dd descargar-fuentes --dncp-masivo 2020-2026 [--items RUC ...]
    uv run dd comparar 80028355-4 80027374-5 --desde 2022 --salida casos/comparaciones/itti
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

from . import config, db, ficha, registros, sanciones

OPENSANCTIONS = {
    "sanctions": "https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv",
    "debarment": "https://data.opensanctions.org/datasets/latest/debarment/targets.simple.csv",
}
OFAC_SDN = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"


def _bajar(url: str, destino: Path) -> Path:
    print(f"  ↓ {url}")
    with httpx.stream("GET", url, follow_redirects=True, timeout=300,
                      headers={"User-Agent": config.USER_AGENT}) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for trozo in r.iter_bytes(1 << 20):
                f.write(trozo)
    print(f"    {destino.stat().st_size / 1e6:.1f} MB → {destino}")
    return destino


def cmd_descargar(args: argparse.Namespace) -> None:
    d = config.dir_fuentes()
    archivos: list[tuple[str, Path]] = []
    if not args.sin_opensanctions:
        print("OpenSanctions (CC BY-NC 4.0, uso no comercial):")
        for nombre, url in OPENSANCTIONS.items():
            archivos.append(("opensanctions", _bajar(url, d / f"opensanctions-{nombre}.csv")))
    if not args.sin_ofac:
        print("OFAC SDN:")
        archivos.append(("ofac", _bajar(OFAC_SDN, d / "ofac-sdn.csv")))
    if archivos:
        print("Construyendo índice de sanciones…")
        print(json.dumps(sanciones.construir_indice(archivos, sanciones.ruta_indice()), indent=2))
    if args.dnit:
        print("DNIT – listado de RUC (10 archivos):")
        print(f"  {registros.descargar_dnit():,} RUC indexados")
    if args.dncp_masivo:
        from . import masivo

        desde, _, hasta = args.dncp_masivo.partition("-")
        for anio in range(int(desde), int(hasta or desde) + 1):
            print(f"DNCP masivo {anio} (solo los CSV necesarios, por rango HTTP)…", flush=True)
            print("  ", masivo.cargar_anio(anio, contratos=not args.sin_contratos, items_rucs=args.items))


def cmd_salud(_: argparse.Namespace) -> None:
    """Prueba de salud por fuente: una llamada mínima a cada una."""
    from .dncp import ClienteDNCP

    filas = []
    try:
        resp, datos = ClienteDNCP().buscar_proveedores(tipo_sancion="INHABILITACION", por_pagina=1)
        filas.append(("DNCP API v3", "ok" if datos["total"] else "sin datos", resp.url))
    except Exception as e:  # noqa: BLE001
        filas.append(("DNCP API v3", f"FALLA: {e}", ""))
    estado = sanciones.estado_indice(demo=config.modo() == "mock")
    filas.append(("Índice de sanciones", "ok" if estado["disponible"] else "no construido",
                  str(estado.get("construido_utc", ""))))
    filas.append(("DNIT listado RUC", "ok" if registros.ruta_dnit().exists() else "no descargado", ""))
    filas.append(("OpenCorporates", "token configurado" if config.env("OPENCORPORATES_API_TOKEN") else "sin token (brecha)", ""))
    filas.append(("SAM.gov", "clave configurada" if config.env("SAM_API_KEY") else "sin clave (brecha)", ""))
    for f in filas:
        print(f"{f[0]:<22} {f[1]:<24} {f[2]}")


def cmd_caso(args: argparse.Namespace) -> None:
    with db.conectar() as con:
        if args.accion == "nuevo":
            print(json.dumps({"caso_id": db.crear_caso(con, args.valor)}))
        else:
            from .servers.evidencia import resumen_caso

            print(json.dumps(resumen_caso(int(args.valor)), ensure_ascii=False, indent=2))


def cmd_ficha(args: argparse.Namespace) -> None:
    resumen = Path(args.resumen).read_text(encoding="utf-8") if args.resumen else None
    print(json.dumps(ficha.generar(args.caso_id, resumen), ensure_ascii=False, indent=2))
    print(ficha.exportar_caso(args.caso_id))


def cmd_comparar(args: argparse.Namespace) -> None:
    from . import perfil

    comp = perfil.comparar(args.rucs, args.desde, args.hasta, con_api=not args.sin_api)
    md = perfil.a_markdown(comp)
    if args.salida:
        salida = Path(args.salida)
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "comparacion.md").write_text(md, encoding="utf-8")
        (salida / "comparacion.json").write_text(json.dumps(comp, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"→ {salida}/comparacion.md y comparacion.json")
    print(md)


def cmd_evaluar(args: argparse.Namespace) -> None:
    from .evaluacion import evaluar

    print(json.dumps(evaluar(args.caso_id, Path(args.referencia)), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="dd", description="Due diligence de proveedores")
    sub = p.add_subparsers(dest="comando", required=True)
    d = sub.add_parser("descargar-fuentes", help="Baja OpenSanctions, OFAC y (opcional) DNIT y arma índices")
    d.add_argument("--dnit", action="store_true", help="También el listado de RUC de la DNIT (~40 MB)")
    d.add_argument("--sin-opensanctions", action="store_true")
    d.add_argument("--sin-ofac", action="store_true")
    d.add_argument("--dncp-masivo", metavar="AÑOS", help="Datos masivos OCDS de la DNCP, p. ej. 2020-2026")
    d.add_argument("--sin-contratos", action="store_true", help="Con --dncp-masivo: solo adjudicaciones")
    d.add_argument("--items", nargs="*", metavar="RUC", help="Con --dncp-masivo: ítems con precio de estos RUC")
    d.set_defaults(func=cmd_descargar)
    sub.add_parser("salud", help="Prueba mínima de cada fuente").set_defaults(func=cmd_salud)
    c = sub.add_parser("caso", help="Crear un caso o ver su resumen")
    c.add_argument("accion", choices=["nuevo", "resumen"])
    c.add_argument("valor")
    c.set_defaults(func=cmd_caso)
    f = sub.add_parser("ficha", help="Generar la ficha de un caso")
    f.add_argument("caso_id", type=int)
    f.add_argument("--resumen", help="Archivo de texto con el resumen (cada línea cita [H-n])")
    f.set_defaults(func=cmd_ficha)
    k = sub.add_parser("comparar", help="Tabla comparativa de varios proveedores (datos masivos DNCP)")
    k.add_argument("rucs", nargs="+")
    k.add_argument("--desde", type=int)
    k.add_argument("--hasta", type=int)
    k.add_argument("--salida", help="Carpeta donde guardar comparacion.md y comparacion.json")
    k.add_argument("--sin-api", action="store_true", help="No consultar tamaño y sanciones en la API")
    k.set_defaults(func=cmd_comparar)
    e = sub.add_parser("evaluar", help="Comparar un caso con la respuesta de referencia")
    e.add_argument("caso_id", type=int)
    e.add_argument("referencia")
    e.set_defaults(func=cmd_evaluar)
    args = p.parse_args(argv)
    try:
        args.func(args)
    except (db.ErrorValidacion, ficha.ErrorFicha, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
