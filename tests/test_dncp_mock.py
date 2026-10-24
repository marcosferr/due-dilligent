from dd import dncp
from dd.dncp import ClienteDNCP, sancion_vigente


def test_buscar_por_nombre_de_fantasia_y_404_como_no_encontrado():
    c = ClienteDNCP(modo="mock")
    _, r = c.buscar_proveedores(nombre="beta")
    assert r["total"] == 1 and r["proveedores"][0]["razon_social"] == "BETA FICTICIA S.R.L."
    resp, r = c.buscar_proveedores(nombre="integralis")
    assert r["total"] == 0 and resp.estado == 404


def test_vigencia_por_fechas_no_por_status():
    c = ClienteDNCP(modo="mock")
    _, beta = c.obtener_proveedor("80900002-4")
    _, gamma = c.obtener_proveedor("PY-RUC-80900003-2")
    assert beta["sanciones"][0]["vigente_por_fechas"] is True
    assert gamma["sanciones"][0]["estado_segun_fuente"] == "Activo"
    assert gamma["sanciones"][0]["vigente_por_fechas"] is False


def test_procesos_por_razon_social_y_record_con_competidores():
    c = ClienteDNCP(modo="mock")
    _, r = c.buscar_procesos(nombre_proveedor="alfa ficticia")
    assert r["total"] == 2
    _, rec = c.obtener_record("ocds-mock-1002")
    roles = {p["nombre"]: p["roles"] for p in rec["partes"]}
    assert "tenderer" in roles["GAMMA FICTICIA S.A."] and rec["oferentes"] == 3


def test_sancion_sin_fin_es_vigente():
    assert sancion_vigente({"period": {"startDate": "2020-01-01T00:00:00Z"}})


def test_recortar():
    assert dncp.recortar({"x": "a" * 10000}, 100)["recortado"] is True


def test_sancion_suspendida_por_cautelar_no_es_vigente():
    # Forma real de la API: inhabilitación con fechas vigentes, suspendida por el Tribunal de Cuentas
    p = {"identifier": {"id": "2515412-5"}, "details": {"sanctions": [{
        "type": "INHABILITACION", "status": "Activo", "description": "mala fe",
        "period": {"startDate": "2025-09-16T00:00:00-04:00", "endDate": "2099-09-16T00:00:00-04:00"},
        "events": [
            {"title": "Inhabilitación creada", "description": "mala fe", "date": "2025-09-16T08:00:00-04:00"},
            {"title": "Habilitación del proveedor", "date": "2025-11-26T10:00:00-04:00",
             "description": "Auto Interlocutorio N° 728/25 ... SUSPENDER, los efectos de la Res. DNCP ..."},
        ]}]}}
    s = dncp.proveedor_compacto(p)["sanciones"][0]
    assert s["vigente_por_fechas"] is True
    assert s["suspendida_o_rehabilitada"] is True and s["vigente"] is False
