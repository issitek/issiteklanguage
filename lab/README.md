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
| 9081 | STT bench (own container `talkdrill-lab-stt`, no port published) | en uso |
| 9082 | Kokoro TTS EN (`talkdrill-lab-tts`, servicio compose) | en uso |
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
| TD-F0-010 (TTS ES) | Voz española: Kokoro ES o Qwen3-TTS 0.6B; bench pendiente |
| Voz humana es-MX | STT con grabación humana real (este bench usa espeak-ng de VozNativa) |
| TD-F0-011…013, 018 | Loop E2E completo, barge-in real, costo por minuto |

### STT/TTS ya ejecutados (2026-11-16)

```bash
# TTS Kokoro EN (contenedor talkdrill-lab-tts, 127.0.0.1:9082)
docker run -d --name talkdrill-lab-tts -p 127.0.0.1:9082:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest
# → generó lab/data/s01…s10.wav + manifest.json (Kokoro af_heart, 24 kHz mono) en 0.56 s/utterance

# STT faster-whisper small CPU int8 (imagen propia)
docker build -t talkdrill-lab-stt lab/stt
docker run --rm -v "$PWD/lab/data:/data:ro" talkdrill-lab-stt --dir /data --manifest /data/manifest.json
# → WER 0.000 (10/10), ~2.2 s por frase
docker run --rm -v /home/dev/share/VozNativa/scratch:/es:ro talkdrill-lab-stt --file /es/bench-es.wav --lang es
# → smoke test es-419: 1 palabra confundida (Ahora→Hola)
# Nota: faster-whisper (CT2 CUDA 12) no soporta Pascal/P100 → STT solo CPU en este host.
```

## Regla de seguridad del laboratorio

- `.env.lab` nunca se commitea (está en `.gitignore`).
- `coturn` usa secreto propio (`talkdrill-lab`), distinto al de cualquier otro proyecto.
- El relay de STUN/TURN se prueba solo en red propia/laboratorio.

## Fase 0b — PoC OpenPronounce (pronunciación)

```bash
# Construir la imagen aislada (CPU, nada toca la P100 ni Qwen/LFM)
cd /home/dev/share/issitekLanguage/lab
docker compose --env-file .env.lab --profile poc build pronunciation
# Humo (Kokoro af_heart como referencia; es humo técnico, no evidencia es-MX)
docker compose --env-file .env.lab --profile poc run --rm pronunciation \
  smoke/smoke-think.wav "I think this is the right thing." --json --no-prosody
```
Guion y consentimiento para grabarse con voluntarios:
`docs/fase0/guion-pronunciacion.md` · audios en `lab/data/pronunciation/` (fuera de git).
Calibrado es-MX (P3) y decisión (P4): faltan las grabaciones.
