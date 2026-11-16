# Evaluación del set de 30 prompts es-MX (TD-F0-008/019) — resultado frío

**Fecha:** 2026-11-16 · **Modelo:** Qwen3.5-4B-Q4_K_M (P100, llama.cpp) · **Config:** temp 0.2, `enable_thinking:false`, seed libre · **Evaluación:** match exacto normalizado (estricto).

## Resultado agregado

| Criterio | Resultado | Umbral | ¿Pasa? |
|---|---|---|---|
| JSON válido (claves §8.3) | **30/30 (100%)** | ≥ 29/30 | ✅ |
| Emotion en whitelist | **30/30** | — | ✅ |
| Corrección exacta (normalizada) | **23/30 (77%)** | ≥ 24/30 (80%) | ❌ |

## Análisis de los 7 fallos

| # | Caso | Modelo devolvió | Veredicto real |
|---|---|---|---|
| 04 | a office → an office | `correction: null` | Fallo real (artículo) |
| 14 | He arrived **on** Monday | "I arrived on Monday" | Fallo real (cambió persona: he→I) |
| 16 | want practice → want **to** practice | `correction: null` | Fallo real (to-infinitive) |
| 18 | adverb position | "at 7 o'clock." (omitió "in the morning") | Fallo menor (fija el error pero recorta información; pierde AM/PM) |
| 21 | for 2 years → have been learning… | `correction: null` | Fallo real (present perfect continuous) |
| 27 | comparativo | "more intelligent" (fragmento, no oración completa) | Fallo de formato/parcial |
| 28 | if he **will** come | "is coming tomorrow" | **Alternativa válida** (predicado de movimiento en futuro próximo) |

- **Fallos reales del modelo:** 04, 14, 16, 18, 21 (5) → a lo sumo 25/30 correcto con juicio humano ≈ **83%** — justamente en el umbral §13.2(3) (≥80% en 30 prompts).
- **Artefacto de match estricto:** 28 (y 27 parcialmente) → con juez humano el score sube.
- JSON impecable y `emotion` siempre en whitelist con el prompt pedagógico actual.

## Conclusiones para el AI Router / prompting

1. Los 5 fallos reales se concentran en **estructuras con path "escondido"** (artículo, to-infinitive, present perfect continuous) — susceptibles de mejora con **few-shot (2–3 ejemplos)** en el system prompt o reglas explícitas ("artículos a/an", "want/suggest/recommend + to-infinitive…").
2. Mantener **match estricto** como métrica de regresión del prompt en CI/lab (honestidad > comodidad); permitir alternativas válidas documentadas en el set.
3. El enrutador ya contempla fallback externa para casos difíciles (§8.1, B2+); para A2, estos 5 casos indican que el modelo local es usable pero **no infalible** — coherente con §13.3 (no-go si calidad pedagógica insuficiente).
4. Sugerencia (experimento TD-F0-008b): añadir 2 few-shot al system prompt y re-ejecutar; si el score sube a ≥ 80% estricto sin romper JSON, se adopta como prompt por defecto del lab.

**Veredicto parcial TD-F0-008/019:** JSON ✅ · corrección ⚠️ (77% estricto / ~83% humano; umbral por decidir en el go/no-go) · latency ✅. La decisión go/no-go sigue siendo del equipo, no de este documento.

## Apéndice — experimento few-shot (2026-11-16, mismo set, 2 ejemplos de corrección 3rd person/calco)

| Métrica | Resultado |
|---|---|
| JSON válido | 30/30 (100%) |
| Corrección exacta (estricto) | **19/30 (63%)** — empeora |
| Tiempo medio | ~1.5 s (notablemente más corto) |

Conclusión: el few-shot "imitado" degradó la cobertura de correcciones (el modelo
colapsó hacia el estilo del ejemplo, con respuestas más cortas y más `correction: null`).
**Se rechaza** este few-shot. El prompt por defecto del lab sigue siendo el simple (77%/~83%).
Siguiente experimento válido si se quiere: few-shot con ejemplos del error exacto
(#04, #16, #21) en vez del error ya dominado (#03, #06), o modelo mayor (Agents-A1-35B-A3B,
Dory1.0-4B disponibles en `/home/ancko/models`) midiendo costo/latencia.
