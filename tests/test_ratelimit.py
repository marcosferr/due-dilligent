from dd.ratelimit import LimiteVelocidad


def test_limite_espera_cuando_se_agota_el_cupo(tmp_path):
    reloj = {"t": 1000.0}
    esperas = []

    def dormir(s):
        esperas.append(s)
        reloj["t"] += s

    lim = LimiteVelocidad("prueba", 15, reloj=lambda: reloj["t"], dormir=dormir, ruta=tmp_path / "rl.json")
    for _ in range(15):
        assert lim.adquirir() == 0
    esperado = lim.adquirir()
    assert esperado > 59 and len(esperas) == 1


def test_limite_compartido_entre_instancias(tmp_path):
    reloj = lambda: 50.0  # noqa: E731
    ruta = tmp_path / "rl.json"
    a = LimiteVelocidad("x", 2, reloj=reloj, dormir=lambda s: None, ruta=ruta)
    b = LimiteVelocidad("x", 2, reloj=reloj, dormir=lambda s: None, ruta=ruta)
    a.adquirir()
    b.adquirir()
    try:
        b.adquirir(espera_maxima=1)
    except TimeoutError:
        pass
    else:
        raise AssertionError("debió agotarse el cupo compartido")
