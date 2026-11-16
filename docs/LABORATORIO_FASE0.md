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
| Modelo | STT es-MX base/small (faster-whisper) | ⬜ pendiente (TD-F0-006) | |
| Modelo | STT CPU fallback | ⬜ pendiente (TD-F0-007) | |
| Modelo | LLM Qwen3.5-4B — calidad pedagógica (set prompts §fase0) | 🟡 bench TTFT/tok/s ejecutado (PASS); set 30 prompts pendiente | `lab/bench_llm.py`, §3.2 |
| Red | coturn lab Allocate + relay HMAC (automatizado) | ✅ PASS (2026-11-16) | §3.1 |
| E2E | aiortc echo + DataChannel (automatizado) | ✅ PASS (2026-11-16) | §3.3 |
| Modelo | TTS EN Kokoro 82M | ⬜ pendiente (TD-F0-009) | |
| Modelo | TTS ES (Kokoro ES o Qwen3-TTS 0.6B) | ⬜ pendiente (TD-F0-010) | |
| E2E | Loop WebRTC→STT→LLM→TTS→RTP→visemes (Chrome escritorio) | ⬜ pendiente (TD-F0-011…012) | |
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
4. Evaluación formal del set de 30 prompts (precisión pedagógica) pendiente — requiere el loop E2E (TD-F0-008 completo).

GPU LLM (lab): ~3.3 GB VRAM (Q4_K_M). Con VAD+Whisper+TTS caben en los 16 GB de la P100.

### 3.3 E2E echo aiortc (TD-F0-003/004) — ✅ PASS (2026-11-16 UTC)

`docker compose --env-file .env.lab exec -T -e LAB_TOKEN=… -e LAB_SERVER_URL=http://lab-server:9090 lab-server python /app/tests/test_echo_e2e.py`

```
{"connectionState": "connected", "audio_frames_recibidos": 22,
 "tipos_datachannel": ["listening_state", "assistant_response"], "pass": true}
```

- WebRTC navegador ↔ aiortc ↔ navegador vía el mismo PC (echo): audio de vuelta recibido en ~1 s.
- DataChannel `events` entrega `listening_state` y `assistant_response` (visemas incluidos) → página `http://127.0.0.1:9090/` lista para TD-F0-004 manual (Chrome escritorio) y para el guion de Fase 0 en Android/iPhone.
- Pendiente en este entorno: prueba manual Chrome, Android real, iPhone real, relay forzado, reconexión, barge-in real, STT/TTS bench.

### 3.4 STT / TTS
- Pendiente (ver `lab/README.md`, comandos preparados; no se descargan modelos hasta decidir).

## 4. Decisión go/no-go

**Estado: PENDIENTE DE EJECUCIÓN.** La decisión final se registrará aquí con firma de las
personas responsables (sección 5). Si algún criterio §13.2 falla y no hay plan B §13.3:
**no-go**, y el backlog de fases 1+ queda bloqueado.

## 5. Firmas

| Rol | Nombre | Decisión | Fecha |
|---|---|---|---|
| Desarrollo | | | |
| Producto | | | |
