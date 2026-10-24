import pytest

from dd import db


def test_hecho_sin_identificador_se_rebaja_a_posible_alerta(con, caso):
    ent, _ = db.registrar_entidad(con, caso, "Alfa Ficticia S.A.", identificadores={"RUC": "80900001-6"})
    hid, adv = db.registrar_hallazgo(con, caso, ent, "Nota de prensa", "Diario", "C", "hecho", "encontrado", "web",
                                     url="https://ejemplo.org/nota")
    assert db.obtener_hallazgo(con, hid)["tipo"] == "posible_alerta"
    assert any("identificador" in a for a in adv)


def test_ruc_con_dv_incorrecto_se_rechaza(con, caso):
    with pytest.raises(db.ErrorValidacion):
        db.registrar_entidad(con, caso, "X S.A.", identificadores={"RUC": "80900001-5"})


def test_encontrado_sin_url_se_rechaza(con, caso):
    ent, _ = db.registrar_entidad(con, caso, "Alfa", identificadores={"RUC": "80900001-6"})
    with pytest.raises(db.ErrorValidacion):
        db.registrar_hallazgo(con, caso, ent, "dato", "f", "A", "hecho", "encontrado", "api")


def test_caso_judicial_exige_etapa(con, caso):
    ent, _ = db.registrar_entidad(con, caso, "Alfa", identificadores={"RUC": "80900001-6"})
    with pytest.raises(db.ErrorValidacion):
        db.registrar_hallazgo(con, caso, ent, "Causa X", "PJ", "B", "posible_alerta", "encontrado", "web",
                              url="https://pj.example/1", categoria_alerta="caso_judicial_imputacion")


def test_regla_dura_solo_con_hecho_a_o_b(con, caso):
    ent, _ = db.registrar_entidad(con, caso, "Alfa", identificadores={"RUC": "80900001-6"})
    hid, adv = db.registrar_hallazgo(con, caso, ent, "Posible sanción", "Prensa", "C", "hecho", "encontrado", "web",
                                     url="https://x.example", identificador_que_ata="RUC 80900001-6",
                                     regla_dura="inhabilitacion_dncp_vigente")
    h = db.obtener_hallazgo(con, hid)
    assert h["regla_dura"] is None and h["categoria_alerta"] == "regla_dura_sin_confirmar"
    assert adv


def test_no_existe_vinculo_de_parentesco(con, caso):
    ent, _ = db.registrar_entidad(con, caso, "Alfa", identificadores={"RUC": "80900001-6"})
    p = db.registrar_persona(con, caso, "Persona Ficticia")
    hid, _ = db.registrar_hallazgo(con, caso, ent, "Directorio", "f", "B", "hecho", "encontrado", "api",
                                   url="https://x.example", identificador_que_ata="RUC 80900001-6")
    with pytest.raises(db.ErrorValidacion):
        db.registrar_vinculo(con, caso, "persona", p, "parentesco", "entidad", ent, hid)
    assert db.registrar_vinculo(con, caso, "persona", p, "director", "entidad", ent, hid)


def test_criterio_congelado_en_el_caso(con, caso):
    c = db.obtener_caso(con, caso)
    assert c["criterio_version"] == "ejemplo-0.1" and len(c["criterio_sha256"]) == 64
