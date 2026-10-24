"""Cliente de la API v3 (OCDS) de la DNCP con modo real y modo mock.

Comportamiento comprobado contra la API pública (oct. 2026):
- Sin token se admiten 15 llamadas por minuto (solo pruebas); el límite se aplica acá.
- `GET /search/suppliers?name=` busca por subcadena en el *nombre de fantasía* (`name`),
  no en la razón social (`identifier.legalName`).
- `GET /search/processes?awards.suppliers.name=` sí busca por subcadena en la razón social
  del adjudicado.
- "Sin resultados" vuelve como HTTP 404 con `{"message": "No encontrado"}`.
- Una sanción puede figurar con `status: "Activo"` aunque su `endDate` ya pasó: la vigencia
  se calcula por fechas, y además se anula si un evento posterior la suspende o rehabilita al
  proveedor (medida cautelar del Tribunal de Cuentas).
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from . import config
from .http import ErrorFuente, Respuesta, get, post_json
from .ratelimit import LimiteVelocidad
from .ruc import normalizar_ruc

BASE_URL = "https://www.contrataciones.gov.py/datos/api/v3/doc"
FUENTE = "DNCP API v3 (OCDS)"


class ClienteDNCP:
    def __init__(self, modo: str | None = None) -> None:
        self.modo = modo or config.modo()
        self.base = config.env("DNCP_BASE_URL", BASE_URL).rstrip("/")
        self.request_token = config.env("DNCP_REQUEST_TOKEN")
        por_minuto = int(config.env("DNCP_LLAMADAS_POR_MINUTO", "15") or 15)
        self.limite = LimiteVelocidad("dncp", por_minuto)
        self._token: str | None = None
        self._token_vence = 0.0
        self._mock: MockDNCP | None = MockDNCP() if self.modo == "mock" else None

    @property
    def modo_acceso(self) -> str:
        return "mock" if self._mock else "api"

    def _cabeceras(self) -> dict[str, str]:
        if not self.request_token:
            return {}
        if not self._token or time.time() > self._token_vence:
            self.limite.adquirir()
            r = post_json(f"{self.base}/oauth/token", {"request_token": self.request_token})
            if r.estado != 200:
                raise ErrorFuente(f"OAuth DNCP falló: HTTP {r.estado}")
            datos = r.json()
            self._token = datos.get("access_token") or datos.get("accessToken")
            self._token_vence = time.time() + 14 * 60
        return {"Authorization": self._token or ""}

    def _get(self, ruta: str, params: dict[str, Any] | None = None) -> tuple[Respuesta, Any]:
        """Devuelve (respuesta, datos|None). datos es None cuando la fuente dice "No encontrado"."""
        if self._mock:
            return self._mock.get(self.base, ruta, params or {})
        resp = get(f"{self.base}{ruta}", params=params, headers=self._cabeceras(), limite=self.limite)
        if resp.estado == 404:
            return resp, None
        if resp.estado != 200:
            raise ErrorFuente(f"DNCP respondió HTTP {resp.estado} en {ruta}")
        return resp, resp.json()

    # --- proveedores -----------------------------------------------------------------

    def buscar_proveedores(
        self,
        nombre: str | None = None,
        ruc: str | None = None,
        categoria_id: str | None = None,
        tipo_sancion: str | None = None,
        pagina: int = 1,
        por_pagina: int = 10,
    ) -> tuple[Respuesta, dict[str, Any]]:
        params = {
            "name": nombre,
            "identifier.id": normalizar_ruc(ruc) if ruc else None,
            "details.categories.id": categoria_id,
            "details.sanctions.type": tipo_sancion,
            "page": pagina,
            "items_per_page": min(por_pagina, 50),
        }
        resp, datos = self._get("/search/suppliers", params)
        if datos is None:
            return resp, {"total": 0, "proveedores": []}
        return resp, {
            "total": (datos.get("pagination") or {}).get("total_items", len(datos.get("list", []))),
            "pagina": pagina,
            "proveedores": [proveedor_compacto(p) for p in datos.get("list", [])],
        }

    def obtener_proveedor(self, ruc: str) -> tuple[Respuesta, dict[str, Any] | None]:
        resp, datos = self._get(f"/suppliers/{quote(normalizar_ruc(ruc))}")
        return resp, proveedor_compacto(datos) if datos else None

    # --- procesos y OCDS -------------------------------------------------------------

    def buscar_procesos(
        self,
        ruc_proveedor: str | None = None,
        nombre_proveedor: str | None = None,
        ocid: str | None = None,
        titulo: str | None = None,
        convocante: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        pagina: int = 1,
        por_pagina: int = 10,
    ) -> tuple[Respuesta, dict[str, Any]]:
        params = {
            "awards.suppliers.id": normalizar_ruc(ruc_proveedor) if ruc_proveedor else None,
            "awards.suppliers.name": nombre_proveedor,
            "ocid": ocid,
            "tender.title": titulo,
            "tender.procuringEntity.name": convocante,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "page": pagina,
            "items_per_page": min(por_pagina, 20),
        }
        resp, datos = self._get("/search/processes", params)
        if datos is None:
            return resp, {"total": 0, "procesos": []}
        return resp, {
            "total": (datos.get("pagination") or {}).get("total_items", len(datos.get("records", []))),
            "pagina": pagina,
            "procesos": [record_compacto(r) for r in datos.get("records", [])],
        }

    def obtener_record(self, ocid: str) -> tuple[Respuesta, dict[str, Any] | None]:
        resp, datos = self._get(f"/ocds/record/{quote(ocid)}")
        if not datos:
            return resp, None
        records = datos.get("records") or [datos]
        return resp, record_compacto(records[0], detallado=True)

    def obtener_recurso(self, tipo: str, ident: str) -> tuple[Respuesta, dict[str, Any] | None]:
        """Contrato, adjudicación, protesta o licitación por su id, recortado para el contexto."""
        rutas = {
            "contrato": "/contracts/{}",
            "adjudicacion": "/awards/{}",
            "protesta": "/complaints/{}",
            "licitacion": "/tender/{}",
            "convocante": "/procuringEntities/{}",
        }
        if tipo not in rutas:
            raise ValueError(f"tipo debe ser uno de {', '.join(rutas)}")
        resp, datos = self._get(rutas[tipo].format(quote(ident)))
        return resp, recortar(datos) if datos else None

    def buscar_convocantes(self, nombre: str, pagina: int = 1) -> tuple[Respuesta, dict[str, Any]]:
        resp, datos = self._get("/search/procuringEntities", {"name": nombre, "page": pagina, "items_per_page": 10})
        if datos is None:
            return resp, {"total": 0, "convocantes": []}
        return resp, {
            "total": (datos.get("pagination") or {}).get("total_items"),
            "convocantes": [
                {"id": c.get("id"), "nombre": c.get("name"), "identificador": (c.get("identifier") or {}).get("id")}
                for c in datos.get("list", [])
            ],
        }


# --- transformaciones compactas (respuestas MCP cortas) -----------------------------------

def _fecha(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def sancion_vigente(sancion: dict[str, Any], ahora: datetime | None = None) -> bool:
    """Vigente por fechas: empezó y no terminó. El campo `status` de la fuente no alcanza."""
    ahora = ahora or datetime.now(timezone.utc)
    periodo = sancion.get("period") or {}
    inicio, fin = _fecha(periodo.get("startDate")), _fecha(periodo.get("endDate"))
    if inicio and inicio > ahora:
        return False
    return fin is None or fin >= ahora


_REHABILITACION = re.compile(r"habilitaci[oó]n del proveedor|suspend|levant", re.IGNORECASE)


def sancion_suspendida(sancion: dict[str, Any]) -> bool:
    """Una medida cautelar o una rehabilitación en el SICP deja sin efecto la sanción aunque
    sus fechas sigan corriendo (caso real: A.I. del Tribunal de Cuentas que suspende la resolución)."""
    for ev in sancion.get("events") or []:
        texto = f"{ev.get('title', '')} {ev.get('description', '')}"
        if ev.get("title") != "Inhabilitación creada" and _REHABILITACION.search(texto):
            return True
    return False


def proveedor_compacto(p: dict[str, Any]) -> dict[str, Any]:
    ident = p.get("identifier") or {}
    detalles = p.get("details") or {}
    contacto = p.get("contactPoint") or {}
    direccion = p.get("address") or {}
    sanciones = []
    for s in detalles.get("sanctions") or []:
        periodo = s.get("period") or {}
        por_fechas, suspendida = sancion_vigente(s), sancion_suspendida(s)
        sanciones.append(
            {
                "tipo": s.get("type"),
                "descripcion": s.get("description"),
                "inicio": periodo.get("startDate"),
                "fin": periodo.get("endDate"),
                "estado_segun_fuente": s.get("status"),
                "vigente_por_fechas": por_fechas,
                "suspendida_o_rehabilitada": suspendida,
                "vigente": por_fechas and not suspendida,
                "eventos": [
                    {"titulo": e.get("title"), "fecha": (e.get("date") or "")[:10],
                     "descripcion": (e.get("description") or "")[:400]}
                    for e in s.get("events") or []
                ],
            }
        )
    return {
        "ruc": ident.get("id"),
        "esquema": ident.get("scheme"),
        "razon_social": ident.get("legalName"),
        "nombre_fantasia": p.get("name"),
        "tipo_persona": detalles.get("legalEntityTypeDetail"),
        "tamano": detalles.get("size"),
        "categorias": [c.get("name") for c in detalles.get("categories") or []],
        "contacto": {
            "nombre": contacto.get("name"),
            "telefono": contacto.get("telephone"),
            "fax_o_celular": contacto.get("faxNumber"),
            "correo": contacto.get("email"),
        },
        "direccion": ", ".join(
            x for x in (direccion.get("streetAddress"), direccion.get("locality"), direccion.get("region"),
                        direccion.get("countryName")) if x
        ),
        "sanciones": sanciones,
        "cantidad_adjudicaciones": p.get("cantidad_adjudicaciones"),
        "fecha_dato": p.get("date"),
    }


def _monto(valor: dict[str, Any] | None) -> str | None:
    if not valor or valor.get("amount") is None:
        return None
    return f"{valor.get('amount')} {valor.get('currency', '')}".strip()


def record_compacto(r: dict[str, Any], detallado: bool = False) -> dict[str, Any]:
    cr = r.get("compiledRelease") or r
    tender = cr.get("tender") or {}
    salida: dict[str, Any] = {
        "ocid": cr.get("ocid") or r.get("ocid"),
        "titulo": tender.get("title"),
        "estado": tender.get("statusDetails") or tender.get("status"),
        "modalidad": tender.get("procurementMethodDetails"),
        "categoria": tender.get("mainProcurementCategoryDetails"),
        "convocante": (tender.get("procuringEntity") or cr.get("buyer") or {}).get("name"),
        "periodo_ofertas": tender.get("tenderPeriod"),
        "cubierto_por": tender.get("coveredBy"),
        "adjudicaciones": [
            {
                "id": a.get("id"),
                "proveedores": [
                    {"nombre": s.get("name"), "ruc": normalizar_ruc(s.get("id", ""))} for s in a.get("suppliers") or []
                ],
                "monto": _monto(a.get("value")),
                "fecha": a.get("date"),
                "estado": a.get("statusDetails") or a.get("status"),
            }
            for a in cr.get("awards") or []
        ],
        "contratos": [
            {
                "id": c.get("id"),
                "monto": _monto(c.get("value")),
                "firmado": c.get("dateSigned"),
                "estado": c.get("statusDetails") or c.get("status"),
            }
            for c in cr.get("contracts") or []
        ],
    }
    if detallado:
        salida["oferentes"] = tender.get("numberOfTenderers")
        salida["partes"] = [
            {"id": p.get("id"), "nombre": p.get("name"), "roles": p.get("roles")} for p in cr.get("parties") or []
        ]
        salida["protestas"] = [
            {"id": c.get("id"), "estado": c.get("statusDetails") or c.get("status"), "fecha": c.get("date")}
            for c in cr.get("complaints") or tender.get("complaints") or []
        ]
        salida["monto_estimado"] = _monto(tender.get("value"))
    return salida


def recortar(datos: Any, max_chars: int = 6000) -> Any:
    """Recorta un JSON grande para no superar el límite de tokens de una respuesta MCP."""
    texto = json.dumps(datos, ensure_ascii=False)
    if len(texto) <= max_chars:
        return datos
    return {"recortado": True, "caracteres_totales": len(texto), "inicio": texto[:max_chars]}


# --- modo mock ---------------------------------------------------------------------------

class MockDNCP:
    """Emula los endpoints usados sobre `data/mocks/dncp.json` (datos FICTICIOS).

    Sirve para demos sin red y para pruebas. Todo lo que sale de acá se marca como mock y la
    ficha muestra un aviso: nunca debe confundirse con un dato real.
    """

    def __init__(self) -> None:
        self.datos = json.loads((config.DIR_MOCKS / "dncp.json").read_text(encoding="utf-8"))

    def _resp(self, base: str, ruta: str, params: dict[str, Any], estado: int, cuerpo: Any) -> tuple[Respuesta, Any]:
        consulta = "&".join(f"{k}={v}" for k, v in params.items() if v not in (None, ""))
        url = f"mock://dncp{ruta}" + (f"?{consulta}" if consulta else "")
        texto = json.dumps(cuerpo, ensure_ascii=False)
        from .db import ahora_utc

        return Respuesta(url, estado, texto, ahora_utc()), (cuerpo if estado == 200 else None)

    def get(self, base: str, ruta: str, params: dict[str, Any]) -> tuple[Respuesta, Any]:
        no_encontrado = {"message": "No encontrado", "status": 404}
        proveedores = self.datos["suppliers"]
        records = self.datos["records"]
        partes = ruta.strip("/").split("/")

        if ruta == "/search/suppliers":
            lista = list(proveedores.values())
            if params.get("name"):
                lista = [p for p in lista if params["name"].lower() in p["name"].lower()]
            if params.get("identifier.id"):
                lista = [p for p in lista if p["identifier"]["id"] == params["identifier.id"]]
            if params.get("details.sanctions.type"):
                t = params["details.sanctions.type"]
                lista = [p for p in lista if any(s.get("type") == t for s in p["details"].get("sanctions", []))]
            if not lista:
                return self._resp(base, ruta, params, 404, no_encontrado)
            return self._resp(base, ruta, params, 200, {"list": lista, "pagination": {"total_items": len(lista)}})

        if partes[0] == "suppliers" and len(partes) == 2:
            p = proveedores.get(partes[1])
            return self._resp(base, ruta, params, 200 if p else 404, p or no_encontrado)

        if ruta == "/search/processes":
            lista = records
            if params.get("awards.suppliers.id"):
                rid = params["awards.suppliers.id"]
                lista = [r for r in lista if any(
                    normalizar_ruc(s["id"]) == rid for a in r["compiledRelease"].get("awards", []) for s in a["suppliers"]
                )]
            if params.get("awards.suppliers.name"):
                n = params["awards.suppliers.name"].lower()
                lista = [r for r in lista if any(
                    n in s["name"].lower() for a in r["compiledRelease"].get("awards", []) for s in a["suppliers"]
                )]
            if params.get("ocid"):
                lista = [r for r in lista if r["ocid"] == params["ocid"]]
            if not lista:
                return self._resp(base, ruta, params, 404, no_encontrado)
            return self._resp(base, ruta, params, 200, {"records": lista, "pagination": {"total_items": len(lista)}})

        if partes[:2] == ["ocds", "record"]:
            r = next((x for x in records if x["ocid"] == partes[2]), None)
            return self._resp(base, ruta, params, 200 if r else 404, {"records": [r]} if r else no_encontrado)

        if partes[0] in ("contracts", "awards", "complaints", "tender", "procuringEntities"):
            obj = self.datos.get(partes[0], {}).get(partes[1])
            return self._resp(base, ruta, params, 200 if obj else 404, obj or no_encontrado)

        if ruta == "/search/procuringEntities":
            lista = [c for c in self.datos.get("procuringEntities", {}).values()
                     if params.get("name", "").lower() in c["name"].lower()]
            if not lista:
                return self._resp(base, ruta, params, 404, no_encontrado)
            return self._resp(base, ruta, params, 200, {"list": lista, "pagination": {"total_items": len(lista)}})

        return self._resp(base, ruta, params, 404, no_encontrado)
