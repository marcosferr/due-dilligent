# Campos OCDS que importan (y cómo los devuelve dd-dncp)

| Campo OCDS | En la respuesta de dd-dncp | Uso |
|---|---|---|
| `parties[].identifier.id` (esquema `PY-RUC`) | `ruc` | Identificador que ata el hallazgo |
| `parties[].identifier.legalName` | `razon_social` | Razón social oficial |
| `parties[].name` | `nombre_fantasia` | Nombre de fantasía (lo que busca `name=`) |
| `parties[].contactPoint` | `contacto.telefono`, `contacto.correo`, `contacto.fax_o_celular` | Llaves de cruce |
| `parties[].address` | `direccion` | Llave de cruce |
| `parties[].details.sanctions[]` | `sanciones[]` con `vigente_por_fechas` | Reglas duras / sanciones históricas |
| `parties[].details.categories` | `categorias` | Rubro declarado vs. lo que vende |
| `parties[].roles` (`tenderer`, `supplier`, `buyer`) | `partes[].roles` en `obtener_record_ocds` | Competidores y convocantes |
| `tender.numberOfTenderers` | `oferentes` | Oferente único |
| `tender.procurementMethodDetails` | `modalidad` | Contratación directa, excepción, concurso, licitación |
| `tender.tenderPeriod` | `periodo_ofertas` | Plazo de presentación de ofertas |
| `tender.value` | `monto_estimado` | Comparar con lo adjudicado |
| `tender.coveredBy` | `cubierto_por` | Fondos especiales (p. ej. FONACIDE) |
| `awards[].suppliers`, `awards[].value` | `adjudicaciones[]` | Quién ganó y por cuánto |
| `contracts[].id`, `value`, `dateSigned`, `status` | `contratos[]` | Contratos firmados; rescisiones |
| `complaints[]` / `tender.complaints` | `protestas[]` | Protestas y su resultado |
| `buyer`, `tender.procuringEntity` | `convocante` | Concentración por convocante |

Código de contratación: el `id` de contrato (p. ej. `CO-30222-17-147192`) y el `planning.identifier`
(ID de llamado) permiten abrir el proceso en el portal.
