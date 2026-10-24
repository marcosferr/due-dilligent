"""Los scripts autocontenidos de las skills deben coincidir con la librería."""

import importlib.util
import json
from pathlib import Path

from dd import db, grafo
from dd.ruc import calcular_dv
from dd.variantes import generar_variantes

SKILLS = Path(__file__).resolve().parents[1] / ".claude" / "skills"


def cargar(ruta):
    spec = importlib.util.spec_from_file_location(ruta.stem, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ruc_dv_portatil():
    mod = cargar(SKILLS / "dd-resolucion-entidades" / "scripts" / "ruc_dv.py")
    for n in ["4873598", "1408703", "80900001", "80077412", "123ABC"]:
        assert mod.calcular_dv(n) == calcular_dv(n)
    assert mod.analizar("4873598-1")["valido"]


def test_variantes_portatil():
    mod = cargar(SKILLS / "dd-resolucion-entidades" / "scripts" / "variantes.py")
    for nombre, kw in [("Integralis S. A.", {"dominio": "integraliscorp.com", "formas_extra": ["LLC"]}),
                       ("Constructora Ñandú SRL", {}), ("Acme Inc.", {"comercial": "Acme"})]:
        esperado = generar_variantes(nombre, kw.get("comercial"), kw.get("dominio"), kw.get("formas_extra"))
        assert mod.generar(nombre, kw.get("comercial"), kw.get("dominio"), kw.get("formas_extra")) == esperado


def test_llaves_portatil(tmp_path, capsys, caso):
    with db.conectar() as con:
        db.registrar_entidad(con, caso, "A S.A.", identificadores={"RUC": "80900001-6"}, telefonos=["+595 21 000 111"],
                             correos=["x@a-corp.example"])
        db.registrar_entidad(con, caso, "B S.A.", identificadores={"RUC": "80900002-4"}, telefonos=["021 000111"],
                             dominio="https://www.a-corp.example/")
        esperado = {(k["llave"], k["valor"]) for k in grafo.llaves_compartidas(con, caso)}
        ruta = tmp_path / "caso.json"
        ruta.write_text(json.dumps({"entidades": db.listar_entidades(con, caso)}))
    mod = cargar(SKILLS / "dd-cruces" / "scripts" / "llaves_compartidas.py")
    mod.main([str(ruta)])
    obtenido = {(k["llave"], k["valor"]) for k in json.loads(capsys.readouterr().out)}
    assert obtenido == esperado == {("telefono", "21000111"), ("dominio", "a-corp.example")}


def test_skills_tienen_frontmatter_valido():
    import re

    for skill in SKILLS.iterdir():
        texto = (skill / "SKILL.md").read_text(encoding="utf-8")
        m = re.match(r"^---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n", texto)
        assert m, skill
        nombre, descripcion = m.groups()
        assert nombre == skill.name and re.fullmatch(r"[a-z0-9-]{1,64}", nombre)
        assert "claude" not in nombre and "anthropic" not in nombre
        assert len(descripcion) <= 1024
