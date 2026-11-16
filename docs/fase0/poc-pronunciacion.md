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
| Controles A/B/C/D | ✅ hecho | ver tabla abajo |
| P1 Grabaciones es-MX (8–12 hablantes) | ⬜ pendiente | guion `guion-pronunciacion.md` listo; audios fuera de git |
| P2 Bench en frío/caliente | ✅ (Kokoro) | p50 1.61 s / p95 1.95 s por utterance; CLI cold ~28 s; primera síntesis de una frase nueva ~+17 s (kokoro offline) |
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

## 3. Hallazgos de ingeniería (offline real)

- El bench y el pipeline funcionan **sin red** (`--network none`, `HF_HUB_OFFLINE=1`).
- Envolver el proceso con `docker compose --profile poc run` (CLI cold ~28 s) no es apto
  para el loop en vivo; en producción se usaría el servidor OpenPronounce o integración
  directa en `services/pronunciation` (una carga de modelos + peticiones en caliente).
- La red de seguridad técnica está lista para P3; la **decisión de adopción** sigue
  bloqueada por las grabaciones es-MX y las etiquetas humanas (P1).

## 4. Lo que NO se puede afirmar aún

- Precisión/recall del evaluador con inglés hablado por mexicanos (necesita P1+P3).
- Umbrales finales para es-MX (a derivarse de las etiquetas).
- Impacto en latencia del profesor Alex (dependerá de dónde corra: CPU del lab, fuera del
  flujo crítico, o en paralelo a STT como define el maestro §9.3-dual-path).
