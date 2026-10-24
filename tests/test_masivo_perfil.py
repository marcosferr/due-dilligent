"""Carga de los datos masivos de la DNCP (CSV OCDS aplanados) y perfil comparativo."""

import csv
import io
import zipfile

from dd import masivo, perfil

P = "compiledRelease/"
A = P + "awards/0/"
C = P + "contracts/0/"
T = C + "implementation/transactions/0/"


def _csv(cols, filas):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(cols)
    w.writerows(filas)
    return buf.getvalue()


def _zips(tmp_path):
    awa, con = tmp_path / "awa.zip", tmp_path / "con.zip"
    with zipfile.ZipFile(awa, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("records.csv", _csv(
            [P + "id", P + "ocid", P + "tender/title", P + "tender/procuringEntity/id", P + "tender/procuringEntity/name",
             P + "tender/procurementMethodDetails", P + "tender/value/amount", P + "tender/value/currency",
             P + "tender/numberOfTenderers"],
            [["r1", "ocds-1", "Título con\r\nsalto de línea", "C1", "Banco X", "Licitación Pública Nacional", "1000", "PYG", "1"],
             ["r2", "ocds-2", "Otro", "C2", "Ministerio Y", "Contratación Directa", "500", "PYG", "1"],
             ["r3", "ocds-3", "Tercero", "C1", "Banco X", "Concurso de Ofertas", "300", "PYG", "3"]]))
        z.writestr("awards.csv", _csv(
            [P + "id", A + "id", A + "status", A + "date", A + "value/amount", A + "value/currency"],
            [["r1", "a1", "active", "2024-03-01T00:00:00-04:00", "1100", "PYG"],
             ["r2", "a2", "active", "2025-05-01T00:00:00-04:00", "500", "PYG"],
             ["r3", "a3", "active", "2025-06-01T00:00:00-04:00", "200", "PYG"],
             ["r3", "a4", "active", "2025-06-01T00:00:00-04:00", "90", "PYG"]]))
        z.writestr("awa_suppliers.csv", _csv(
            [P + "id", A + "id", A + "suppliers/0/id", A + "suppliers/0/name"],
            [["r1", "a1", "PY-RUC-80900001-6", "ALFA"], ["r2", "a2", "PY-RUC-80900001-6", "ALFA"],
             ["r3", "a3", "PY-RUC-80900001-6", "ALFA"], ["r3", "a4", "PY-RUC-80900002-4", "BETA"]]))
        z.writestr("awa_items.csv", _csv(
            [P + "id", A + "id", A + "items/0/description", A + "items/0/classification/id",
             A + "items/0/classification/description", A + "items/0/quantity", A + "items/0/unit/name",
             A + "items/0/unit/value/amount", A + "items/0/unit/value/currency"],
            [["r1", "a1", "Toner", "44103103-001", "Toner", "10", "Unidad", "200", "PYG"],
             ["r3", "a4", "Toner", "44103103-001", "Toner", "5", "Unidad", "100", "PYG"]]))
    with zipfile.ZipFile(con, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("contracts.csv", _csv(
            [P + "id", C + "id", C + "awardID", C + "dateSigned", C + "value/amount", C + "value/currency"],
            [["r1", "K1", "a1", "2024-03-10", "1100", "PYG"], ["r2", "K2", "a2", "2025-05-10", "500", "PYG"]]))
        z.writestr("con_imp_transactions.csv", _csv(
            [P + "id", C + "id", T + "id", T + "value/amount", T + "value/currency", T + "date", T + "requestDate",
             T + "payer/id", T + "payee/id", T + "sourceSystem"],
            [["r1", "K1", "t1", "550", "PYG", "2024-06-15", "2024-06-05", "C1", "PY-RUC-80900001-6", "SICP"],
             ["r1", "K1", "t1", "550", "PYG", "2024-06-15", "2024-06-05", "C1", "PY-RUC-80900001-6", "SICP"]]))
    return awa, con


def test_carga_deduplica_y_perfil(tmp_path):
    awa, con_zip = _zips(tmp_path)
    conteo = masivo.cargar_anio(2025, items_rucs=None, origen_awa=awa, origen_con=con_zip)
    assert conteo["adjudicacion"] == 4 and conteo["pago"] == 2
    masivo.cargar_anio(2026, origen_awa=awa, origen_con=con_zip)  # el paquete siguiente repite registros
    con = masivo.conectar()
    assert con.execute("SELECT COUNT(*) FROM adjudicacion").fetchone()[0] == 4
    assert con.execute("SELECT COUNT(*) FROM pago").fetchone()[0] == 1
    assert "salto de línea" in con.execute("SELECT titulo FROM proceso WHERE release_id='r1'").fetchone()[0]

    p = perfil.perfil(con, "80900001-6")
    assert p["escala"]["adjudicaciones"] == 3 and p["escala"]["monto_adjudicado_pyg"] == 1800
    assert p["escala"]["por_anio"][2025]["monto_pyg"] == 700
    assert p["dependencia"]["principal_convocante"] == "Banco X"
    assert p["modalidad"]["pct_monto_no_competitivo"] == round(100 * 500 / 1800, 1)
    # competitivos con dato: r1 (1 oferente) y r3 (3); la directa r2 no cuenta
    assert p["competencia"]["pct_oferente_unico"] == 50.0
    # r1 (1100/1000) y r2 (500/500) tienen una sola adjudicación en su proceso; r3 tiene dos y no compara
    assert p["precio"]["procesos_comparables"] == 2
    assert p["precio"]["mediana_adjudicado_sobre_estimado"] == 1.05
    assert p["ejecucion"]["monto_pagado_pyg"] == 550 and p["ejecucion"]["pct_pagado_de_lo_contratado"] == 34.4
    assert p["ejecucion"]["mediana_dias_solicitud_a_pago"] == 10.0
    assert perfil.perfil(con, "80900001-6", desde=2025)["escala"]["adjudicaciones"] == 2


def test_items_y_comparacion(tmp_path):
    awa, con_zip = _zips(tmp_path)
    masivo.cargar_anio(2025, contratos=False, items_rucs=["80900001-6", "80900002-4"], origen_awa=awa)
    con = masivo.conectar()
    filas = perfil.precios_vs_mercado(con, "80900001-6", minimo_comparables=2)
    assert filas[0]["relacion"] == round(200 / 150, 2) and filas[0]["comparables"] == 2
    comp = perfil.comparar(["80900001-6", "80900002-4"], con_api=False)
    assert comp["tabla"][0][1:] == ["ALFA", "BETA"]
    md = perfil.a_markdown(comp)
    assert "| 2025 |" in md and "contexto para comparar" in md


def test_estado_sin_datos():
    assert masivo.estado()["disponible"] is False
