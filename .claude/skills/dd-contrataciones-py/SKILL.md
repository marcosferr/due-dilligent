---
name: dd-contrataciones-py
description: Consulta contrataciones públicas paraguayas de un proveedor en la DNCP (API v3 OCDS) por MCP - adjudicaciones, contratos, sanciones e inhabilitaciones, protestas, competidores y banderas rojas. Usar en el bloque de contrataciones de un due diligence o cuando pregunten por licitaciones, contratos o sanciones DNCP de un RUC.
---

# Contrataciones públicas (DNCP)

Herramientas del servidor `dd-dncp`. Todas piden `caso_id` y registran la consulta sola, incluso
cuando no hay resultados. Sin token hay **15 llamadas por minuto** compartidas: preferir el RUC al
nombre, no repetir consultas (hay caché de 24 h) y paginar solo si hace falta.

## Comportamiento de la API (comprobado)
- `buscar_proveedores(nombre=...)` busca por subcadena en el **nombre de fantasía**, no en la razón social.
- `buscar_procesos(nombre_proveedor=...)` busca por subcadena en la **razón social** de los adjudicados.
- Solo los adjudicados aparecen en `buscar_procesos`; los oferentes que perdieron están en
  `obtener_record_ocds(ocid).partes` con rol `tenderer`.
- "Sin resultados" = `estado: no_encontrado` (la API devuelve 404). Es un resultado: ya quedó
  registrado; probar las demás variantes antes de concluir nada.
- Una sanción puede decir `estado_segun_fuente: "Activo"` con fecha de fin pasada. Usar
  `vigente`.

## Pasos por entidad con RUC
1. `obtener_proveedor(caso_id, ruc)`: razón social, nombre de fantasía, contacto, dirección,
   categorías, sanciones, cantidad de adjudicaciones.
   - Hallazgo de identidad (`hecho`, A, `identificador_que_ata: "RUC …"`).
   - Cada sanción: `hecho` A. INHABILITACION con `vigente: true` → `regla_dura: inhabilitacion_dncp_vigente`.
     Ya cumplida → `categoria_alerta: sancion_dncp_historica`. Copiar la descripción en `extracto`.
   - Si `suspendida_o_rehabilitada: true` (p. ej. medida cautelar del Tribunal de Cuentas), **no** aplicar
     la regla dura aunque las fechas sigan corriendo: registrar la sanción con `sancion_dncp_historica` y
     copiar en `extracto` el evento que la suspende (resolución, auto interlocutorio, fecha).
   - Teléfono, correo y dirección → `actualizar_entidad` (llaves de cruce).
2. `buscar_procesos(caso_id, ruc_proveedor=ruc)`: total de procesos adjudicados; revisar las páginas
   necesarias. Para la ficha alcanza un hallazgo `contexto` con el total y los procesos relevantes
   (montos más altos, mismos convocantes, excepciones).
3. Para los procesos relevantes: `obtener_record_ocds(caso_id, ocid)`: oferentes (competidores),
   cantidad de oferentes, protestas, contratos. Revisar banderas rojas (`reference/banderas-rojas.md`).
4. Protestas, contratos o adjudicaciones puntuales: `obtener_recurso(caso_id, tipo, id)`.
5. Competidores frecuentes: registrarlos como entidad (`rol: competidor`) con su RUC y contacto
   (`obtener_proveedor`) para que `dd-cruces` detecte llaves compartidas. Cuidar el cupo de llamadas:
   solo los que compiten en varios procesos con el proveedor.

## Pasos por nombre (sin RUC o para entidades hermanas)
Para cada variante: `buscar_proveedores(nombre=variante)` y `buscar_procesos(nombre_proveedor=variante)`.
Si aparece un RUC, validarlo y volver a los pasos por RUC. Si una entidad extranjera figura como
proveedora, anotar el identificador que usa (campo "R.U.C. / IDAP" o esquema distinto de PY-RUC).

## Evidencia
La URL de la evidencia es la de la API (pública, se puede abrir sin token). Capturar con
`capturar(caso_id, url)` antes de registrar el hallazgo y pasar `consulta_id` y `captura_id`.
En modo mock las URL empiezan con `mock://` y todo se marca como ficticio.

## Qué preguntas responde este bloque (caso Integralis)
- ¿Qué entidad figura como proveedora en la DNCP: la S.A. con RUC o la LLC con identificador extranjero?
- ¿Tiene sanciones o inhabilitaciones, vigentes o cumplidas?
- ¿Con qué convocantes contrató, por qué montos y en qué modalidades?
- ¿Contra quién compitió? ¿Comparte teléfono, dirección o dominio con algún competidor?
