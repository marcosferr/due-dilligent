---
name: dd-cruces
description: Cruza personas, empresas y datos de contacto de un due diligence para encontrar vínculos y llaves compartidas (teléfono, correo, dirección, dominio, persona) entre el proveedor, sus entidades hermanas, competidores y funcionarios, con reglas de prudencia. Usar después de recolectar los datos de un caso o cuando pregunten por vínculos, relaciones o conflictos de interés.
---

# Cruces y mapa de vínculos

El vínculo aparece al cruzar fuentes (caso ABC: declaraciones juradas × DNCP). Las llaves de cruce
son personas, direcciones, teléfonos, correos y dominios.

## Pasos
1. Completar las llaves de cada entidad con `actualizar_entidad` (teléfonos, correos, direcciones,
   dominio) a partir de los hallazgos de identidad y de la DNCP.
2. `llaves_compartidas(caso_id)` y `llaves_compartidas(caso_id, entre_casos=true)` (contra casos
   anteriores de la base). Alternativa sin servidor: exportar el caso (`generar_ficha` deja
   `caso.json`) y correr `uv run python .claude/skills/dd-cruces/scripts/llaves_compartidas.py var/casos/caso-N/caso.json`.
3. Para cada llave compartida relevante: registrar un hallazgo (`hecho` si ambas entidades tienen
   identificador y el dato sale de fuentes A/B; si no, `posible_alerta`) y un vínculo con
   `agregar_vinculo` (`mismo_telefono`, `misma_direccion`, `mismo_correo`, `mismo_dominio`) que
   apunte a ese hallazgo. Si además compitieron en el mismo proceso: `compitio_contra` y
   `categoria_alerta: llave_compartida_competidor`.
4. Personas: cada persona con rol público → `registrar_persona` y vínculo (`director`, `accionista`,
   `representante`, `gestor`) con su hallazgo. `screen_persona` para cada una.
5. Entidades hermanas (S.A. ↔ LLC): `misma_marca`. Comparar personas: si coinciden, es contexto que
   explica la relación; si no coinciden y nadie lo explica → `personas_no_coinciden_sin_explicacion`.
   Si el registro extranjero solo muestra un agente registrado → vínculo `agente_registrado` (no
   cuenta como persona vinculada) y `propietarios_no_identificables` como posible alerta.
6. Funcionarios: si una persona del proveedor aparece como funcionaria del convocante
   (`funcionario_en`), registrar con su fuente y etapa temporal (¿coincide con el contrato?).
7. `mapa_vinculos(caso_id)` para revisar el grafo; la ficha lo incluye.

## Reglas de prudencia
- Mismo apellido **no** es parentesco. No existe un tipo de vínculo "parentesco" y no se infiere.
- Un vínculo no es una irregularidad. Se describe con su fuente; no se califica.
- Teléfonos de centrales, estudios contables o agentes registrados compartidos por muchas empresas
  son contexto, no alerta: anotarlo en el `extracto`.
- Dominios genéricos (gmail.com, hotmail.com) no son llave.
- Toda línea del mapa tiene un hallazgo que la respalda; sin hallazgo no hay vínculo.
