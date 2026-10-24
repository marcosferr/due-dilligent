import json

from dd import db, evaluacion


def test_metricas(tmp_path, caso):
    with db.conectar() as con:
        ent, _ = db.registrar_entidad(con, caso, "ALFA FICTICIA S.A.", identificadores={"RUC": "80900001-6"})
        db.registrar_hallazgo(con, caso, ent, "Adjudicado en servicio de vigilancia", "DNCP", "A", "hecho",
                              "encontrado", "mock", url="mock://x", identificador_que_ata="RUC 80900001-6")
        db.registrar_consulta(con, caso, "DNCP", "name='Alfa S.A.'", n_resultados=0, modo_acceso="mock")
    ref = tmp_path / "ref.json"
    ref.write_text(json.dumps({
        "caso": "Alfa", "color_esperado": "verde",
        "hechos": [
            {"id": "A-01", "entidad": {"RUC": "80900001-6"}, "palabras_clave": ["vigilancia"]},
            {"id": "A-02", "entidad": {"RUC": "80900001-6"}, "palabras_clave": ["protesta"]},
        ],
    }))
    r = evaluacion.evaluar(caso, ref)
    assert r["cobertura"]["pct"] == 50.0
    assert r["evidencia_completa"]["pct"] == 0.0
    assert r["no_encontrado_auditable"]["pct"] == 100.0
    assert r["semaforo"]["coincide"] is True
