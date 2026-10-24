"""Modelo de datos en SQLite.

Tablas del documento de diseño (entidad, persona, vinculo, consulta, hallazgo) más `caso`,
que agrupa una corrida y fija el criterio de semáforo antes de empezar, y `captura`, la
evidencia en disco con su hash. Las reglas de oro se validan acá, no en el prompt.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import config
from .ruc import normalizar_ruc, validar_ruc

CONFIABILIDADES = ("A", "B", "C", "D")
TIPOS_HALLAZGO = ("hecho", "posible_alerta", "contexto")
ESTADOS = ("encontrado", "parcial", "no_encontrado", "no_accesible")
ETAPAS_JUDICIALES = ("denuncia", "imputacion", "acusacion", "condena", "sobreseimiento", "absolucion", "otra")
MODOS_ACCESO = ("api", "descarga", "web", "navegador", "manual", "mock")
TIPOS_VINCULO = (
    "accionista",
    "representante",
    "director",
    "gestor",
    "agente_registrado",  # servicio corporativo: no es persona vinculada (regla del caso Nevada)
    "misma_direccion",
    "mismo_telefono",
    "mismo_correo",
    "mismo_dominio",
    "funcionario_en",
    "compitio_contra",
    "contrato_con",
    "sucesora_de",
    "misma_marca",
)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS caso (
    id INTEGER PRIMARY KEY,
    consulta_inicial TEXT NOT NULL,
    creado_utc TEXT NOT NULL,
    criterio_version TEXT NOT NULL,
    criterio_sha256 TEXT NOT NULL,
    criterio_json TEXT NOT NULL,
    modo TEXT NOT NULL,
    ficha_generada_utc TEXT
);
CREATE TABLE IF NOT EXISTS entidad (
    id INTEGER PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES caso(id),
    razon_social TEXT NOT NULL,
    variantes TEXT NOT NULL DEFAULT '[]',
    tipo TEXT,
    pais TEXT,
    identificadores TEXT NOT NULL DEFAULT '{}',
    dominio TEXT,
    telefonos TEXT NOT NULL DEFAULT '[]',
    correos TEXT NOT NULL DEFAULT '[]',
    direcciones TEXT NOT NULL DEFAULT '[]',
    rol TEXT NOT NULL DEFAULT 'investigada',
    notas TEXT
);
CREATE TABLE IF NOT EXISTS persona (
    id INTEGER PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES caso(id),
    nombre TEXT NOT NULL,
    documento TEXT,
    cargos TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS consulta (
    id INTEGER PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES caso(id),
    fuente TEXT NOT NULL,
    consulta TEXT NOT NULL,
    url TEXT,
    fecha_utc TEXT NOT NULL,
    n_resultados INTEGER,
    modo_acceso TEXT NOT NULL,
    estado TEXT NOT NULL,
    detalle TEXT,
    es_mock INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS captura (
    id INTEGER PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES caso(id),
    url TEXT NOT NULL,
    fecha_utc TEXT NOT NULL,
    ruta_html TEXT,
    ruta_imagen TEXT,
    sha256 TEXT NOT NULL,
    metodo TEXT NOT NULL,
    estado_http INTEGER
);
CREATE TABLE IF NOT EXISTS hallazgo (
    id INTEGER PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES caso(id),
    entidad_id INTEGER NOT NULL REFERENCES entidad(id),
    persona_id INTEGER REFERENCES persona(id),
    dato TEXT NOT NULL,
    extracto TEXT,
    fuente TEXT NOT NULL,
    url TEXT,
    fecha_utc TEXT NOT NULL,
    confiabilidad TEXT NOT NULL,
    tipo TEXT NOT NULL,
    estado TEXT NOT NULL,
    modo_acceso TEXT NOT NULL,
    identificador_que_ata TEXT,
    etapa_judicial TEXT,
    categoria_alerta TEXT,
    regla_dura TEXT,
    consulta_id INTEGER REFERENCES consulta(id),
    captura_id INTEGER REFERENCES captura(id),
    es_mock INTEGER NOT NULL DEFAULT 0,
    advertencias TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS vinculo (
    id INTEGER PRIMARY KEY,
    caso_id INTEGER NOT NULL REFERENCES caso(id),
    desde_tipo TEXT NOT NULL CHECK (desde_tipo IN ('entidad', 'persona')),
    desde_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    hacia_tipo TEXT NOT NULL CHECK (hacia_tipo IN ('entidad', 'persona')),
    hacia_id INTEGER NOT NULL,
    hallazgo_id INTEGER NOT NULL REFERENCES hallazgo(id)
);
CREATE TABLE IF NOT EXISTS cache_http (
    clave TEXT PRIMARY KEY,
    fecha_utc TEXT NOT NULL,
    estado INTEGER NOT NULL,
    cuerpo TEXT NOT NULL
);
"""


class ErrorValidacion(ValueError):
    """Un dato viola una regla de oro y no se guarda."""


def ahora_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def conectar(ruta: Path | None = None) -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(ruta or config.ruta_db(), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(ESQUEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _fila(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for campo in ("variantes", "identificadores", "telefonos", "correos", "direcciones", "cargos", "advertencias"):
        if campo in d and isinstance(d[campo], str):
            d[campo] = json.loads(d[campo])
    return d


def _filas(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [_fila(r) for r in rows]  # type: ignore[misc]


def _elegir(valor: str | None, permitidos: tuple[str, ...], campo: str) -> str | None:
    if valor is None or valor == "":
        return None
    valor = valor.strip().lower() if campo != "confiabilidad" else valor.strip().upper()
    if valor not in permitidos:
        raise ErrorValidacion(f"{campo} inválido: {valor!r}. Permitidos: {', '.join(permitidos)}")
    return valor


# --- caso -----------------------------------------------------------------------------

def leer_criterio(ruta: Path | None = None) -> tuple[dict[str, Any], str, str]:
    texto = (ruta or config.CRITERIO_SEMAFORO).read_text(encoding="utf-8")
    criterio = json.loads(texto)
    return criterio, hashlib.sha256(texto.encode("utf-8")).hexdigest(), texto


def crear_caso(con: sqlite3.Connection, consulta_inicial: str, ruta_criterio: Path | None = None) -> int:
    """Crea el caso y congela el criterio de semáforo vigente (copia + hash)."""
    criterio, sha, texto = leer_criterio(ruta_criterio)
    cur = con.execute(
        "INSERT INTO caso (consulta_inicial, creado_utc, criterio_version, criterio_sha256, criterio_json, modo)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (consulta_inicial, ahora_utc(), criterio.get("version", "sin-version"), sha, texto, config.modo()),
    )
    return int(cur.lastrowid)


def obtener_caso(con: sqlite3.Connection, caso_id: int) -> dict[str, Any]:
    caso = _fila(con.execute("SELECT * FROM caso WHERE id = ?", (caso_id,)).fetchone())
    if caso is None:
        raise ErrorValidacion(f"No existe el caso {caso_id}. Crear uno con crear_caso.")
    return caso


# --- entidades y personas ---------------------------------------------------------------

def registrar_entidad(
    con: sqlite3.Connection,
    caso_id: int,
    razon_social: str,
    *,
    tipo: str | None = None,
    pais: str | None = None,
    identificadores: dict[str, str] | None = None,
    variantes: list[str] | None = None,
    dominio: str | None = None,
    telefonos: list[str] | None = None,
    correos: list[str] | None = None,
    direcciones: list[str] | None = None,
    rol: str = "investigada",
    notas: str | None = None,
) -> tuple[int, list[str]]:
    """Registra una entidad legal. Devuelve (id, advertencias).

    Un RUC paraguayo se normaliza y se valida con su dígito verificador; si el DV no
    coincide se rechaza, porque atar hallazgos a un RUC mal escrito contamina todo el caso.
    """
    obtener_caso(con, caso_id)
    advertencias: list[str] = []
    ids = {k.strip().upper(): str(v).strip() for k, v in (identificadores or {}).items() if str(v).strip()}
    if "RUC" in ids:
        ruc = normalizar_ruc(ids["RUC"])
        if "-" in ruc and not validar_ruc(ruc):
            raise ErrorValidacion(f"RUC {ruc} no pasa la validación del dígito verificador")
        if "-" not in ruc:
            advertencias.append("RUC sin dígito verificador: completarlo con dnit_validar_ruc antes de cruzar")
        ids["RUC"] = ruc
    if not ids:
        advertencias.append(
            "Entidad sin identificador: sus hallazgos solo pueden ser posibles alertas o contexto"
        )
    cur = con.execute(
        "INSERT INTO entidad (caso_id, razon_social, variantes, tipo, pais, identificadores, dominio,"
        " telefonos, correos, direcciones, rol, notas) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            caso_id,
            razon_social.strip(),
            json.dumps(variantes or [], ensure_ascii=False),
            tipo,
            (pais or "").upper() or None,
            json.dumps(ids, ensure_ascii=False),
            (dominio or "").lower() or None,
            json.dumps(telefonos or [], ensure_ascii=False),
            json.dumps(correos or [], ensure_ascii=False),
            json.dumps(direcciones or [], ensure_ascii=False),
            rol,
            notas,
        ),
    )
    return int(cur.lastrowid), advertencias


def actualizar_entidad(con: sqlite3.Connection, entidad_id: int, **campos: Any) -> None:
    """Agrega datos de contacto o identificadores sin perder los anteriores."""
    actual = obtener_entidad(con, entidad_id)
    for campo in ("telefonos", "correos", "direcciones", "variantes"):
        if campos.get(campo):
            actual[campo] = sorted(set(actual[campo]) | set(campos[campo]))
    if campos.get("identificadores"):
        nuevos = {k.upper(): str(v) for k, v in campos["identificadores"].items()}
        if "RUC" in nuevos:
            nuevos["RUC"] = normalizar_ruc(nuevos["RUC"])
            if "-" in nuevos["RUC"] and not validar_ruc(nuevos["RUC"]):
                raise ErrorValidacion(f"RUC {nuevos['RUC']} no pasa la validación del dígito verificador")
        actual["identificadores"].update(nuevos)
    for campo in ("dominio", "tipo", "pais", "notas"):
        if campos.get(campo):
            actual[campo] = campos[campo]
    con.execute(
        "UPDATE entidad SET variantes=?, identificadores=?, telefonos=?, correos=?, direcciones=?,"
        " dominio=?, tipo=?, pais=?, notas=? WHERE id=?",
        (
            json.dumps(actual["variantes"], ensure_ascii=False),
            json.dumps(actual["identificadores"], ensure_ascii=False),
            json.dumps(actual["telefonos"], ensure_ascii=False),
            json.dumps(actual["correos"], ensure_ascii=False),
            json.dumps(actual["direcciones"], ensure_ascii=False),
            actual["dominio"],
            actual["tipo"],
            actual["pais"],
            actual["notas"],
            entidad_id,
        ),
    )


def obtener_entidad(con: sqlite3.Connection, entidad_id: int) -> dict[str, Any]:
    ent = _fila(con.execute("SELECT * FROM entidad WHERE id = ?", (entidad_id,)).fetchone())
    if ent is None:
        raise ErrorValidacion(f"No existe la entidad {entidad_id}")
    return ent


def listar_entidades(con: sqlite3.Connection, caso_id: int) -> list[dict[str, Any]]:
    return _filas(con.execute("SELECT * FROM entidad WHERE caso_id = ? ORDER BY id", (caso_id,)).fetchall())


def registrar_persona(
    con: sqlite3.Connection,
    caso_id: int,
    nombre: str,
    documento: str | None = None,
    cargos: list[str] | None = None,
) -> int:
    """Solo datos públicos ligados al rol en la empresa o en contratos públicos."""
    obtener_caso(con, caso_id)
    cur = con.execute(
        "INSERT INTO persona (caso_id, nombre, documento, cargos) VALUES (?,?,?,?)",
        (caso_id, nombre.strip(), documento, json.dumps(cargos or [], ensure_ascii=False)),
    )
    return int(cur.lastrowid)


def listar_personas(con: sqlite3.Connection, caso_id: int) -> list[dict[str, Any]]:
    return _filas(con.execute("SELECT * FROM persona WHERE caso_id = ? ORDER BY id", (caso_id,)).fetchall())


# --- consultas y capturas ---------------------------------------------------------------

def registrar_consulta(
    con: sqlite3.Connection,
    caso_id: int,
    fuente: str,
    consulta: str,
    *,
    url: str | None = None,
    n_resultados: int | None = None,
    modo_acceso: str = "api",
    estado: str | None = None,
    detalle: str | None = None,
    es_mock: bool = False,
) -> int:
    """Registra una consulta aunque no haya devuelto nada: el "no encontrado" es un resultado."""
    obtener_caso(con, caso_id)
    modo_acceso = _elegir(modo_acceso, MODOS_ACCESO, "modo_acceso") or "api"
    if estado is None:
        estado = "encontrado" if n_resultados else "no_encontrado"
    estado = _elegir(estado, ESTADOS, "estado")
    cur = con.execute(
        "INSERT INTO consulta (caso_id, fuente, consulta, url, fecha_utc, n_resultados, modo_acceso,"
        " estado, detalle, es_mock) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (caso_id, fuente, consulta, url, ahora_utc(), n_resultados, modo_acceso, estado, detalle, int(es_mock)),
    )
    return int(cur.lastrowid)


def listar_consultas(con: sqlite3.Connection, caso_id: int) -> list[dict[str, Any]]:
    return _filas(con.execute("SELECT * FROM consulta WHERE caso_id = ? ORDER BY id", (caso_id,)).fetchall())


def registrar_captura(
    con: sqlite3.Connection,
    caso_id: int,
    url: str,
    sha256: str,
    metodo: str,
    ruta_html: str | None = None,
    ruta_imagen: str | None = None,
    estado_http: int | None = None,
) -> int:
    cur = con.execute(
        "INSERT INTO captura (caso_id, url, fecha_utc, ruta_html, ruta_imagen, sha256, metodo, estado_http)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (caso_id, url, ahora_utc(), ruta_html, ruta_imagen, sha256, metodo, estado_http),
    )
    return int(cur.lastrowid)


def obtener_captura(con: sqlite3.Connection, captura_id: int) -> dict[str, Any] | None:
    return _fila(con.execute("SELECT * FROM captura WHERE id = ?", (captura_id,)).fetchone())


# --- hallazgos ----------------------------------------------------------------------------

def registrar_hallazgo(
    con: sqlite3.Connection,
    caso_id: int,
    entidad_id: int,
    dato: str,
    fuente: str,
    confiabilidad: str,
    tipo: str,
    estado: str,
    modo_acceso: str,
    *,
    url: str | None = None,
    extracto: str | None = None,
    identificador_que_ata: str | None = None,
    etapa_judicial: str | None = None,
    categoria_alerta: str | None = None,
    regla_dura: str | None = None,
    consulta_id: int | None = None,
    captura_id: int | None = None,
    persona_id: int | None = None,
) -> tuple[int, list[str]]:
    """Guarda un hallazgo aplicando las reglas de oro. Devuelve (id, advertencias).

    - Siempre atado a una entidad del caso (nunca a la marca).
    - "hecho" exige un identificador que lo ate (RUC, registro, documento, dominio...);
      si falta, se guarda como posible alerta y se avisa.
    - Una regla dura (rojo directo) solo vale sobre un hecho con confiabilidad A o B.
    - Un caso judicial exige su etapa: denuncia no es imputación ni condena.
    """
    caso = obtener_caso(con, caso_id)
    entidad = obtener_entidad(con, entidad_id)
    if entidad["caso_id"] != caso_id:
        raise ErrorValidacion(f"La entidad {entidad_id} no pertenece al caso {caso_id}")
    if not dato or not dato.strip():
        raise ErrorValidacion("El hallazgo necesita un dato")

    confiabilidad = _elegir(confiabilidad, CONFIABILIDADES, "confiabilidad")
    tipo = _elegir(tipo, TIPOS_HALLAZGO, "tipo")
    estado = _elegir(estado, ESTADOS, "estado")
    modo_acceso = _elegir(modo_acceso, MODOS_ACCESO, "modo_acceso")
    etapa_judicial = _elegir(etapa_judicial, ETAPAS_JUDICIALES, "etapa_judicial")
    advertencias: list[str] = []

    if estado in ("encontrado", "parcial") and not url:
        raise ErrorValidacion("Un hallazgo encontrado necesita la URL exacta de la fuente")

    if tipo == "hecho" and not (identificador_que_ata or "").strip():
        tipo = "posible_alerta"
        advertencias.append("Sin identificador que lo ate: se guardó como posible_alerta, no como hecho")
    if tipo == "hecho" and confiabilidad == "D":
        tipo = "posible_alerta"
        advertencias.append("Fuente D no puede sostener un hecho: se guardó como posible_alerta")

    criterio = json.loads(caso["criterio_json"])
    reglas = {r["id"] for r in criterio.get("reglas_duras", [])}
    if regla_dura:
        if regla_dura not in reglas:
            raise ErrorValidacion(f"regla_dura desconocida {regla_dura!r}. Del criterio: {', '.join(sorted(reglas))}")
        if tipo != "hecho" or confiabilidad not in ("A", "B"):
            advertencias.append(
                "Regla dura ignorada: requiere un hecho con identificador y confiabilidad A o B;"
                " queda como posible alerta a verificar"
            )
            categoria_alerta = categoria_alerta or criterio.get("categoria_regla_dura_no_confirmada", "otra")
            regla_dura = None

    severidades = criterio.get("severidades", {})
    if tipo == "posible_alerta" and not categoria_alerta:
        categoria_alerta = "otra"
    if categoria_alerta and categoria_alerta not in severidades:
        advertencias.append(f"categoria_alerta {categoria_alerta!r} no está en el criterio; se usa 'otra'")
        categoria_alerta = "otra"

    if categoria_alerta and categoria_alerta.startswith("caso_judicial") and not etapa_judicial:
        raise ErrorValidacion("Un caso judicial necesita su etapa (denuncia, imputacion, acusacion, condena...)")

    es_mock = modo_acceso == "mock"
    if consulta_id is not None:
        fila = con.execute("SELECT caso_id, es_mock FROM consulta WHERE id = ?", (consulta_id,)).fetchone()
        if fila is None or fila["caso_id"] != caso_id:
            raise ErrorValidacion(f"La consulta {consulta_id} no existe en el caso {caso_id}")
        es_mock = es_mock or bool(fila["es_mock"])
    if captura_id is not None and obtener_captura(con, captura_id) is None:
        raise ErrorValidacion(f"No existe la captura {captura_id}")
    if estado in ("encontrado", "parcial") and captura_id is None:
        advertencias.append("Sin captura: usar capturar(url) y volver a registrar para tener evidencia completa")

    cur = con.execute(
        "INSERT INTO hallazgo (caso_id, entidad_id, persona_id, dato, extracto, fuente, url, fecha_utc,"
        " confiabilidad, tipo, estado, modo_acceso, identificador_que_ata, etapa_judicial, categoria_alerta,"
        " regla_dura, consulta_id, captura_id, es_mock, advertencias)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            caso_id,
            entidad_id,
            persona_id,
            dato.strip(),
            extracto,
            fuente,
            url,
            ahora_utc(),
            confiabilidad,
            tipo,
            estado,
            modo_acceso,
            identificador_que_ata,
            etapa_judicial,
            categoria_alerta if tipo in ("posible_alerta", "hecho") else None,
            regla_dura,
            consulta_id,
            captura_id,
            int(es_mock),
            json.dumps(advertencias, ensure_ascii=False),
        ),
    )
    return int(cur.lastrowid), advertencias


def listar_hallazgos(
    con: sqlite3.Connection,
    caso_id: int,
    entidad_id: int | None = None,
    tipo: str | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM hallazgo WHERE caso_id = ?"
    args: list[Any] = [caso_id]
    if entidad_id is not None:
        sql += " AND entidad_id = ?"
        args.append(entidad_id)
    if tipo:
        sql += " AND tipo = ?"
        args.append(tipo)
    return _filas(con.execute(sql + " ORDER BY id", args).fetchall())


def obtener_hallazgo(con: sqlite3.Connection, hallazgo_id: int) -> dict[str, Any] | None:
    return _fila(con.execute("SELECT * FROM hallazgo WHERE id = ?", (hallazgo_id,)).fetchone())


# --- vínculos -----------------------------------------------------------------------------

def _existe_nodo(con: sqlite3.Connection, caso_id: int, tipo: str, nodo_id: int) -> bool:
    tabla = "entidad" if tipo == "entidad" else "persona"
    fila = con.execute(f"SELECT caso_id FROM {tabla} WHERE id = ?", (nodo_id,)).fetchone()
    return fila is not None and fila["caso_id"] == caso_id


def registrar_vinculo(
    con: sqlite3.Connection,
    caso_id: int,
    desde_tipo: str,
    desde_id: int,
    tipo: str,
    hacia_tipo: str,
    hacia_id: int,
    hallazgo_id: int,
) -> int:
    """Cada línea del mapa de vínculos tiene su hallazgo (y por lo tanto su fuente).

    No existe un tipo "parentesco": el sistema nunca lo infiere por apellido.
    """
    tipo = _elegir(tipo, TIPOS_VINCULO, "tipo de vínculo")  # type: ignore[assignment]
    for t, i in ((desde_tipo, desde_id), (hacia_tipo, hacia_id)):
        if t not in ("entidad", "persona") or not _existe_nodo(con, caso_id, t, i):
            raise ErrorValidacion(f"No existe {t} {i} en el caso {caso_id}")
    hallazgo = obtener_hallazgo(con, hallazgo_id)
    if hallazgo is None or hallazgo["caso_id"] != caso_id:
        raise ErrorValidacion("Todo vínculo necesita un hallazgo del mismo caso que lo respalde")
    cur = con.execute(
        "INSERT INTO vinculo (caso_id, desde_tipo, desde_id, tipo, hacia_tipo, hacia_id, hallazgo_id)"
        " VALUES (?,?,?,?,?,?,?)",
        (caso_id, desde_tipo, desde_id, tipo, hacia_tipo, hacia_id, hallazgo_id),
    )
    return int(cur.lastrowid)


def listar_vinculos(con: sqlite3.Connection, caso_id: int) -> list[dict[str, Any]]:
    return _filas(con.execute("SELECT * FROM vinculo WHERE caso_id = ? ORDER BY id", (caso_id,)).fetchall())
