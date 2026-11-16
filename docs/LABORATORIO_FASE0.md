# LABORATORIO_FASE0 — Evidencia de validación de IA (talkdrill)

**Regla:** ninguna fase 1+ se ejecuta hasta que este documento declare *go*.
Criterios de aprobación: `DOCUMENTO_MAESTRO.md` §13.2 · Criterios de no-go y plan B: §13.3 · Backlog: `TD-F0-001…020`.

## 1. Entorno

| Componente | Detalle |
|---|---|
| Host | Fedora (sesión Wayland), `/home/dev/share/issitekLanguage` (repo independiente) |
| GPU | NVIDIA Tesla P100-PCIE 16 GB, 16384 MiB, driver 580.196.07, CDI `nvidia.com/gpu=0` (~18 MiB usados al inicio del lab) |
| CPU/RAM | ver `nproc` en el host (≥ 18 hilos para llama.cpp) |
| Docker | 29.9.2 · Compose v5.6.1 |
| Modelos locales | `/home/ancko/models/qwen3.5-4b/Qwen3.5-4B-Q4_K_M.gguf` (2.7 GB, montaje read-only) |
| Imágenes locales | `ghcr.io/ggml-org/llama.cpp:server-cuda`, `coturn/coturn:latest` |
| Puertos lab | 3478 (+49152–49200 relay), 9080 (LLM), 9081 (STT, reservado), 9082 (TTS, reservado), 9090 (lab-server) |

Aislamiento: contenedores `talkdrill-lab-*` propios, red dedicada, puertos solo en `127.0.0.1`
(salvo coturn en modo host, como mxerp). **No se modifican** drivers, Fedora, juegos ni contenedores
Qwen/LFM existentes. Secreto TURN propio (`talkdrill-lab`) vía `.env.lab` (no versionado).

## 2. Matriz de pruebas

| Dimensión | Caso | Estado | Evidencia |
|---|---|---|---|
| Cliente | Chrome escritorio (Fedora) — conexión, audio loopback, DataChannel | ⬜ pendiente verificación manual | |
| Cliente | Android real (Chrome/Capacitor build de prueba) | ⬜ pendiente (dispositivo) | |
| Cliente | iPhone real (Safari/WKWebView) | ⬜ pendiente (dispositivo) | |
| Red | Wi-Fi local | ⬜ pendiente | |
| Red | Datos móviles | ⬜ pendiente | |
| Red | NAT restrictivo forzando `relay` con coturn | ⬜ pendiente | |
| Audio | Permiso micrófono / denegación / re-solicitud | ⬜ pendiente | |
| Audio | Audífonos con mic y sin mic | ⬜ pendiente | |
| Sesión | Suspensión y reanudación de app (móvil/navegador) | ⬜ pendiente | |
| Sesión | Reconexión tras corte 10 s / 60 s | ⬜ pendiente (TD-F0-017) | |
| Sesión | Barge-in: alumno interrumpe al profesor | ⬜ pendiente (TD-F0-013) | |
| Modelo | STT es-MX base/small (faster-whisper) | 🟡 smoke test OK (espeak-ng); voz humana pendiente | §3.4 |
| Modelo | STT CPU fallback | ✅ PASS (STT solo CPU en este host) | §3.4 |
| Modelo | LLM Qwen3.5-4B — calidad pedagógica (set prompts §fase0) | 🟡 bench TTFT/tok/s ejecutado (PASS); set 30 prompts pendiente | `lab/bench_llm.py`, §3.2 |
| Red | coturn lab Allocate + relay HMAC (automatizado) | ✅ PASS (2026-11-16) | §3.1 |
| E2E | aiortc echo + DataChannel (automatizado) | ✅ PASS (2026-11-16) | §3.3 |
| E2E | Conversación completa aiortc (WAV Kokoro como mic) | ✅ PASS (2026-11-16) · STT CPU 4.6 s | §3.5 |
| Pronunciación | PoC OpenPronounce (humo + bench + proxy ES) | ✅ offline CPU · Kokoro 96.59 nativo · proxy ES ~21–24 (sin calibrar castiga a es-MX) · es-MX humano pendiente | §3.6 |
| Modelo | TTS EN Kokoro 82M | ✅ PASS (0.56 s/utterance CPU) | §3.4 |
| Modelo | TTS ES (Kokoro ES o Qwen3-TTS 0.6B) | ⬜ pendiente (TD-F0-010) | |
| E2E | Loop WebRTC→STT→LLM→TTS→RTP→visemes (automatizado) | ✅ PASS (2026-11-16) · Chrome manual pendiente | §3.5 |
| E2E | Sesión estable ≥ 15 min | ⬜ pendiente | |
| Negocio | Costo por minuto local vs externo | ⬜ pendiente (TD-F0-018) | |

## 3. Resultados (se rellenan al ejecutar)

### 3.1 coturn lab — Allocate con credencial HMAC (TD-F0-002) — ✅ PASS (2026-11-16 UTC)

- `POST /ice-credentials` del lab-server cuaja `<expira>_talkdrill` con HMAC-SHA1, separador `_`, TTL 300 s.
- `turnutils_uclient -C _ -u <ts>_talkdrill -w <cred> -y 127.0.0.1`: **Allocate OK**, `Received relay addr: 192.168.1.42:49160` (dentro del rango 49152–49200), channel bind OK, 0% pérdida media útil, RTT 0.25 ms.
- Contenedor `lab-coturn-1` (imagen local `coturn/coturn:latest`), `network_mode: host`. Secreto propio vía `.env.lab` (no versionado). STUN en 3478 responde.

### 3.2 LLM — TTFT y throughput (TD-F0-008) — ✅ PASS con hallazgo (2026-11-16 UTC)

`python3 lab/bench_llm.py` — 6 prompts del set §fase0, `enable_thinking:false`, temp 0.4:

| Prompt (alumno) | TTFT | total | tok/s |
|---|---|---|---|
| Yesterday I go to the school. | 0.43 s | 2.42 s | 46.0 |
| I have saw that movie three times. | 0.24 s | 2.62 s | 50.5 |
| She don't like coffee. | 0.25 s | 1.97 s | 48.7 |
| I work in a office near downtown. | 0.25 s | 1.02 s | 42.9 |
| How many money do you need? | 0.22 s | 2.34 s | 50.5 |
| I am agree with you. | 0.24 s | 2.54 s | 50.4 |

**Hallazgos:**
1. **Qwen3.5-4B razona por defecto** (`reasoning_content` antes que `content`). Sin desactivarlo, el TTFT clínicamente útil no llega y el bench queda inutilizable para conversación. Con `chat_template_kwargs: {"enable_thinking": false}`: TTFT 0.22–0.43 s y ~43–50 tok/s de generación en P100. **Decisión para la arquitectura:** la conversación siempre llama con thinking desactivado; thinking queda para usos offline (análisis de sesión, currículum adaptativo).
2. **Calidad pedagógica de muestra** (`Yesterday I go to the school.`): corrección correcta (`went`, artículo omitido), explicación amable en español, JSON válido según maestro §8.3.
3. **Desviación de esquema:** el modelo devolvió `"emotion": "encouraged"` (no está en el enum `encouraging`). El **AI Router debe normalizar** emociones (whitelist + sinónimos) antes de mandarlas al avatar; añadirlo a TD-F2-002.
4. Set de 30 prompts ejecutado (TD-F0-008/019): **JSON 30/30, emociones 30/30, corrección 23/30 (77% estricto)**; fallos reales: artículos, to-infinitive, present perfect continuous (y un cambio de persona en #14). Ver `docs/fase0/resultados-30-prompts.md`.
5. Experimento few-shot: 19/30 (63%) — rechazado; prompt por defecto simple.

GPU LLM (lab): ~3.3 GB VRAM (Q4_K_M). Con VAD+Whisper+TTS caben en los 16 GB de la P100.

### 3.3 E2E echo aiortc (TD-F0-003/004) — ✅ PASS (2026-11-16 UTC)

`docker compose --env-file .env.lab exec -T -e LAB_TOKEN=… -e LAB_SERVER_URL=http://lab-server:9090 lab-server python /app/tests/test_echo_e2e.py`

```
{"connectionState": "connected", "audio_frames_recibidos": 22,
 "tipos_datachannel": ["listening_state", "assistant_response"], "pass": true}
```

- WebRTC navegador ↔ aiortc ↔ navegador vía el mismo PC (echo): audio de vuelta recibido en ~1 s.
- DataChannel `events` entrega `listening_state` y `assistant_response` (visemas incluidos) → página `http://127.0.0.1:9090/` lista para TD-F0-004 manual (Chrome escritorio) y para el guion de Fase 0 en Android/iPhone.
- Pendiente en este entorno: prueba manual Chrome, Android real, iPhone real, relay forzado, reconexión, barge-in real, loop E2E con STT/TTS real, evaluación del set de 30 prompts.

### 3.5 Loop conversacional E2E (TD-F0-011/012) — ✅ PASS automatizado (2026-11-16 UTC)

`python /app/tests/test_conversation_e2e.py` (cliente aiortc envía `s02.wav` Kokoro
"Yesterday I went to school." como micrófono; el servidor responde por RTP):

```
connectionState: connected
assistant_text: "¡Muy bien! Tu frase es correcta y natural. ¡Buen trabajo!"
correction: null           ← correcto: la frase no tenía error (esquema §8.3 normalizado)
emotion: encouraging
visemes: 45 (heurística texto→visema; el TTS remsky no expone pistas fonéticas)
metrics: stt_ms 4584 · llm_ms ~900-1700 · tts_ms ~900-1050 · turno total ~6.4 s
pass: true · audio del profesor: ~450 frames Opus
```

**Latencia primer-voz (medido):** STT CPU int8 **≈4.6 s** domina el turno (Beam 5, ~4 s de
utterance con pre/post silencio). LLM ~1-1.7 s (enable_thinking=false). TTS ~1 s.
La meta < 2.5 s de inicio de voz **no se cumple en este host por el STT en CPU**
(faster-whisper CT2/CUDA 12 no soporta Pascal sm_60). Requiere GPU sm_70+ o STT
externo; ver riesgo R11 (maestro §15). El resto del pipeline (LLM+TTS+eventos) va holgado.

Notas:
- Modo `echo` preservado para regresión (`LAB_MODE=echo`); verificado también hoy.
- Barge-in implementado en servidor (VAD + cancelación de SpeakerTrack + evento `interrupt`)
  pero **pendiente de prueba humana con audífonos** (TD-F0-013) — no medible sin altavoces.
- La corrección con `original == corrected` se normaliza a `null` en el servidor.

### 3.6 Fase 0b — PoC OpenPronounce (humo Kokoro) — ✅ PASS técnico (2026-11-16 UTC)

Dato crítico para el go/no-go: el humo con Kokoro **solo** valida integración técnica;
la evidencia de es-MX vendrá de las etiquetas humanas (P1–P4, pendiente).

- Contenedor `talkdrill-lab-pronunciation` (CPU, aislado de la P100 y de Qwen/LFM; openpronounce MIT; torch CPU; `OPENPRONOUNCE_TTS=kokoro` voz af_heart). Primero run ~2.4 GB de checkpoints Wav2Vec2 + `spacy download en_core_web_sm` horneado en la imagen (sin red en runtime).
- Humo (frases exactas, WAV Kokoro): `smoke-think.wav` → **score 98.39**, PER 0.0; `smoke-howareyou.wav` → **score 100.0**.
- **Bench offline** (`--network none` + `HF_HUB_OFFLINE=1`, CPU, warm): **mean 96.59** sobre las 30 frases Kokoro; **p50 1.61 s / p95 1.95 s** por utterance. Señal: hasta nativo marca errores a veces («teacher» en frase 25, 90.46) — vigilar FPR al calibrar.
- **Controles A/B/C/D** (automatizados): mismatch A1/A2 → score ~1–3 con errores detectados; ruido SNR 10/20 dB → ~96 (intacto); truncado 0.8 s → 39.37 con 2 errores; −15 dB → 99.19. Ver `docs/fase0/poc-pronunciacion.md` para tablas y comandos exactos.
- Latencia CLI ~28 s por utterance en frío (CPU); el bench se medirá en caliente/servidor (P2).
- Datos: `lab/data/pronunciation/` (audio/consent/labels/manifest) **excluidos de git** (`lab/data/` en `.gitignore`); consentimiento obligatorio con plantilla `docs/fase0/consentimiento-plantilla.md`.
- Guion de 30 frases orientadas /θ ð ɪ iː ɹ ʃ tʃ/: `docs/fase0/guion-pronunciacion.md`. Plantillas: `labels-template.csv`. Consentimiento: `consentimiento-plantilla.md`.

**Aguarda:** recolección + etiquetado es-MX (2 jueces) → bench → calibración → informe
`docs/fase0/poc-pronunciacion.md` con decisión adoptar/modificar/descartar. El go/no-go
de Fase 0 queda condicionado a este análisis (precision/recall por palabra + falsos positivos).

### 3.4 STT / TTS — ✅ PASS en EN (2026-11-16 UTC)

**TTS EN (Kokoro 82M, `remsky/kokoro-fastapi-cpu` en 127.0.0.1:9082, voz `af_heart`):**
- Síntesis de ~1 s de audio en **0.56 s** en CPU (RTF < 1) → la TTS no será el cuello de botella.
- 10 frases A1–A2/en-US generadas y guardadas en `lab/data/s01…s10.wav` (24 kHz mono PCM).

**STT EN (faster-whisper **small**, CPU int8, imagen `talkdrill-lab-stt` provisionada hoy):**
- Transcripción de las 10 frases Kokoro: **WER = 0.000 (10/10)**, latencia media **~2.2 s** por frase.
- Nota metodológica: son audios limpios sintetizados; el WER real con voz humana,
  ruido y acento mexicano se medirá con el piloto (no extrapolable de este bench).

**STT es-MX (smoke test, `bench-es.wav` de VozNativa, espeak-ng es-419 — NO voz humana):**
- Hipótesis: «Hola, quiero crear una nueva cotización para el cliente con los productos que necesita.»
  (esperado: «**Ahora**, quiero crear…») → 1 palabra confundida (Ahora→Hola), resto correcto.
- Válido como smoke test; la validación con voz humana en es-MX queda pendiente (dispositivo/piloto).

**Restricción de la P100:** faster-whisper (CTranslate2, CUDA 12) no soporta Pascal (sm_60);
el STT corre en CPU en este host. Aceptable para desarrollo; producción requiere GPU sm_70+
o build compatible (nuevo riesgo R11 en maestro §15). Qwen3.5-4B (llama.cpp GGUF) sí aprovecha la P100 (~3.3 GB VRAM).

**Pendiente:** voz española TTS (TD-F0-010), STT con voz humana es-MX, bench bajo concurrencia.

## 4. Decisión go/no-go

**Estado: PENDIENTE DE EJECUCIÓN.** La decisión final se registrará aquí con firma de las
personas responsables (sección 5). Si algún criterio §13.2 falla y no hay plan B §13.3:
**no-go**, y el backlog de fases 1+ queda bloqueado.

## 5. Firmas

| Rol | Nombre | Decisión | Fecha |
|---|---|---|---|
| Desarrollo | | | |
| Producto | | | |
