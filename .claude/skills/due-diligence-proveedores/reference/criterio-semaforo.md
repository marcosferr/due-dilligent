# Criterio del semáforo

La fuente de verdad es `config/criterio_semaforo.json` (versionado en el repositorio). Al crear un
caso se guarda una copia y su SHA-256: el criterio no puede cambiar a mitad de un caso, y la ficha
muestra con qué versión se calculó. **Los valores actuales son el ejemplo del documento de diseño;
la UNI debe reemplazarlos antes de usar el sistema.**

## Cómo se calcula

1. **Reglas duras** (deciden solas el color). Solo valen sobre un `hecho` con identificador y
   confiabilidad A o B; si no, el sistema las convierte en posible alerta `regla_dura_sin_confirmar`.
   - `inhabilitacion_dncp_vigente`: inhabilitación con `vigente: true` (por fechas y sin suspensión ni rehabilitación) en la DNCP.
   - `sancion_confirmada_por_identificador`: candidato de `screen_*` con `coincide_identificador: true`.
   - `ruc_cancelado_o_bloqueado`: estado CANCELADO o BLOQUEADO en la DNIT.
2. **Puntaje** sobre hechos y posibles alertas con `categoria_alerta`:
   `P = Σ severidad(categoría) × confianza(A=1.0, B=0.7, C=0.4, D=0)`.
3. **Umbrales**: P = 0 → verde; 0 < P < 5 → amarillo; P ≥ 5 → rojo.

## Qué categoría usar

| Situación | `tipo` | `categoria_alerta` / `regla_dura` |
|---|---|---|
| Inhabilitación DNCP vigente por fechas | hecho (A) | `regla_dura: inhabilitacion_dncp_vigente` |
| Inhabilitación o amonestación DNCP ya cumplida | hecho (A) | `sancion_dncp_historica` |
| Lista de sanciones, mismo identificador | hecho (B) | `regla_dura: sancion_confirmada_por_identificador` |
| Lista de sanciones, solo nombre | posible_alerta | `coincidencia_sancion_solo_nombre` |
| RUC cancelado o bloqueado | hecho (A) | `regla_dura: ruc_cancelado_o_bloqueado` |
| RUC con suspensión temporal | hecho (A) | `ruc_suspendido` |
| Causa judicial | según atadura | `caso_judicial_denuncia` / `_imputacion` / `_acusacion` / `_condena` + `etapa_judicial` |
| Protesta o reclamo en la DNCP contra o del proveedor | hecho | `protesta_o_reclamo` |
| Rescisión o incumplimiento de contrato | hecho | `incumplimiento_contractual` |
| Comparte teléfono/dirección/correo con un competidor del mismo proceso | hecho | `llave_compartida_competidor` |
| El registro no permite saber quién está detrás | posible_alerta | `propietarios_no_identificables` |
| Las personas de entidades hermanas no coinciden y nadie lo explica | posible_alerta | `personas_no_coinciden_sin_explicacion` |
| Nota de prensa negativa | posible_alerta (C) | `prensa_negativa` |
| Bandera roja OCDS (ver dd-contrataciones-py) | según dato | `indicador_ocds_bandera_roja` |
| Dato neutro (RUC activo, contrato adjudicado, LLC existente) | hecho / contexto | sin categoría |

La ficha siempre muestra tres listas: las razones del color con su enlace, las brechas y lo que
cambiaría el resultado. Verde no certifica ausencia de riesgo.
