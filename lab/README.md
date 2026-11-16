# Lab talkdrill — Fase 0 (laboratorio de validación)

Demuestra, con evidencia, el ciclo **WebRTC → STT → LLM → TTS → RTP de regreso → visemas**
antes de construir el producto. Nada de esto toca el entorno Fedora, los juegos,
los contenedores Qwen/LFM existentes ni drivers NVIDIA: todo vive en contenedores
propios (`talkdrill-lab-*`), puertos locales documentados abajo.

## Puertos reservados (solo 127.0.0.1)

| Puerto | Uso | Estado |
|---|---|---|
| 3478, 49152–49200 | coturn laboratorio (STUN/TURN REST-only) | ✅ configurado |
| 9080 | llama-server (Qwen3.5-4B Q4_K_M, P100) | ✅ configurado |
| 9081 | faster-whisper bench (pendiente TD-F0-006) | reservado |
| 9082 | Kokoro / Qwen3-TTS bench (pendiente TD-F0-009/010) | reservado |
| 9090 | lab-server (aiortc: echo + DataChannel + TURN creds) | ✅ configurado |
| 5060/8080/7000/… | **NO usar** (ocupados por proyectos existentes) | — |

## Arranque

```bash
cd /home/dev/share/issitekLanguage/lab
cp .env.lab.example .env.lab
# editar .env.lab: LAB_TOKEN y TURN_SHARED_SECRET largos y aleatorios
docker compose --env-file .env.lab up -d coturn llm lab-server
docker compose --env-file .env.lab ps
curl -s http://127.0.0.1:9090/health
```

## Verificación rápida (sin dispositivos)

```bash
# 1) Telemetría coturn: Allocate con credencial HMAC (usa el contenedor coturn)
#    (la credencial la genera el lab-server: POST /ice-credentials)
curl -s -X POST -H "x-lab-token: $LAB_TOKEN" http://127.0.0.1:9090/ice-credentials

# 2) LLM bench (TD-F0-008)
python3 bench_llm.py --url http://127.0.0.1:9080/v1 --model qwen3.5-4b

# 3) E2E echo automatizado (TD-F0-003/004): aiortc→aiortc, RTP + DataChannel
source .env.lab   # exporta LAB_TOKEN
docker compose --env-file .env.lab exec -T lab-server python /app/tests/test_echo_e2e.py
```

## Prueba manual (navegador, mismo PC)

`http://127.0.0.1:9090/` → pega el `LAB_TOKEN` → **Conectar** → oye tu voz devuelta,
en el canvas «Avatar de prueba» se anima la boca según visemas; botón
**Reportar ICE (getStats)** guarda candidateType/RTT en el lab-server
(`GET /webrtc/ice-report/recent`).

## Pendiente en este entorno (requiere acción humana/dispositivo)

| Item | Qué falta |
|---|---|
| TD-F0-014 (Android real) | Instalar la página de prueba en Android físico (LAN o túnel) y ejecutar guion |
| TD-F0-015 (iPhone real) | Idem en iPhone; si WKWebView falla → documentar plan B (plugin Capacitor WebRTC) |
| TD-F0-016 (NAT restrictivo) | Probar con datos móviles/forzar relay; necesita red externa |
| TD-F0-017 (reconexión) | Guion manual de corte de red 10 s/60 s en navegador |
| TD-F0-006/007 (STT) | faster-whisper bench (descarga ~460 MB modelo); comando abajo |
| TD-F0-009/010 (TTS) | Kokoro 82M EN / ES y Qwen3-TTS; descarga de modelos; comando abajo |
| TD-F0-011…013, 018 | Loop E2E completo, barge-in real, costo por minuto |

### Comandos preparados para STT/TTS (cuando se decida descargar modelos)

```bash
# faster-whisper server (CPU) — test rápido con un WAV propio:
docker run --rm -v "$PWD/data:/data" ghcr.io/speaches-ai/speaches:latest-cpu   # OpenAI-compatible /v1/audio/transcriptions
# Kokoro (CPU vale para el bench):
docker run --rm -p 127.0.0.1:9082:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
```
(Los flags/imágenes se confirman en el momento del bench; no se ejecutan hasta entonces.)

## Regla de seguridad del laboratorio

- `.env.lab` nunca se commitea (está en `.gitignore`).
- `coturn` usa secreto propio (`talkdrill-lab`), distinto al de cualquier otro proyecto.
- El relay de STUN/TURN se prueba solo en red propia/laboratorio.
