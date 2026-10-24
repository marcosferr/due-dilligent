from dd import sanciones


def test_coincidencia_por_nombre_sin_identificador():
    r = sanciones.screen("Alfa Ficticia S.A.", demo=True)
    refs = {c["ref"]: c for c in r["candidatos"]}
    assert "demo-002" in refs and refs["demo-002"]["coincide_identificador"] is False


def test_coincidencia_confirmada_por_identificador():
    r = sanciones.screen("Beta Ficticia SRL", identificadores=["80900002-4"], demo=True)
    assert r["candidatos"][0]["ref"] == "demo-001"
    assert r["candidatos"][0]["coincide_identificador"] is True


def test_persona_no_matchea_empresas():
    r = sanciones.screen("Juan Ejemplo Ficticio", persona=True, demo=True)
    assert [c["ref"] for c in r["candidatos"]] == ["demo-003"]


def test_indice_real_ausente_lanza():
    import pytest

    with pytest.raises(FileNotFoundError):
        sanciones.screen("x y z", demo=False)
