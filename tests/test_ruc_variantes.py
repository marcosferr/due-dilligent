from dd.ruc import calcular_dv, completar_ruc, normalizar_ruc, validar_ruc
from dd.variantes import detectar_forma, generar_variantes, normalizar, similitud


def test_dv_contra_ruc_reales_de_la_dncp():
    # RUC tomados de respuestas públicas de la API v3 de la DNCP
    assert validar_ruc("4873598-1")
    assert validar_ruc("1408703-0")
    assert not validar_ruc("4873598-2")


def test_normalizar_y_completar():
    assert normalizar_ruc("PY-RUC-4.873.598-1") == "4873598-1"
    assert completar_ruc("4873598") == "4873598-1"
    assert calcular_dv("80900001") == 6


def test_variantes_cubren_las_escrituras_de_la_forma_juridica():
    v = generar_variantes("Integralis S. A.", dominio="https://www.integraliscorp.com/", formas_extra=["LLC"])
    for esperada in ["Integralis", "Integralis S.A.", "Integralis S.A", "Integralis SA",
                     "Integralis Sociedad Anónima", "Integralis LLC", "integraliscorp.com"]:
        assert esperada in v
    assert len(v) == len({x.lower() for x in v})


def test_detectar_forma_y_normalizar():
    assert detectar_forma("INTEGRALIS SOCIEDAD ANONIMA") == ("INTEGRALIS", "S.A.")
    assert detectar_forma("Integralis LLC") == ("Integralis", "LLC")
    assert normalizar("Integrális S.A.") == "INTEGRALIS"


def test_similitud():
    assert similitud("Integralis S.A.", "INTEGRALIS SA") == 1.0
    assert similitud("Integralis", "Constructora Delta") < 0.5
