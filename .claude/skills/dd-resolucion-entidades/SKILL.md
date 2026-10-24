---
name: dd-resolucion-entidades
description: Resuelve qué entidades legales hay detrás de un nombre o marca de proveedor antes de investigar - razón social exacta, RUC con dígito verificador, entidades hermanas en otros países y variantes de nombre a probar. Usar al empezar un due diligence, cuando un nombre puede ser varias empresas, hay homónimos, o hay que validar un RUC.
---

# Resolución de entidades

La unidad de análisis es la **entidad legal con su identificador**, no el nombre. Esta skill
corre antes de cualquier búsqueda de antecedentes.

## Pasos
1. **Variantes.** `variantes_nombre(nombre, nombre_comercial, dominio, formas_extra)` (dd-registros)
   o `uv run python .claude/skills/dd-resolucion-entidades/scripts/variantes.py "<nombre>" --dominio x --formas LLC`.
   Guardar la lista: se prueba cada variante en cada fuente.
2. **RUC.** Si llegó un RUC: `dnit_validar_ruc` (o `scripts/ruc_dv.py`). Si falta el DV, calcularlo.
   Si el DV no coincide, el RUC está mal escrito: no seguir con ese número.
3. **Razón social ↔ RUC** (en este orden, registrando todo):
   - `dnit_buscar_ruc(nombre=...)` y `dnit_buscar_ruc(ruc=...)`: razón social oficial y estado.
   - `buscar_proveedores(ruc=...)` en dd-dncp; por nombre, `buscar_proveedores(nombre=...)` busca
     en el **nombre de fantasía** y `buscar_procesos(nombre_proveedor=...)` en la **razón social**
     de los adjudicados. Probar las variantes en ambas.
   - Web: sitio de la empresa, directorios. Cada búsqueda con `registrar_consulta`.
4. **Entidades hermanas.** Si la marca menciona otra forma jurídica u otro país (LLC, Inc., sucursal),
   es otra entidad: buscar su registro (`registro_extranjero(nombre, jurisdiccion)`, p. ej. `us_nv`;
   si no hay token o el registro es solo web, `registro_solo_web` + `capturar(usar_navegador=True)`).
   Preguntar también: ¿la entidad extranjera tiene sucursal inscripta y RUC propio en Paraguay?
   (DNIT por nombre; Registros Públicos es brecha).
5. **Registrar** cada entidad con `registrar_entidad`: razón social exacta, tipo (S.A., S.R.L., LLC…),
   país (ISO: PY, US), `identificadores` ({"RUC": "…"} o {"US-NV": "…"}), variantes, dominio,
   teléfonos, correos y direcciones (son las llaves de cruce). `rol`: `investigada` para las del
   proveedor; `relacionada` para hermanas; `competidor` o `convocante` si aparecen después.
   Una entidad que no se pudo identificar se registra igual, sin identificador, y se anota la brecha.
6. **Hallazgo de identidad** por entidad: el registro que la identifica (DNIT/DNCP/registro extranjero)
   como `hecho` con `identificador_que_ata`, capturado.

## Homónimos
- Mismo nombre ≠ misma entidad. Sin un identificador común (RUC, documento, dirección, dominio,
  teléfono), la coincidencia es `posible_alerta`.
- Descartar un homónimo también es un resultado: registrar `contexto` explicando qué identificador
  no coincide (p. ej. "otra entidad: RUC distinto, rubro construcción, Encarnación").
- Mismo apellido no es parentesco. Nunca inferirlo.

## Caso de prueba: una marca, dos entidades
"Integralis" no es un proveedor: es una marca con al menos dos entidades a resolver por separado,
una S.A. paraguaya (buscar su RUC) y una LLC con domicilio en Nevada (buscar su número de registro,
estado, gestores y agente registrado). Los datos de AmCham (rubro, sitio integraliscorp.com,
teléfono) son confiabilidad C hasta verificarlos, y el listado se captura con navegador.
Cada hallazgo se ata a una de las dos entidades, nunca a "Integralis".
