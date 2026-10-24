---
name: dd-ficha
description: Genera la ficha de due diligence de un proveedor en Markdown y HTML desde la base de evidencia - entidades, hallazgos con fuente, fecha y captura, consultas sin resultado, brechas, vínculos y semáforo sugerido con sus razones. Usar al cerrar un caso o cuando pidan la ficha, el informe o el semáforo de un proveedor.
---

# Ficha y semáforo sugerido

La ficha se arma **solo** desde la base (`generar_ficha`); el modelo no escribe filas a mano. El único
texto libre es el resumen, y cada una de sus líneas debe citar `[H-n]` (hallazgo) o `[C-n]` (consulta).
Si una línea no cita un hallazgo existente con URL, la herramienta la rechaza: corregir y reintentar.

## Antes de generar
1. `resumen_caso(caso_id)`: revisar
   - `sin_captura`: capturar y volver a registrar esos hallazgos (o explicar por qué no hay captura).
   - posibles alertas pendientes: confirmar con identificador o dejarlas como están.
   - entidades sin identificador: ¿se pudo resolver? Si no, debe figurar como brecha.
2. Verificar que cada consulta sin resultado tenga su texto exacto (las de dd-* lo tienen; las web,
   si se registraron con `registrar_consulta`).
3. Verificar que ningún hallazgo esté atado a "la marca": cada uno apunta a una entidad concreta.

## Resumen (opcional, recomendado)
Cinco a diez líneas, cada una con su cita. Solo lo que dice la fuente, con la etapa de cada caso
judicial. Sin adjetivos ni conclusiones ("confiable", "riesgoso", "irregular"). Ejemplo:

```
ALFA FICTICIA S.A. (RUC 80900001-6) figura en la DNCP sin sanciones [H-3].
Fue adjudicada en 2 procesos de servicios de seguridad entre 2025 y 2026 [H-5].
Comparte teléfono con BETA FICTICIA S.R.L., que compitió en los mismos procesos [H-9].
No se encontraron resultados en OpenSanctions ni OFAC para ninguna variante del nombre [C-12].
El registro de Nevada no pudo consultarse (solo web) [C-15].
```

## Generar
`generar_ficha(caso_id, resumen)` → `var/casos/caso-N/ficha.md`, `ficha.html`, `semaforo.json` y
`caso.json` (todas las tablas, para auditoría y evaluación). También: `uv run dd ficha N --resumen archivo.txt`.

La estructura está en `templates/ficha.md`. La ficha siempre incluye: avisos (documento interno,
mock, criterio de ejemplo), semáforo con razones enlazadas, entidades, personas, hallazgos por
entidad, consultas sin resultado, brechas, vínculos y llaves, tareas de verificación, qué cambiaría
el resultado, calidad de la evidencia y el bloque de revisión humana.

## Al entregar
Decir el color sugerido **como sugerencia**, sus razones con enlace, las brechas y lo que cambiaría
el resultado. Recordar que la conclusión la firma una persona y que el proveedor debe poder
responder antes de una decisión que lo afecte.
