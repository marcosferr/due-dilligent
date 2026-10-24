import pytest


@pytest.fixture(autouse=True)
def entorno_aislado(tmp_path, monkeypatch):
    """Cada prueba usa su propia base y carpeta de datos, en modo mock y sin red."""
    monkeypatch.setenv("DD_HOME", str(tmp_path / "var"))
    monkeypatch.setenv("DD_MODO", "mock")
    monkeypatch.delenv("DNCP_REQUEST_TOKEN", raising=False)
    monkeypatch.delenv("OPENCORPORATES_API_TOKEN", raising=False)
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    yield


@pytest.fixture
def con():
    from dd import db

    with db.conectar() as c:
        yield c


@pytest.fixture
def caso(con):
    from dd import db

    caso_id = db.crear_caso(con, "Proveedor de prueba")
    con.commit()
    return caso_id
