# PoC de pronunciación (Fase 0b) — Estado y evidencia

**Regla de decisión (definida por producto):** el go/no-go de Fase 0b no depende del
humo Kokoro sino de métricas contra etiquetas humanas (precisión/recall por palabra
y **falsos positivos**). Score ≥90 con Kokoro = humo técnico, no validación es-MX.

## Estado por paso (2026-11-16)

| Paso | Estado | Evidencia |
|---|---|---|
| P0 Infra (contenedor CPU aislado) | ✅ hecho | `lab/pronunciation/Dockerfile`, stack MIT CPU, Kokoro af_heart como voz de referencia offline; no toca P100/Qwen/LFM/Fedora/NVIDIA |
| Humo Kokoro | ✅ PASS técnico | smoke-think → **98.39** (PER 0.0): audio Kokoro = texto TTS, exactamente pareado |
| Bench automatizado | ✅ hecho | offline (`--network none` + `HF_HUB_OFFLINE=1`); tabla completa abajo; harness `lab/pronunciation/bench.py` |
| Controles A/B/C/D | ✅ hecho | ver §2 |
| Experimento proxy ES (ef_dora/em_alex) | ✅ hecho | §3: scores ~21–24 vs 96.6 nativo → uso sin modificar sería castigo generalizado; la señal favorece «modificar/recalibrar» |
| P1 Grabaciones es-MX (9 hablantes reales) | ✅ hecho (con incidencias) | 270 WAVs recibidos via web recorder y bajados de uploads/ del VPS; fuera de git; s06 = silencio absoluto (repetir) |
| P2 Bench en frío/caliente | ✅ (Kokoro + 9 hablantes reales) | p50 1.61 s / p95 1.95 s por utterance; bench es-MX 270/270 evaluados; tabla completa abajo |
| P3 Calibración vs etiquetas | ⬜ pendiente | requiere P1 + 2 jueces; umbrales propuestos: adoptar precision≥0.70 y recall≥0.80, **FPR≤0.25** (a confirmar con los datos) |
| P4 Informe go/no-go de adopción | ⬜ pendiente | decisión adoptar/modificar/descartar |
| P5 Maestro+backlog (solo si adoptar/modificar) | ⬜ condicional | DOCUMENTO_MAESTRO 1.0→1.1 |

## 1. Bench Kokoro (techo nativo, 30 frases A1–B1, `af_heart`)

`mean_score=96.59 · p50=1.61s · p95=1.95s` (offline, CPU, warm)

| Frase | Score | PER | WER | errores |
|---|---|---|---|---|
| 21 The price of fresh fruit is really high. | 97.94 | 0.04 | 0.00 | 0 |
| 22 She sells fresh fish and chips. | 100.00 | 0.00 | 0.00 | 0 |
| 23 I watch TV on Sundays and shop on Friday. | 93.33 | 0.00 | 0.22 | 0 |
| 24 Chicken, cheese and churros, please! | 91.90 | 0.05 | 0.20 | 0 |
| 25 The teacher teaches touch in class. | 90.46 | 0.10 | 0.17 | 1 («teacher» marcado como error) |
| 26 I bought a very cheap phone with cash. | 100.00 | 0.00 | 0.00 | 0 |
| 27 She lives in a big apartment near the beach. | 100.00 | 0.00 | 0.00 | 0 |
| 28 I drink tea every day at seven. | 100.00 | 0.00 | 0.00 | 0 |
| 29 I would like a chicken sandwich and a drink. | 97.24 | 0.07 | 0.00 | 0 |
| 30 These three things are for them. | 97.50 | 0.06 | 0.00 | 0 |

(Las filas 1–20 pasaron igual — `ok=30`, `mean_score=96.59`; no quedaron versionadas
 porque el volcado JSON cayó en un mount de solo lectura y la salida completa no se
 archivó. El número agregado n=30 es el de referencia.)

**Señal importante:** hasta en audio nativo limpio el evaluador marca errores a veces
(p. ej. «teacher» en la frase 25). Esto indica que sus umbrales de palabra son conservadores
y habrá que vigilar la **tasa de falsos positivos** al calibrar — especialmente en es-MX.

## 2. Controles automatizados

| ID | Control | Score | PER | WER | Errores | Veredicto |
|---|---|---|---|---|---|---|
| A1 | audio «think…» vs texto «How are you?» | 2.94 | 3.60 | 2.33 | 3 | ✅ detecta mismatch |
| A2 | audio «How are you?» vs texto «think…» | 1.01 | 1.00 | 1.00 | 7 | ✅ detecta mismatch |
| B20 | «think…» + ruido blanco SNR 20 dB | 95.76 | 0.00 | 0.00 | 0 | ✅ robusto |
| B10 | «think…» + ruido blanco SNR 10 dB | 96.19 | 0.00 | 0.00 | 0 | ✅ robusto |
| C1 | primeros 0.8 s de «think…» | 39.37 | 0.44 | 0.43 | 2 | ✅ detecta incompleto |
| D1 | «think…» a −15 dB | 99.19 | 0.00 | 0.00 | 0 | ✅ robusto al gain |

- Primera frase con síntesis de referencia nueva (p. ej. A1): ~+17 s adicionales (kokoro
  offline; el coste se paga una vez por frase y se cachea en `/models`).
- La robustez a ruido/gain no dice nada sobre es-MX; es solo verificación funcional.

## 3. Experimento proxy: voces españolas leyendo inglés (ef_dora, em_alex)

Objetivo: aproximar «inglés hablado por un mexicano» sin esperar a humanos y medir
cómo puntuaría OpenPronounce. Generadas las mismas 30 frases con las dos voces ES
de Kokoro y evaluadas offline (mismos comandos de §3). **NO es calibración humana**;
es un test de estrés con acento de TTS (más fuerte que un humano A2 real).

| Voz | mean | min | max | Observación |
|---|---|---|---|---|
| Kokoro af_heart (nativo EN) | 96.59 | 90.46 | 100.00 | techo; incluso native marca «teacher» a veces |
| Kokoro ef_dora (ES, mujer) | **24.41** | 5.00 | 52.16 | PER medio 0.69 |
| Kokoro em_alex (ES, hombre) | **21.63** | 0.00 | 51.55 | PER medio 0.70 |

Detalle representativo (ef_dora): «Three thin things are there.» → 6.00 ·
«My mother and father are together.» → 5.00 · «Rice is delicious with ripe tomatoes.» → 9.80 ·
«Fit or feed, which do you need?» → 38.32 · «The list of seats is little.» → 51.71.

**Interpretación honesta:** el TTS español leyendo inglés produce una fonología
prácticamente sin inventario inglés (Más fuerte que un humano A2 mexicano real), así
que estos números son una **cota inferior agresiva**, no una estimación de precisión
verdadera. Aun así son una señal fuerte:

1. OpenPronounce calibrado en inglés americano es **demasiado estricto para es-MX**:
   marcaría como «mal» prácticamente todo lo que un mexicano diga de corrido.
2. Adoptarlo **sin modificar** los umbrales haría que el MVP castigara a todos los
   alumnos mexicanos — exactamente el modo de falla anti-pedagógico.
3. La mitigación natural es **evaluación selectiva**: evaluar fonemas de alto riesgo
   (/θ, ð, ɪ, iː, ɹ/) con umbrales re-calibrados en es-MX y NO exigir fidelidad
   americana total (p. ej., ignorar variación de /ɹ/ o de vocales reducidas).
4. Los umbrales y pesos (0.3×acústico, 0.4×PER, 0.3×WER, con la PER acoplada a
   "te suenan nativo") pueden ajustarse con el dataset es-MX humano; la fórmula y las
   constantes viven en openpronounce (`openpronounce.speech` / `phones`), licencia MIT.

**Estado de la decisión:** la señal favorece fuertemente «modificar (recalibrar)»
antes que «adoptar tal cual», o incluso que disuade la evaluación global y apunta a
algo más acotado. La decisión real queda supeditada a P1–P3 (humano) — y el go/no-go
de Fase 0b sigue abierto.

## 4. Hallazgos de ingeniería (offline real)

- El bench y el pipeline funcionan **sin red** (`--network none`, `HF_HUB_OFFLINE=1`).
- Envolver el proceso con `docker compose --profile poc run` (CLI cold ~28 s) no es apto
  para el loop en vivo; en producción se usaría el servidor OpenPronounce o integración
  directa en `services/pronunciation` (una carga de modelos + peticiones en caliente).
- La red de seguridad técnica está lista para P3; la **decisión de adopción** sigue
  bloqueada por las grabaciones es-MX y las etiquetas humanas (P1).


## 6. Bench sobre 9 hablantes reales (2026-11-18)

| Hablante | Score mean | PER | WER | Errores flaggeados | Nota |
|---|---|---|---|---|---|
| s02 saw3m5w | 76.86 | 0.13 | 0.13 | 8 | audio estable, buen desempeño |
| s01 s4ytvdu | 72.24 | 0.20 | 0.23 | 16 | audio estable |
| s04 smwbmvr | 69.75 | 0.22 | 0.24 | 15 | audio estable |
| s03 scgmrmf | 68.91 | 0.19 | 0.23 | 12 | audio estable |
| s05 srd6p8h | 52.47 | 0.30 | 0.43 | 25 | señal baja (RMS 110) |
| s07 swe7hwq | 50.96 | 0.37 | 0.45 | 37 | volumen medio-bajo |
| s08 sx29h8t | 46.99 | 0.32 | 0.48 | 30 | señal media-baja |
| s09 szem96e | 22.16 | 0.66 | 0.78 | 96 | señal muy baja (RMS 415) |
| s06 styrwam | **0.00** | **1.00** | **1.00** | **200** | **silencio absoluto** — repetir grabación |

- 270/270 enrolado evaluados. **Media global 51.15** vs 96.59 para Kokoro nativo (techo ilustrativo).
- Normalización a −1 dBFS no cambia la clasificación; NO es problema de ganancia.
- **3 variantes problemáticas** de adquisición: s06 (silencio), s05 y s09 (muy bajo volumen); la calidad mecánica diluye la señal.
- **Interpretación provisional**: lectura no-estadística de que los evaluadores actuales castigan fuertemente el inglés mexicano de nativos; ninguno de los 9 está en el rango "bien pronunciado".
- Conclusión previa:OpenPronounce requiere recalibración o excepciones de tolerancia antes de usarse tal cual.

## 5. Lo que NO se puede afirmar aún

- Precisión/recall del evaluador con inglés hablado por mexicanos (necesita P1+P3).
- Umbrales finales para es-MX (a derivarse de las etiquetas).
- Impacto en latencia del profesor Alex (dependerá de dónde corra: CPU del lab, fuera del
  flujo crítico, o en paralelo a STT como define el maestro §9.3-dual-path).
