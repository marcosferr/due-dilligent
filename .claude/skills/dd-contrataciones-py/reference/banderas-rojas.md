# Banderas rojas seleccionadas (OCDS)

Selección inicial inspirada en la guía de banderas rojas de Open Contracting Partnership
(https://open-contracting.org/redflags, 73 indicadores mapeados a OCDS). **Revisar contra la guía y
ajustar con el equipo antes de la demo.** Una bandera roja es una señal para mirar, nunca una
conclusión: se registra como `posible_alerta` con `categoria_alerta: indicador_ocds_bandera_roja`,
salvo que el criterio del caso diga otra cosa.

| Bandera | Cómo verla con dd-dncp | Por qué importa |
|---|---|---|
| Oferente único | `obtener_record_ocds`: `oferentes == 1` en procesos competitivos | Competencia restringida |
| Plazo de ofertas muy corto | `periodo_ofertas.durationInDays` bajo para la modalidad | Limita la participación |
| Uso frecuente de excepciones o contratación directa | `modalidad` en los procesos del proveedor | Evita la competencia |
| Concentración con un convocante | Mismo `convocante` en gran parte de las adjudicaciones | Posible relación privilegiada |
| Adjudicado ≈ estimado | `adjudicaciones[].monto` muy cercano a `monto_estimado` en varios procesos | Posible filtración de precio |
| Oferentes que comparten datos de contacto | Teléfono, correo, dirección o dominio iguales entre `partes` tenderer (ver dd-cruces) | Posible colusión o ofertas de cobertura |
| Rotación de ganadores | Los mismos oferentes se turnan como ganador en procesos del mismo convocante | Posible reparto de mercado |
| Proveedor ganador con sanción vigente | `sanciones[].vigente` en la fecha de adjudicación | Incumplimiento de inhabilitación |
| Protestas reiteradas | `protestas` en varios procesos ganados | Cuestionamientos del proceso |
| Rubro no coincide con lo adjudicado | `categorias` del proveedor vs. `categoria` del proceso | Empresa de fachada o intermediaria |

Para cada bandera registrar en `extracto` los números concretos (p. ej. "3 de 5 procesos con un solo
oferente: ocds-…, ocds-…") y los `ocid` en el dato.
