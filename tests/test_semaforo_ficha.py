import pytest

from dd import db, ficha, grafo, semaforo


def _base(con, caso):
    alfa, _ = db.registrar_entidad(con, caso, "ALFA FICTICIA S.A.", identificadores={"RUC": "80900001-6"},
                                   telefonos=["021 000 111"])
    beta, _ = db.registrar_entidad(con, caso, "BETA FICTICIA S.R.L.", identificadores={"RUC": "80900002-4"},
                                   telefonos=["(021) 000-111"], rol="competidor")
    return alfa, beta


def test_verde_sin_alertas(con, caso):
    alfa, _ = _base(con, caso)
    db.registrar_hallazgo(con, caso, alfa, "RUC activo", "DNCP", "A", "hecho", "encontrado", "api",
                          url="mock://dncp/x", identificador_que_ata="RUC 80900001-6")
    assert semaforo.calcular(con, caso)["color_sugerido"] == "verde"


def test_regla_dura_da_rojo(con, caso):
    _, beta = _base(con, caso)
    db.registrar_hallazgo(con, caso, beta, "Inhabilitación vigente", "DNCP", "A", "hecho", "encontrado", "api",
                          url="mock://dncp/s", identificador_que_ata="RUC 80900002-4",
                          regla_dura="inhabilitacion_dncp_vigente")
    s = semaforo.calcular(con, caso)
    assert s["color_sugerido"] == "rojo" and s["reglas_duras"]


def test_puntaje_y_fuente_d_vale_cero(con, caso):
    alfa, _ = _base(con, caso)
    db.registrar_hallazgo(con, caso, alfa, "Homónimo en lista", "OS", "B", "posible_alerta", "encontrado", "descarga",
                          url="https://os.example/1", categoria_alerta="coincidencia_sancion_solo_nombre")
    db.registrar_hallazgo(con, caso, alfa, "Rumor", "Foro", "D", "posible_alerta", "encontrado", "web",
                          url="https://foro.example", categoria_alerta="prensa_negativa")
    s = semaforo.calcular(con, caso)
    assert s["puntaje"] == 2.1 and s["color_sugerido"] == "amarillo"
    assert any("Fuente D" in t["motivo"] for t in s["tareas_verificacion"])


def test_llave_compartida_telefono(con, caso):
    _base(con, caso)
    llaves = grafo.llaves_compartidas(con, caso)
    assert llaves and llaves[0]["llave"] == "telefono" and len(llaves[0]["entidades"]) == 2


def test_resumen_sin_cita_se_rechaza(con, caso):
    alfa, _ = _base(con, caso)
    hid, _ = db.registrar_hallazgo(con, caso, alfa, "RUC activo", "DNCP", "A", "hecho", "encontrado", "api",
                                   url="mock://dncp/x", identificador_que_ata="RUC 80900001-6")
    assert ficha.validar_texto(con, caso, f"El RUC figura activo [H-{hid}].") == []
    assert ficha.validar_texto(con, caso, "La empresa es confiable.")
    assert ficha.validar_texto(con, caso, "Dato [H-999].")


def test_generar_ficha_md_y_html(caso):
    with db.conectar() as con:
        alfa, _ = _base(con, caso)
        hid, _ = db.registrar_hallazgo(con, caso, alfa, "RUC activo", "DNCP", "A", "hecho", "encontrado", "mock",
                                       url="mock://dncp/x", identificador_que_ata="RUC 80900001-6")
        db.registrar_consulta(con, caso, "DNCP", "search/suppliers name='Alfa SA'", n_resultados=0,
                              modo_acceso="mock", es_mock=True)
    out = ficha.generar(caso, f"El RUC figura activo [H-{hid}].")
    md = open(out["markdown"], encoding="utf-8").read()
    html = open(out["html"], encoding="utf-8").read()
    assert "DATOS FICTICIOS" in md and "Consultas sin resultado" in md and "Alfa SA" in md
    assert "<table>" in html and "VERDE" in html
    with pytest.raises(ficha.ErrorFicha):
        ficha.generar(caso, "Afirmación sin fuente")
