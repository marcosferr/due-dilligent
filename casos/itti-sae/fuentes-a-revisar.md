# Caso Itti S.A.E.: fuentes a revisar

Corrida del 24/10/2026 (caso 1, modo real, criterio `ejemplo-0.1`). Esta lista es para que el equipo
**revise a mano** cada fuente; el agente no descargó ni guardó en el repositorio documentos de terceros
(las capturas de evidencia quedan locales en `var/casos/caso-1/capturas/`, fuera del control de versiones).

- Ficha completa: [`ficha.md`](ficha.md) · [`ficha.html`](ficha.html) · datos: [`caso.json`](caso.json) · semáforo: [`semaforo.json`](semaforo.json)
- Las referencias `H-n` (hallazgo) y `C-n` (consulta) remiten a la ficha.

> Documento interno de trabajo. El semáforo es una **sugerencia** calculada con el criterio de ejemplo del
> documento de diseño, no con el de la UNI. La conclusión la firma una persona y el proveedor debe poder
> responder antes de cualquier decisión.

## Resultado sugerido y qué lo mueve

**ROJO por puntaje** (P = 9,6; umbral 5), sin reglas duras activadas: no hay inhabilitación vigente, ni
coincidencias en listas de sanciones, ni RUC cancelado. El color depende de que los aportes se mantengan
al revisar las fuentes:

| Si la revisión muestra que… | Efecto en P |
|---|---|
| La fusión ITTI–J. Fleischman es anterior a 2022 (no competían como empresas independientes) → H-21 pasa a contexto | −2 → 7,6 |
| La amonestación de J. Fleischman no corresponde atribuirla al caso (es de la empresa absorbida) → H-18 fuera | −2 |
| Los procesos con oferente único o sobre el estimado tienen explicación en el pliego → H-5, H-6 a contexto | −1 cada uno |
| La DNCP resuelve a favor de ITTI la denuncia de Solubank o la desestima → H-13 fuera | −0,4 |
| La DNCP confirma la denuncia de Solubank con ITTI involucrada | sube; nueva fuente A |

Con H-21 y H-18 explicados, P quedaría en 5,6: todavía rojo con el criterio de ejemplo, pero en el límite.
**El criterio definitivo de la UNI puede cambiar el color.**

## Entidades resueltas

| Entidad | Identificador | Rol | Fuente |
|---|---|---|---|
| ITTI S.A.E. | RUC 80028355-4 (DV válido), ACTIVO | investigada | DNCP H-1, DNIT H-2 |
| J. FLEISCHMAN Y CIA SOCIEDAD ANONIMA | RUC 80001490-1, ACTIVO en DNIT | relacionada (DNCP: "absorbido por ITTI S.A.E.C.A") | H-18, H-19 |
| FIDEICOMISO DE GARANTIA ITTI S.A.E.C.A-BANCO NACIONAL DE FOMENTO | RUC 80141040-1, ACTIVO | relacionada | DNIT H-22 |
| Banco Nacional de Fomento | DNCP-SICP-CODE-191 | convocante principal (10 de 34) | H-4 |
| KONECTA SA / ROSHKA S.A. | RUC 80027374-5 / 80089752-8 | competidores recurrentes | H-8 |

Ojo: **"ITTI S.A.E.C.A." no tiene RUC propio en la DNIT**; el nombre aparece en el fideicomiso y en el
registro DNCP de J. Fleischman. Confirmar si es la misma entidad (cambio de forma jurídica) o un error de carga.

## 1. Prioridad alta: verificar antes de concluir

| # | Fuente | URL | Qué revisar | Hallazgo |
|---|---|---|---|---|
| 1 | Registros Públicos (Dirección General de los Registros Públicos) | presencial / con usuario | Estatuto y directorio de ITTI S.A.E.; **fecha e inscripción de la fusión por absorción** de J. Fleischman y Cía.; accionistas | brecha C-57; afecta H-21, H-18 |
| 2 | DNCP – denuncia del Consorcio Solubank, llamado 445258 | https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-445258-1 (8 protestas o denuncias asociadas) | Estado actual de la denuncia; si hubo resolución, su texto y si involucra a ITTI | H-11, H-13 |
| 3 | DNCP – llamado 480207 (core bancario, 135.853 M PYG) | https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-480207-1 | Acta de apertura de sobres técnicos (29/06/2026), oferentes, dictamen de evaluación cuando se publique | H-14 |
| 4 | DNCP – procesos ITTI vs. J. Fleischman (2022) | [403937](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-403937-1) · [410287](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-410287-1) · [409250](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-409250-1) · [381088](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-381088-1) | Fechas de presentación de ofertas vs. fecha de la fusión; firmantes y representantes de cada oferta | H-21 |
| 5 | DNCP – proveedor J. Fleischman | https://www.contrataciones.gov.py/datos/api/v3/doc/suppliers/80001490-1 | Origen de la amonestación (18/01/2023, sin fecha de fin): proceso y resolución | H-18 |
| 6 | Declaraciones juradas de bienes (Contraloría General de la República) | https://www.contraloria.gov.py/ | Para verificar en fuente oficial la afirmación de ABC Color sobre inversiones declaradas del presidente en la compañía y su desinversión | H-15 (hoy solo prensa, C) |

## 2. Prioridad media: banderas rojas de contrataciones

| # | Fuente | URL | Qué revisar | Hallazgo |
|---|---|---|---|---|
| 7 | LPN 411587 BNF, oferente único (3.200 M PYG) | https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-411587-1 | Pliego: requisitos que pudieron limitar la competencia; consultas y aclaraciones | H-5 |
| 8 | Subasta 467133 BNF, único oferente, +18,6 % sobre el estimado | https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-467133-1 | Justificación de la adjudicación por encima del precio referencial | H-6 |
| 9 | Procesos con adjudicado = estimado (8) | p. ej. https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-439550-1 | Confirmar si son contratos abiertos con monto máximo (explicaría la igualdad) | H-7 |
| 10 | Procesos de software del BNF con Konecta y Roshka | [428009](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-428009-1) · [439550](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-439550-1) · [439551](https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-439551-1) | Informes de evaluación: puntajes de cada oferente | H-8 |
| 11 | Resolución DNCP 4786/23 (protesta de Roshka, rechazada in límine) | https://www.contrataciones.gov.py/documentos/download/marco-legal/61769 | Motivo exacto del rechazo (formal, no de fondo) | H-9 |
| 12 | Resoluciones DNCP 2595/23 y 3086/23 (investigación de oficio 293) | https://www.contrataciones.gov.py/documentos/download/marco-legal/59733 · https://www.contrataciones.gov.py/documentos/download/marco-legal/60179 | Confirmar que la investigación fue sobre el pliego de la Municipalidad y no sobre ITTI | H-10 |
| 13 | Concentración con el BNF (10 de 34) | https://www.contrataciones.gov.py/datos/api/v3/doc/search/processes?awards.suppliers.id=80028355-4 | Montos totales por convocante; relación con el fideicomiso de garantía ITTI–BNF | H-4, H-22 |

## 3. Prensa (confiabilidad C: solo orienta la verificación)

| # | Medio y fecha | URL | Qué dice | Hallazgo |
|---|---|---|---|---|
| 14 | ABC Color, 11/05/2025 | https://www.abc.com.py/economia/2025/05/11/itti-habria-incumplido-un-requisito-sustancial-en-la-licitacion-del-bnf/ | ITTI sin formulario de oferta firmado en 445258; llamado declarado desierto | H-12 |
| 15 | Prensa Mercosur (cita a ABC), 09/12/2025 | https://prensamercosur.org/2025/12/09/al-menos-cinco-articulos-se-violaron-en-licitacion-del-bnf-segun-denuncia/ | Denuncia de Solubank ante la DNCP, pendiente | H-13 |
| 16 | ABC Color, 05/08/2026 | https://www.abc.com.py/economia/2026/08/05/aun-con-solo-dos-competidores-y-cambios-en-el-llamado-bnf-considera-que-proceso-del-core-es-transparente/ | 480207 con dos oferentes; observaciones de Softshop; vínculo con el presidente | H-14, H-15 |
| 17 | ABC Color, 02/08/2026 | https://www.abc.com.py/politica/2026/08/02/bnf-demora-la-evaluacion-tecnica-de-ofertas-para-adquirir-core-bancario/ | Demora en la evaluación técnica | sin registrar: leer |
| 18 | ABC Color, 03/05/2025 · 19/04/2025 · 29/05/2025 | https://www.abc.com.py/economia/2025/05/03/bnf-tuvo-solo-dos-ofertas-del-core-bancario-y-una-de-ellas-es-de-la-itti/ · https://www.abc.com.py/economia/2025/04/19/advertencias-de-limitante-sobresalen-en-licitacion-del-bnf-sobre-home-banking/ · https://www.abc.com.py/economia/2025/05/29/atropellos-en-licitacion-de-bnf-atentan-contra-seguridad-juridica-del-pais-alertan/ | Antecedentes del core bancario y del home banking | sin registrar: leer |
| 19 | Infonegocios | https://infonegocios.com.py/y-ademas/itti-la-fusion-de-dos-grandes-tecnologicos-inaugura-nueva-casa-y-consolida-liderazgo | Fusión con J. Fleischman | H-16 |
| 20 | abogados.com.ar (Ferrere) | https://abogados.com.ar/ferrere-asesora-a-grupo-vazquez-en-adquisicion-tecnologica-local/29942 | Adquisición del 100 % de J. Fleischman por el Grupo Vázquez: **buscar la fecha** | H-16 |
| 21 | Buenos Aires Herald | https://buenosairesherald.com/business/tech/this-top-paraguayan-tech-firm-has-opened-offices-in-buenos-aires-and-its-looking-for-argentine-talent | César Astigarraga como presidente | H-17 |

## 4. Brechas: no se pudo consultar

| Fuente | Motivo | Consulta |
|---|---|---|
| Registros Públicos | Trámite presencial o con usuario | C-57 |
| Poder Judicial (expedientes de ITTI y J. Fleischman) | Sin API; no se automatizó sin revisar los términos de uso | C-58 |
| Certificado DNCP CO-27001-22-221589 (representantes legales) | Devuelve HTML en lugar del PDF; requiere navegador | C-55 |
| Screening PEP | El índice cargado no incluye la colección de PEP de OpenSanctions | C-56 |
| Bolsa de Valores de Asunción / Superintendencia de Valores | No consultado: como S.A.E. (emisora), sus prospectos y hechos relevantes pueden mostrar accionistas y directorio | pendiente |

## 5. Lo que salió limpio

- Sin coincidencias en OpenSanctions (sanciones y exclusiones, incluido el Banco Mundial) ni en OFAC para
  ITTI S.A.E., J. Fleischman y el fideicomiso (C-33 a C-35), ni para las seis personas de contacto
  registradas en la DNCP (C-42 a C-47).
- ITTI S.A.E. no tiene sanciones en la DNCP (H-1).
- Konecta y Roshka no comparten teléfono, correo ni dirección con ITTI (H-8).

## Notas de método

- 58 consultas registradas (18 sin resultado, 4 no accesibles); 22 hallazgos, todos con URL y captura.
- Durante la corrida se corrigieron tres fallas de la herramienta (incluidas en el mismo commit):
  la forma jurídica "S.A.E." no se reconocía; la búsqueda DNIT por nombre podía esconder la coincidencia
  exacta detrás de subcadenas ("SELLITTI"); y la similitud de nombres penalizaba el orden "APELLIDO, Nombre"
  de OFAC. El screening de personas se repitió con la corrección (C-42 a C-47).
- Mismo apellido no es parentesco; un vínculo no es una irregularidad. Las afirmaciones de prensa están
  marcadas como tales.
