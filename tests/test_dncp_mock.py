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
