# Issitek Language (talkdrill.com) — Documento Maestro de Desarrollo

**Plataforma SaaS de aprendizaje de inglés para México** · Web + Android + iOS · IA híbrida

| Campo | Valor |
|---|---|
| Producto | **Issitek Language** (dominio comercial **talkdrill.com**) |
| Versión | 1.1 |
| Fecha | 2026-11-21 |
| Estado | Aprobado para desarrollo — Fase 0 (voz) cerrada; Fase 0b (evaluador fonético) en investigación paralela, **no bloqueante** |
| Repositorio | `/home/dev/share/issitekLanguage` (repositorio git independiente) |
| Idioma | Español (México) |
| Audiencia | Equipo de desarrollo, diseño, QA y producto |

> **Regla de ingeniería número 1 (v1.1).** Hay dos pistas distintas y no deben
> confundirse:
>
> 1. **Voz conversacional** (WebRTC → STT → LLM → TTS → RTP → visemas): validada
>    en laboratorio (`docs/LABORATORIO_FASE0.md`). Es el diferenciador y **sí**
>    es bloqueante.
> 2. **Evaluación fonética** (¿pronunció bien?): **no** es prerrequisito para
>    construir el producto. Se ejecuta como investigación paralela (Fase 0b,
>    §13.5) y solo se habilita cuando supera su gate de validación.
>
> Mientras el gate no esté aprobado, el alumno puede **escuchar, grabar,
> repetir y autocomparar**, pero **no se le muestra un puntaje**.

---

## 1. Visión del producto

**Issitek Language** (dominio comercial **talkdrill.com**) es una plataforma SaaS educativa cuyo diferenciador es un
**profesor virtual 3D que conversa por voz con estudiantes mexicanos**, entiende
sus errores y adapta las clases a su nivel de inglés.

No es un chatbot con una interfaz educativa alrededor. Es un **sistema de
aprendizaje con cuatro motores independientes**:

| Motor | Responsabilidad |
|---|---|
| **Motor pedagógico** | Qué enseñar y cómo evaluar. Controla ritmo, contenido, dificultad y tipo/momento de corrección. No depende del LLM. |
| **Motor conversacional** | Comprende al alumno y genera respuestas (vía AI Router). |
| **Motor de voz** | Escucha (VAD + STT), reconoce, genera (TTS) y reproduce audio. |
| **Motor visual** | Anima al profesor 3D y sincroniza labios con la voz (visemes por DataChannel). |

La característica central: el profesor **enseña inglés usando español mexicano
cuando es necesario, y aumenta progresivamente el porcentaje de inglés** conforme
mejora el estudiante.

Flujo de experiencia:

1. El alumno entra y selecciona su nivel (o realiza la evaluación de nivel).
2. Elige un profesor virtual.
3. Inicia una conversación hablada.
4. El profesor escucha y responde con voz.
5. Si el alumno comete un error, lo corrige sin interrumpir excesivamente la conversación.
6. Puede escuchar la frase correcta, repetirla y recibir evaluación.
7. La plataforma registra los errores y adapta las siguientes actividades.

---

## 2. Decisiones de arquitectura (ADRs)

### ADR-001 — WebRTC-first desde el día 1

**Decisión:** el transporte de audio alumno ↔ profesor IA es **WebRTC**
(Opus sobre DTLS-SRTP) desde la primera versión funcional, no WebSocket con
payloads de audio.

**Contexto:** la experiencia central es una conversación hablada en tiempo
real con barge-in (el alumno interrumpe al profesor), reproducción progresiva
del TTS y sincronización labial < 100 ms. WebSocket con audio en base64 o
chunks no ofrece QoS, control de congestión, ni renegociación — y obligaría a
un rediseño completo después.

**Reemplaza:** la decisión original "Audio en tiempo real: WebSocket
inicialmente, WebRTC como evolución".

**Consecuencias:**
- (+) Latencia y eficiencia de medio reales (Opus, NACK, congestión, jitter buffer).
- (+) Barge-in e interrupciones naturales sobre el mismo stream bidireccional.
- (+) Telemetría de conexión (`candidateType`, RTT, bytes) integrada al protocolo.
- (−) Complejidad inicial: ICE/NAT/TURN, codecs, buffers, ciclo de vida de sesión.
- (−) WKWebView (iOS) requiere validación explícita en dispositivo real (ver Fase 0 y Riesgos).

**Alternativas evaluadas y descartadas:** WebSocket + audio chunked (baseline
original, descartado por calidad de experiencia); grabación + subida HTTP
(solo para ejercicios puntuales como evaluación de pronunciación, no para conversación).

### ADR-002 — aiortc propio en el Voice Service; sin SFU en el MVP

**Decisión:** la peer connection del lado servidor la sostiene un servicio
Python con **aiortc** (FastAPI alrededor). **No se incorpora un SFU** (LiveKit,
mediasoup) en el MVP.

**Comparación:**

| Criterio | aiortc | LiveKit | mediasoup |
|---|---|---|---|
| Personalización | Excelente | Alta | Excelente |
| Complejidad inicial | Media-alta | Baja-media | Alta |
| Control del audio | Total | Alto | Total |
| SFU integrado | No | Sí | Sí |
| Barge-in personalizado | Sí | Sí | Sí |
| Integración Python | Nativa | Agentes y SDK | Principalmente Node.js |
| Dependencias operativas | Moderadas | Mayores | Mayores |
| Conversación 1:1 | Excelente | Excelente | Excelente |

**Por qué no LiveKit inicialmente:** su framework de agentes es atractiva para
avanzar rápido, pero introduce un framework adicional que no necesitamos para
una conexión 1:1 sencilla, y añade operación y monitoreo de una pieza más.

**Por qué no mediasoup:** excelente para infraestructura multimedia avanzada,
pero más trabajo de integración y mantenimiento. Se consideraría si después
hay clases grupales, distribución de audio/video a muchos participantes.

**Una peer connection por alumno.** Se medirá cuántas conexiones soporta una
instancia del Voice Service; la escala horizontal será por instancias con
enrutamiento de sesión vía Redis. **Regla:** incorporar un SFU solo cuando
existan clases grupales o del orden de >50 conexiones por alumno-profesor por sala.

**Deuda conocida (aceptada):** aiortc no es un framework de agentes
conversacionales. El ciclo de vida de sesión, buffers, cancelación de
tareas (LLM/TTS en curso), recuperación ante desconexiones y limpieza de
recursos **se implementan y prueban deliberadamente**; son parte central del producto.

### ADR-003 — coturn REST-only con HMAC y credenciales temporales

**Decisión:** TURN propio self-hosted con **coturn**, modo **REST-only
(`use-auth-secret`)**, credenciales de vida corta generadas por la API con
HMAC-SHA1 (patrón validado en `mxerp`).

- Separador REST: **`_`** (compatible con Asterisk y coturn; evita el problema
  del `:` en usernames). Username: `<unix_ts>_<nombre>`; password/credential:
  `HMAC_SHA1(secret, username)` en base64.
- La API cuaja credenciales cortas para el navegador/app (igual que
  `app/telephony/webrtc_ice.py` en `mxerp`: `turn_hmac_credential()` +
  `build_ice_servers()`).
- coturn **no es obligatorio** para todo el tráfico: ICE elige host/srflx (P2P)
  o relay (coturn) sin intervención del alumno. Es la ruta de transporte
  alternativa, no un "piso" lógico de la arquitectura.
- coturn corre en la misma red Docker que la app (o en el VPS público) con
  `network_mode: host` en desarrollo; en producción, exponiendo solo lo necesario.
- Telemetría ICE estilo mxerp: el cliente reporta `candidateType`
  (host/srflx/relay), RTT y bytes a `POST /api/v1/webrtc/ice-report`.

### ADR-004 — Señalización HTTPS + WS trickle; DataChannel para eventos

**Decisión:**
- **Señalización SDP/ICE inicial:** HTTPS. `POST .../webrtc/offer` → la API devuelve el answer (o `POST .../webrtc/answer` en flujo inverso).
- **ICE trickle:** WebSocket `WS .../signaling` (JSON: `{"type":"ice","candidate":...}`, `{"type":"end_of_candidates"}`). HTTP `POST .../webrtc/ice` queda como alternativa.
- **Eventos de conversación y visemas:** **RTCDataChannel** `events` (reliable, ordered) sobre la misma peer connection.
- El DataChannel **no puede sustituir la señalización**: requiere que la
  conexión ya esté establecida. La señalización inicial siempre va por HTTPS/WS.
- Sin audio en DataChannel: el audio viaja por RTP. El DataChannel es para
  JSON pedagógico/control (correcciones, traducciones, emociones, visemas,
  confirmación de barge-in, métricas de sesión).

### ADR-005 — Avatar renderizado en el dispositivo del alumno

**Decisión:** Three.js + formato VRM en cliente; **no se genera video** por
respuesta. El modelo VRM se descarga una vez y se cachea (Cache Storage /
assets de la app). El servidor envía **visemas y emociones** por DataChannel;
three.js los reproduce sincronizados con el audio RTP (lip-sync < 100 ms).

**Consecuencia:** costo marginal de cómputo de avatar ≈ 0 en servidor; GPU del
cliente hace el render. Permite múltiples profesores sin costo por minuto de video.

### ADR-006 — AI Router con modelos intercambiables

**Decisión:** la aplicación **nunca habla directamente con un proveedor**.
Todo pasa por el **AI Router**, que selecciona el modelo por tarea, latencia,
costo y disponibilidad, con *fallback ladder*: local → externa → error
pedagógico amigable. El formato de salida es el mismo (JSON pedagógico)
independientemente del modelo. Consumo registrado en `ai_usage` por usuario,
tarea y modelo.

**Modelos iniciales a evaluar (no entrenar modelos propios):**

| Función | Primera opción | Alternativa |
|---|---|---|
| Cerebro conversacional | Qwen3.5 4B cuantizado (P100, llama.cpp, API compatible OpenAI) — **thinking desactivado en conversación** | API externa |
| Conversación avanzada | API externa | Qwen local |
| Reconocimiento de voz | faster-whisper / whisper.cpp base-small | API STT externa |
| Voz inglesa | Kokoro 82M | Qwen3-TTS 0.6B |
| Voz española | Kokoro español (sujeto a pruebas) | Qwen3-TTS 0.6B |
| Evaluación de pronunciación | Pipeline fonético especializado (MFA + métricas acústicas) | Evaluación externa |

### ADR-007 — Repositorio independiente `issitekLanguage`

**Decisión:** git repo propio en `/home/dev/share/issitekLanguage`
(`git init -b main`). **No se versiona nada dentro del monorepo padre**
`/home/dev/share` ni se modifica ninguno de sus archivos, proyectos,
contenedores o configuraciones.

### ADR-008 — Laboratorio P100 aislado

**Decisión:** la Tesla P100 de 16 GB se usa **como laboratorio de inferencia**,
no como servidor de producción multiusuario. Todo el laboratorio vive en
**contenedores Docker aislados** (red dedicada, volúmenes propios), sin tocar:
- Drivers NVIDIA, kernel, configuración gráfica, sesión de Fedora.
- Contenedores Qwen/LFM existentes (`Qwen36-35B-A3B`, `LFM25-24B-A2B`, `strata-p100-deploy`, `llamaCppP100`).
- Juegos ni otros proyectos.

Se medirá latencia, RTF, concurrencia y memoria **antes** de cualquier
decisión de capacidad. Si el laboratorio es viable, la P100 alimenta el MVP
interno; la producción externa requiere dimensionamiento propio (ver Riesgos).

### ADR-009 — WebRTC también para evaluación puntual por audio

La evaluación de pronunciación de frases en contextos no conversacionales
(p. ej. "repite esta frase") usará WebRTC cuando la sesión ya esté viva, y
subida HTTP (grabación puntual → `POST /pronunciation/evaluate`) cuando no.
El camino HTTP es **auxiliar**, nunca el transporte de la conversación.

### ADR-010 — Privacidad por diseño desde el día 1

Consentimiento explícito para grabar voz, retención configurable y eliminación
de grabaciones, controles de acceso a `speech_assets`, y diseño para menores
(consentimiento parental, minimización de datos). Ver §16. En México aplica la
**LFPDPPP**; el aviso de privacidad se publicará antes del piloto.

### ADR-011 — Evaluador de pronunciación desacoplado (puerto/adaptador)

El evaluador fonético se define como **puerto** (`PronunciationEvaluator`) con un
**resultado normalizado versionado**; OpenPronounce, Azure Speech, Speechace,
ELSA y GOP local son **adaptadores** intercambiables. Hay tres capas separadas:

1. **Evaluador**: analiza el audio y devuelve evidencia acústica.
2. **Motor pedagógico**: decide si corrige, cuándo y cómo.
3. **Interfaz**: presenta solo la retroalimentación autorizada.

Cambiar de motor no toca lecciones, esquema educativo ni UI. Contrato en
`docs/fase1/contrato-evaluador.md`.

### ADR-012 — Fase 0b no bloqueante (investigación paralela)

La validación del evaluador fonético deja de ser prerrequisito de Fase 1. Corre
como investigación paralela con un **gate de adopción** (§13.5). Hasta aprobarlo,
`PRONUNCIATION_EVAL_ENABLED=false`: el alumno escucha, graba, repite y se
autocompara, sin puntaje. Regla de producto: **un score con
`reliability != validated` no se presenta como evaluación objetiva.**

### ADR-013 — Puntuación educativa y fonética separadas

`exercise_attempts.score` mide el desempeño del ejercicio educativo y alimenta
las reglas de avance y el progreso académico. La evidencia fonética vive **solo**
en `pronunciation_attempts`. Una evaluación experimental nunca altera el progreso
académico del alumno.

### ADR-014 — Grabación de ejercicios asíncrona (MediaRecorder), WebRTC solo conversación

La práctica de pronunciación de ejercicios usa `MediaRecorder` + subida firmada a
almacenamiento S3-compatible (`POST /recordings/presign` → `PUT` → `POST /recordings/{id}/complete`).
WebRTC se reserva **exclusivamente** para la conversación en tiempo real (ADR-001,
ADR-009). Esto abarata el ejercicio, permite reintentos y desacopla la práctica
del ciclo de vida de una sesión WebRTC.

---

## 3. Arquitectura general

```
                        WebRTC-first
  Alumno                                        Servidor
  ┌─────────────────────┐        Opus/DTLS-SRTP  ┌──────────────────────────────┐
  │ Vue 3 + Vite + TS   │ ══════════════════════ │  FastAPI + aiortc             │
  │ Three.js + VRM      │   1 RTCPeerConnection  │  Voice Service (1 PC/alumno)  │
  │ Capacitor 8         │   audio bidireccional  │                              │
  │ (Android / iOS)     │                        │  ┌─ VAD (silero/energía)      │
  │                     │   HTTPS/WSS            │  ├─ STT (faster-whisper)     │
  │  ┌───────────────┐  │ ═════════════════════► │  ├─ Orquestador conversación │
  │  │ DataChannel   │  │   señalización SDP/ICE │  ├─ AI Router ────────────┐  │
  │  │ events        │◄─┼────────────────────────┤  ├─ TTS (Kokoro/Qwen3)    │  │
  │  │ correcciones, │  │   visemes, corrección, │  └─ RTP de regreso        │  │
  │  │ visemes...    │  │   emoción, interrupt   │                          │  │
  │  └───────────────┘  │                        └───────┬──────────────────┘  │
  └─────────────────────┘                                │                     │
            │                                             ▼                     │
            │                                   AI Core (AI Router)
            │                                   ┌──────────────────────────┐  │
            │             API Gateway FastAPI   │ IA local (P100 lab):     │  │
            │             REST + WS ICE trickle │ Qwen3.5-4B / faster-     │  │
            │             JWT · rate limit      │ whisper / Kokoro         │  │
            ▼                                   ├──────────────────────────┤  │
  Web · Android · iOS                           │ IA externa (respaldo):   │  │
                                                 │ conversaciones complejas, │  │
                                                 │ explicaciones avanzadas  │  │
                                                 └──────────────────────────┘  │

  Infraestructura: PostgreSQL · Redis · S3-compatible (audio) · coturn (TURN relay) · Docker Compose
```

### 3.1 Clientes

| Capa | Tecnología | Notas |
|---|---|---|
| Web | Vue 3 + Vite + TypeScript | SPA; PWA opcional |
| Android | Capacitor 8 | WebView moderno con WebRTC; permisos mic nativos |
| iOS | Capacitor 8 | WKWebView; requiere validación en dispositivo (Fase 0) |
| Avatar | Three.js + VRM | Render en cliente; visemas por DataChannel |
| Audio | Web Audio API + RTCPeerConnection | Captura 48 kHz, downsample 16 kHz mono para STT |

Capacitor permite llevar la app web a Android, iOS y web con una sola base de
código, conservando acceso a capacidades nativas (micrófono, audífonos,
interrupciones telefónicas, segundo plano) mediante interfaces por plataforma.

### 3.2 API Gateway (FastAPI)

- JWT (access + refresh), rate limiting, CORS estricto, request-id, logging estructurado.
- Sirve: REST de todos los dominios + **señalización WebRTC** (HTTPS + WS para ICE trickle).
- No procesa audio: delega la peer connection al **Voice Service** (mismo proceso
  en desarrollo; servicio separado en producción).
- La sesión WebRTC queda anclada a `conversation_sessions.id`.

### 3.3 Voice Service (aiortc)

Responsabilidades del proceso:

1. Recibir `RTCPeerConnection` (una por sesión; sticky vía Redis + instancia).
2. Decodificar Opus → PCM 16 kHz mono → VAD → segmentación por turnos.
3. `faster-whisper` (o whisper.cpp) con confianza por hipótesis; pasar texto + confianza a la pipeline.
4. Llamar al **AI Router** con el contexto pedagógico (nivel, objetivo, debilidades, historial reciente).
5. Recibir respuesta estructurada (texto, corrección, traducción, emoción, visemas) y sintetizar con **TTS** (chunked/streaming de ser posible).
6. Enviar audio por RTP de regreso; enviar visemas/emociones por **DataChannel** `events`.
7. **Barge-in:** si el VAD detecta voz del alumno mientras el profesor habla → cancelar síntesis TTS en curso, flush de buffers RTP, notificar al cliente (`{"type":"interrupt"}`) y descartar el turno restante.
8. **Turn detection:** silencio sostenido (VAD) + heurística de intención (¿frase completa?) para decidir fin de turno; no depender solo de pausas fijas.
9. **Telemetría:** candidateType, RTT, jitter, bytes, tiempos de cada etapa (STT, LLM, TTS) a `ice_telemetry` y a logs.

### 3.4 Topología WebRTC (detalle)

```
Navegador/App                                    Voice Service
─────────────                                    ─────────────
getUserMedia({audio})                            aiortc RTCPeerConnection
RTCPeerConnection ────── offer (HTTPS) ──────►   setRemoteDescription(offer)
                        ◄───── answer ─────────  createAnswer()
                        ◄───►  ICE candidates (WS trickle)
RTCDataChannel("events") ═══════════════════►    canal de eventos (JSON)
MediaStreamTrack(audio)  ══ RTP/Opus ════════►   VAD → Whisper → ...
                          ◄══ RTP/Opus ══════   audio TTS del profesor
```

- **STUN:** en desarrollo, STUN público o coturn en modo STUN.
- **TURN:** coturn propio con credenciales HMAC temporales (§ADR-003).
  ICE usará relay solo si no hay ruta directa (restrictivo/simétrico).
- **Codec:** Opus (obligatorio WebRTC); DTLS-SRTP obligatorio (no existe modo sin cifrar).
- **Sin SFU:** 1:1 directo navegador↔servicio. Escalado = más instancias + enrutador de sesión por Redis.
- **Caída de conexión:** el cliente reintenta con backoff (hasta 3 intentos)
  re-creando offer; la sesión se reanuda con el historial persistido en
  `conversation_messages` (el profesor "recuerda" aunque caiga el transporte).

### 3.5 Datos e infraestructura

PostgreSQL (sistema de verdad) · Redis (sesiones, enrutado, rate limit, caché,
repetición espaciada en cola) · S3-compatible (audios, modelos VRM,
assets) · coturn (TURN/STUN) · Docker Compose (MVP) · Nginx (TLS, proxy).

Separación de servidores:

| Servidor | Contenido |
|---|---|
| App | nginx · web · api · voice · worker · postgres · redis · minio · coturn |
| IA (laboratorio P100) | LLM local (llama.cpp/Qwen) · faster-whisper · Kokoro/Qwen3-TTS · AI Router |
| Externos | API IA de respaldo · Mercado Pago / Stripe · correo · monitoreo |

---

## 4. Estructura del repositorio

```
issitekLanguage/
├─ apps/
│  └─ web/                  # Vue 3 + Vite + TS (única base para web y Capacitor)
│     ├─ src/
│     │  ├─ avatar/         # Three.js + VRM, visemas, expresiones, gestos
│     │  ├─ webrtc/         # RTCPeerConnection, señalización, DataChannel, VAD cliente
│     │  ├─ audio/          # captura, worklet, reproducción, interrupciones
│     │  ├─ views/ · stores/ · router/ · services/
│     ├─ android/ · ios/    # proyectos Capacitor (generados)
│     └─ capacitor.config.ts
├─ services/
│  ├─ api/                  # FastAPI: REST, auth, señalización, negocio (cursos/progreso/suscripciones)
│  ├─ voice/                # FastAPI + aiortc: peer connection, VAD, STT, TTS, AI Router client
│  └─ worker/               # tareas: webhooks pagos, recordatorios, retención audio, digests
├─ packages/
│  └─ shared/               # contratos: JSON Schema de eventos DataChannel, tipos TS, OpenAPI snapshot
├─ infra/
│  ├─ docker-compose.yml    # desarrollo all-in-one (postgres, redis, minio, coturn, nginx)
│  ├─ docker-compose.prod.yml
│  ├─ nginx/
│  └─ .env.example
└─ docs/
   ├─ DOCUMENTO_MAESTRO.md  # este archivo
   ├─ BACKLOG.md
   ├─ LABORATORIO_FASE0.md  # (se crea al ejecutar Fase 0)
   └─ adr/                  # ADRs detallados si crecen
```

Decisión de tooling: monorepo simple **sin** Nx/Turborepo en el MVP;
`pnpm workspaces` para JS/TS y `uv` (o rye) para Python. Un solo repo
versionado (independiente del monorepo padre).

---

## 5. Contratos API

Prefijo global: `/api/v1`. Autenticación: `Authorization: Bearer <access_jwt>`.
Respuestas de error: `{"error": {"code", "message", "request_id"}}`.

### 5.1 REST por dominios

| Módulo | Endpoints principales |
|---|---|
| Auth | `POST /auth/register` · `POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` |
| Perfil | `GET /users/me` · `PATCH /users/me` |
| Cursos | `GET /courses` · `GET /courses/{id}` · `GET /lessons/{id}` · `GET /lessons/{id}/exercises` · `POST /lessons/{id}/complete` |
| Progreso | `GET /progress` · `GET /statistics` |
| Evaluación de nivel | `POST /placement/start` · `POST /placement/answer` · `GET /placement/result` |
| Conversación (lifecycle) | `POST /conversation/sessions` · `GET /conversation/sessions` · `GET /conversation/sessions/{id}` · `POST /conversation/sessions/{id}/finish` |
| Señalización WebRTC | `POST /conversation/sessions/{id}/webrtc/offer` · `POST /conversation/sessions/{id}/webrtc/ice` · `WS /conversation/sessions/{id}/signaling` |
| Telemetría ICE | `POST /webrtc/ice-report` · `GET /webrtc/ice-report/recent` (admin) |
| Audio puntual | `POST /speech/transcribe` · `POST /speech/synthesize` (auxiliares; no para conversación) |
| Pronunciación | `POST /pronunciation/evaluate` · `GET /pronunciation/attempts/{id}` · `GET /pronunciation/attempts` |
| Grabaciones | `POST /recordings/presign` · `POST /recordings/{id}/complete` · `GET /recordings/{id}` · `DELETE /recordings/{id}` |
| Intentos de ejercicio | `POST /exercises/{id}/attempts` · `GET /exercises/{id}/attempts` · `GET /me/history` |
| Audio de referencia (TTS) | `GET /tts/reference?text=&voice_id=` (con caché) · `GET /tts/voices` |
| Consentimientos | `GET /consents` · `POST /consents` · `DELETE /consents/{kind}` |
| IA (debug/admin) | `POST /ai/chat` (uso interno) · `GET /ai/models` · `GET /ai/usage` (admin) |
| Suscripciones | `GET /subscriptions/plans` · `POST /subscriptions/subscribe` · `POST /subscriptions/cancel` · `POST /billing/webhook/mercadopago` · `POST /billing/webhook/stripe` |
| Admin | `GET /admin/users` · `GET /admin/analytics` · `GET /admin/sessions/{id}` (trazabilidad de conversación) · `GET/POST/PATCH /admin/{courses,lessons,exercises}` · `GET /admin/students` · `GET /admin/students/{id}/progress` |

### 5.2 Señalización WebRTC (detalle)

Flujo nominal (el cliente crea el offer porque quiere recibir audio + datachannel):

1. `POST /conversation/sessions/{id}/webrtc/offer`
   ```json
   { "sdp": "v=0 o=- ...", "type": "offer",
     "ice_servers": { "use": true } }
   ```
   Respuesta `200`:
   ```json
   { "sdp": "v=0 o=- ...", "type": "answer",
     "ice_servers": [
       {"urls": ["stun:stun.example.com:3478"]},
       {"urls": ["turn:turn.example.com:3478?transport=udp"], "username": "1731763200_talkdrill_u123", "credential": "base64(hmac…)"}
     ] }
   ```
   Las `ice_servers` las cuaja la API con HMAC de vida corta (TTL ≤ 5 min,
   separador `_`); el cliente las pasa a `RTCPeerConnection({iceServers})`.

2. ICE trickle por WS (`/signaling`), mensajes JSON:
   ```json
   {"type":"ice","candidate":"candidate:842163049 1 udp 1677729535 …","sdpMid":"0","sdpMLineIndex":0}
   {"type":"end_of_candidates"}
   {"type":"bye","reason":"user_left"}
   ```

3. DataChannel `events`: abierto por el cliente en el offer
   (`negotiated: false`, ordenado, reliable). El servidor lo acepta en `on_datachannel`.

### 5.3 Eventos del DataChannel `events`

Todos los mensajes son JSON con `{"type": ..., "v": 1, "session_id": "...", "ts": "<iso8601>"}`.

**Profesor → Alumno:**

```json
{
  "type": "assistant_response",
  "v": 1,
  "session_id": "sess_123",
  "ts": "2026-11-15T12:00:00Z",
  "text": "Yesterday I went to school.",
  "display_translation": "Ayer fui a la escuela.",
  "correction": {
    "original": "Yesterday I go to the school.",
    "corrected": "Yesterday I went to school.",
    "reason": "Past simple",
    "error_type": "grammar_tense"
  },
  "emotion": "encouraging",
  "visemes": [
    {"t_ms": 0,   "id": "sil", "weight": 0.0},
    {"t_ms": 120, "id": "B",   "weight": 0.9},
    {"t_ms": 240, "id": "AA",  "weight": 1.0}
  ],
  "audio_seq": 42,
  "model": "qwen3.5-4b-instruct-q4"
}
```

| Evento | Dirección | Contenido |
|---|---|---|
| `assistant_response` | S→C | Texto, traducción, corrección opcional, emoción, timeline de visemas, seq de audio |
| `turn_end` | S→C | Fin de turno del profesor (para avatar idle) |
| `interrupt` | S→C | Barge-in confirmado: el cliente corta reproducción/lip-sync |
| `listening_state` | S→C | `listening`/`thinking`/`speaking` para animaciones del avatar |
| `correction_hint` | S→C | Corrección menor sin corte de flujo (tooltip/caption) |
| `error` | S→C | `{code, message}` pedagógico o técnico |

**Alumno → Profesor:**

| Evento | Contenido |
|---|---|
| `client_hello` | Versión de cliente, capacidades (visemas, formatos), locale |
| `interrupt` | Barge-in detectado en cliente (refuerzo del VAD servidor) |
| `caption_ack` | El alumno vio la corrección en pantalla |
| `session_metrics` | RTT observado, bytes, candidateType (si no hay `/ice-report`) |

### 5.4 Notificaciones de conexión (WebSocket auxiliar)

Además del WS de ICE trickle, `WS /conversation/sessions/{id}/events`
(autenticado) notifica ciclo de vida fuera de la peer connection:
`session_started`, `session_finished`, `usage_warning` (minutos restantes del
plan), `plan_limit_reached`. **El audio nunca viaja por este canal.**

---

## 6. Esquema de base de datos (PostgreSQL)

DDL de referencia (resumen; el DDL completo vive en `services/api` migraciones Alembic).

```sql
-- Núcleo de usuarios y monetización
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name     TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'active',   -- active|suspended|deleted
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE subscriptions (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan           TEXT NOT NULL,                    -- free|plus|premium
  status         TEXT NOT NULL,                    -- active|past_due|canceled|trialing
  provider       TEXT,                             -- mercadopago|stripe
  provider_sub_id TEXT,
  current_period_end TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE user_profiles (
  user_id        UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  native_language TEXT NOT NULL DEFAULT 'es-MX',
  learning_goals JSONB NOT NULL DEFAULT '[]',
  interests      JSONB NOT NULL DEFAULT '[]',
  consent_recording BOOLEAN NOT NULL DEFAULT false,
  consent_at     TIMESTAMPTZ,
  birth_year     INT,                              -- para controles de menores
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE student_levels (
  user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course         TEXT NOT NULL DEFAULT 'general',
  cefr_level     TEXT NOT NULL CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, course)
);

-- Catálogo educativo
CREATE TABLE courses (id UUID PRIMARY KEY, cefr_level TEXT NOT NULL, title_es TEXT, title_en TEXT,
                      description JSONB, published BOOLEAN NOT NULL DEFAULT false);
CREATE TABLE lessons (id UUID PRIMARY KEY, course_id UUID NOT NULL REFERENCES courses(id),
                      order_index INT NOT NULL, title_es TEXT, title_en TEXT,
                      objectives JSONB, est_minutes INT, published BOOLEAN NOT NULL DEFAULT false);
CREATE TABLE exercises (id UUID PRIMARY KEY, lesson_id UUID NOT NULL REFERENCES lessons(id),
                        order_index INT NOT NULL, kind TEXT NOT NULL,   -- repeat|choose|translate|speak|listen
                        prompt JSONB NOT NULL, answer_key JSONB, difficulty INT NOT NULL DEFAULT 1);
CREATE TABLE vocabulary (id UUID PRIMARY KEY, cefr_level TEXT NOT NULL, lemma TEXT NOT NULL,
                         pos TEXT, translation_es TEXT NOT NULL, example_en TEXT,
                         audio_asset_id UUID, UNIQUE (cefr_level, lemma, pos));
CREATE TABLE grammar_topics (id UUID PRIMARY KEY, cefr_level TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
                             name_es TEXT NOT NULL, name_en TEXT NOT NULL, explanation JSONB, rules JSONB);

-- Progreso y memoria de aprendizaje
CREATE TABLE student_progress (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lesson_id UUID NOT NULL REFERENCES lessons(id),
  status TEXT NOT NULL DEFAULT 'not_started',     -- not_started|in_progress|completed
  score NUMERIC(5,2), attempts INT NOT NULL DEFAULT 0,
  completed_at TIMESTAMPTZ, PRIMARY KEY (user_id, lesson_id)
);
CREATE TABLE learning_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,                              -- vocab_seen|vocab_mastered|grammar_error|exercise_done|session_end
  ref_type TEXT, ref_id UUID,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON learning_events (user_id, kind, created_at DESC);
CREATE TABLE pronunciation_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expected_text TEXT NOT NULL, hypothesis TEXT,    -- salida STT cruda
  phoneme_errors JSONB, score NUMERIC(5,2),
  audio_asset_id UUID, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sesiones de conversación (WebRTC) y mensajes
CREATE TABLE conversation_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  avatar_id UUID, voice_profile_id UUID,
  level_at_start TEXT NOT NULL,
  ice_policy TEXT NOT NULL DEFAULT 'all',          -- all|relay
  turn_used BOOLEAN, candidate_type TEXT,          -- host|srflx|relay
  rtt_ms INT, jitter_ms INT, bytes_sent BIGINT, bytes_received BIGINT,
  consent_recording BOOLEAN NOT NULL DEFAULT false,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  retention_until TIMESTAMPTZ,                     -- borrado programado de audio
  metrics JSONB NOT NULL DEFAULT '{}'              -- latencias por etapa
);
CREATE INDEX ON conversation_sessions (user_id, started_at DESC);
CREATE TABLE conversation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('student','assistant','system')),
  text TEXT NOT NULL,
  correction JSONB, translation TEXT, emotion TEXT,
  stt_confidence NUMERIC(4,3),                     -- NULL para mensajes del profesor
  audio_asset_id UUID, visemes JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON conversation_messages (session_id, created_at);
CREATE TABLE ice_telemetry (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  candidate_type TEXT, rtt_ms INT, bytes_sent BIGINT, bytes_received BIGINT,
  event TEXT NOT NULL,                              -- connected|relay|disconnected|failed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Assets de audio y catálogo de avatar/voces
CREATE TABLE speech_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,   -- NULL = asset del sistema
  kind TEXT NOT NULL,                               -- tts_reply|student_recording|exercise
  storage_key TEXT NOT NULL,                        -- MinIO/S3 key
  duration_ms INT, sample_rate INT, bytes BIGINT,
  retention_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE avatars (id UUID PRIMARY KEY, name TEXT NOT NULL, vrm_storage_key TEXT NOT NULL,
                      thumbnail_key TEXT, gender TEXT, style TEXT, published BOOLEAN NOT NULL DEFAULT true);
CREATE TABLE voice_profiles (id UUID PRIMARY KEY, provider TEXT NOT NULL,             -- kokoro|qwen3-tts|external
                             voice_id TEXT NOT NULL, locale TEXT NOT NULL DEFAULT 'en-US',
                             display_name TEXT, sample_text TEXT, published BOOLEAN NOT NULL DEFAULT true);

-- IA: consumo y registro de modelos
CREATE TABLE ai_usage (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  session_id UUID REFERENCES conversation_sessions(id) ON DELETE SET NULL,
  task TEXT NOT NULL,                               -- chat|correction|translation|tts|stt|evaluation
  model TEXT NOT NULL,                              -- id lógico en model_registry
  provider TEXT NOT NULL,                           -- local_p100|external_x|...
  tokens_in INT, tokens_out INT, seconds_audio NUMERIC(8,2),
  cost_usd NUMERIC(10,6), latency_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON ai_usage (user_id, created_at DESC);
CREATE INDEX ON ai_usage (model, created_at DESC);
CREATE TABLE model_registry (
  id TEXT PRIMARY KEY,                              -- p.ej. 'qwen3.5-4b-instruct-q4'
  kind TEXT NOT NULL,                               -- llm|stt|tts|aligner
  provider TEXT NOT NULL,                           -- llama.cpp|kokoro|whisper.cpp|external:<vendor>
  endpoint TEXT,                                    -- URL interna (OpenAI-compatible)
  config JSONB NOT NULL DEFAULT '{}',               -- cuantización, temperatura, device
  enabled BOOLEAN NOT NULL DEFAULT true,
  cost_per_1k_tokens_usd NUMERIC(10,6),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== Fase 1 (v1.1): voz, intentos y consentimiento =====
-- Deltas sobre pronunciation_attempts (evaluador desacoplado, ADR-011)
ALTER TABLE pronunciation_attempts
  ADD COLUMN exercise_id UUID REFERENCES exercises(id),
  ADD COLUMN attempt_no INT NOT NULL DEFAULT 1,
  ADD COLUMN evaluator TEXT,                    -- openpronounce|azure|speechace|elsa|gop|fake
  ADD COLUMN engine_version TEXT,
  ADD COLUMN status TEXT NOT NULL DEFAULT 'disabled',  -- disabled|pending|completed|failed
  ADD COLUMN confidence NUMERIC(4,3),
  ADD COLUMN reliability TEXT NOT NULL DEFAULT 'unvalidated', -- validated|experimental|unvalidated
  ADD COLUMN result_json JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN latency_ms INT,
  ADD COLUMN cost_usd NUMERIC(10,6),
  ADD COLUMN audio_sha256 TEXT,
  ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1.0';

-- Deltas sobre speech_assets (separación referencia vs alumno, ADR-014)
ALTER TABLE speech_assets
  ADD COLUMN sha256 TEXT,
  ADD COLUMN source TEXT NOT NULL DEFAULT 'student_recording', -- tts_reference|student_recording|exercise
  ADD COLUMN consent_id UUID,
  ADD COLUMN mime TEXT,
  ADD COLUMN deleted_at TIMESTAMPTZ;

CREATE TABLE consents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,     -- recording | third_party_processing | parental
  version       TEXT NOT NULL,     -- versión del aviso de privacidad aceptado
  granted_at    TIMESTAMPTZ,
  revoked_at    TIMESTAMPTZ,
  evidence      JSONB NOT NULL DEFAULT '{}',  -- ip_hash, user_agent_hash, método
  UNIQUE (user_id, kind, version)
);

CREATE TABLE exercise_attempts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  exercise_id   UUID NOT NULL REFERENCES exercises(id),
  attempt_no    INT NOT NULL DEFAULT 1,
  response      JSONB NOT NULL DEFAULT '{}',
  score         NUMERIC(5,2),      -- puntuación EDUCATIVA (no fonética; ADR-013)
  is_correct    BOOLEAN,
  hints_used    INT NOT NULL DEFAULT 0,
  time_ms       INT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, exercise_id, attempt_no)
);

CREATE TABLE tts_cache (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  text_hash     TEXT NOT NULL,
  voice_id      TEXT NOT NULL,
  locale        TEXT NOT NULL DEFAULT 'en-US',
  storage_key   TEXT NOT NULL,
  duration_ms   INT,
  hit_count     BIGINT NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (text_hash, voice_id)
);
```

Notas:
- `CITEXT` requiere `CREATE EXTENSION citext`. `pgcrypto`/`gen_random_uuid()` vía `pgcrypto` o pg13+.
- Retención: `speech_assets.retention_until` + worker diario; borrado físico en el almacenamiento S3 y NULL en referencias.
- Menores: `user_profiles.birth_year` + flag parental para consentimiento y límites de sesión.
- Estadísticas (`/statistics`) se sirven con vistas materializadas sobre
  `learning_events` y `student_progress` (refresco por worker, no en caliente).
- `exercise_attempts.score` es **educativo**; la evidencia fonética vive en
  `pronunciation_attempts` (ADR-013).
- `speech_assets.source` separa audio de referencia TTS de grabaciones del
  alumno; nunca comparten política de retención (ADR-014).
- El flag `PRONUNCIATION_EVAL_ENABLED` (Apéndice A) mantiene la evaluación
  fonética desactivada hasta que se apruebe el gate §13.5.

---

## 7. Infraestructura y despliegue

### 7.1 Desarrollo (Docker Compose all-in-one)

Servicios actuales de F1: `web` (build Vue + nginx, proxy `/api` y `/s3`) ·
`api` · `postgres` · `redis` · `storage` (S3-compatible de desarrollo).
En fases posteriores se suman `voice`, `worker` y `coturn`.

```yaml
# infra/docker-compose.yml (resumen de servicios, no exhaustivo)
services:
  web:     { build: ../apps/web, ports: ["8090:80"], depends_on: [api, storage] }
  api:     { build: ../services/api, env_file: .env, depends_on: [postgres, redis, storage] }
  postgres:{ image: postgres:16, volumes: ["pgdata:/var/lib/postgresql/data"] }
  redis:   { image: redis:7 }
  storage: { build: ../services/storage-dev }   # moto en desarrollo; producción S3/MinIO/Garage
  # voice / worker / coturn se añaden en F2/F4a
```

- Secretos por `.env` (jamás en git); `.env.example` documenta cada variable.
- **Proyecto Compose independiente:** `COMPOSE_PROJECT_NAME=issitek-language`.
  Contenedores, red y volúmenes llevan ese prefijo (`issitek-api`,
  `issitek_net`, `issitek_pgdata`). En desarrollo no se publican `80/443`;
  `web` escucha en `8090` y el almacenamiento S3 en `9100` para no chocar con
  otros proyectos. Coturn puede reutilizarse con realm `talkdrill`, sin
  compartir secretos.
- **URLs firmadas:** la API firma contra el host interno (`storage:9000`) y
  reescribe al endpoint público (`MINIO_PUBLIC_ENDPOINT`). En desarrollo nginx
  sirve `/s3` en el mismo origen para evitar CORS; en producción se apunta al
  endpoint S3 público.
- Desarrollo funciona en CPU; la P100 se usa vía `--profile gpu` o en el servidor de lab.

### 7.2 Despliegue MVP

| Servidor | Contenido |
|---|---|
| App VPS | nginx · web (build estático) · api · voice (CPU en dev/staging) · worker · postgres · redis · minio · coturn (`3478/udp`, `3478/tcp`, `5349` TURNS, rango relay) |
| Lab IA P100 | faster-whisper · Kokoro/Qwen3-TTS · Qwen3.5-4B (llama.cpp server, API OpenAI-compatible en `:8080`) · expuesto **solo** a la red de confianza (VPN o VPC) |
| Externos | API IA de respaldo · Mercado Pago + Stripe webhooks · correo (SMTP) · monitoreo (Uptime + logs; Prometheus/Grafana opcional) |

### 7.3 Reglas de convivencia con la infraestructura existente

- El proyecto vive en `/home/dev/share/issitekLanguage` con su propio git;
  **no se modifica** el monorepo padre ni sus archivos.
- El laboratorio P100 usa contenedores propios (red `talkdrill`, volúmenes `talkdrill-*`); no se tocan `llamaCppP100`, `strata-p100-deploy`, `Qwen36-35B-A3B`, `LFM25-24B-A2B` ni drivers NVIDIA.
- Puertos: se eligen puertos libres fuera de los usados por proyectos existentes; quedan documentados en `infra/README.md` al ejecutar la Fase 1.
- coturn: se **permite** reutilizar la experiencia de mxerp (config y procedimiento),
  pero la instancia es propia de talkdrill (realm y secreto distintos).

---

## 8. Motor de IA (AI Router)

### 8.1 Enrutamiento por tarea

| Tarea | Ruta preferente | Fallback |
|---|---|---|
| Corrección gramatical en turno | Local (Qwen3.5-4B) | Externa |
| Diálogo/continuación conversacional | Local | Externa |
| Explicación avanzada (B2+) | Externa | Local |
| Ejercicios y traducción contextual | Local | Externa |
| Evaluación de pronunciación | Pipeline fonético (no LLM) | — |
| Resúmenes/estadísticas para alumno | Local | Externa |

### 8.2 Latency ladder y disponibilidad

1. Local sano → local. 2. Local lento/caído (timeout 2.5 s) → externa.
3. Externa caída → respuesta pedagógica genérica offline ("Let's keep going — could you rephrase that?") + evento `error` con código; la conversación nunca muere por el LLM.

### 8.3 Contrato de salida estructurada (independiente del modelo)

```json
{
  "reply_text": "…",
  "translation_es": "…",
  "correction": {"original":"…","corrected":"…","error_type":"grammar_tense|pronunciation|vocabulary|comprehension|stt_attributable","reason":"…"} | null,
  "emotion": "neutral|encouraging|surprised|confused|approving|playful",
  "visemes": [ … ],            // opcional: si el proveedor TTS los da; si no, se derivan del texto+SSML
  "level_hint": "A2",
  "tool_calls": []              // futuro: ejercicios dinámicos, lookup de vocabulario
}
```

El router **normaliza** esta salida antes de emitirla por DataChannel (hallazgo
2026-11-16): valores fuera de enum (p. ej. `encouraged`) se mapean al sinónimo
permitido más cercano o a `neutral`; JSON inválido → 1 reintento → fallback o
error pedagógico. Nunca se reenvía al avatar un valor no validado.

### 8.4 Laboratorio P100 (medición)

Procedimiento y resultados en `docs/LABORATORIO_FASE0.md`. Métricas mínimas:
TTFT y tok/s del LLM local; RTF y latencia p50/p95 de STT y TTS; sesiones
concurrentes hasta saturar; VRAM/RAM por sesión; costo por minuto de conversación
(local vs externa). **Ninguna cifra se promete hasta medirla; los objetivos
son metas, no resultados garantizados.**

Hallazgo registrado (2026-11-16, TD-F0-008): Qwen3.5-4B razona por defecto
(`reasoning_content`); con `chat_template_kwargs:{"enable_thinking":false}` el
TTFT medido es 0.22–0.43 s y la generación ~43–50 tok/s en P100. La regla de
la arquitectura conversacional: **thinking desactivado en el loop de voz**;
thinking solo para tareas offline.

---

## 9. Motor pedagógico

### 9.1 CEFR adaptado a México

Niveles A1–C2 con contenidos situados en México (mercado, trabajo, viajes,
familia, negocios, salud). Cada nivel define: gramática, vocabulario meta,
funciones comunicativas, porcentaje objetivo de inglés en la conversación
(A1: 30%; A2: 50%; B1: 70%; B2: 85%; C1+: 100%), y criterios de evaluación.

### 9.2 Memoria del estudiante

```json
{
  "level": "A2",
  "native_language": "es-MX",
  "learning_goals": ["conversation", "business"],
  "weaknesses": ["past_simple", "present_perfect", "th_pronunciation"],
  "vocabulary_mastery": 0.68,
  "grammar_mastery": 0.54,
  "speaking_confidence": 0.71,
  "daily_streak": 8
}
```

(Ilustrativo. Fuente de verdad: `student_levels`, `learning_events`, `pronunciation_attempts`, `vocabulary` con `student_vocabulary_state` derivado.)

- **Repetición espaciada** (SM-2 simplificado) sobre vocabulario y puntos gramaticales débiles.
- **Tipado de errores:** gramatical · pronunciación · vocabulario · comprensión · **atribuible a STT** (no penaliza al alumno cuando Whisper malinterpreta).
- El motor decide: cuándo corregir, cuánto énfasis, y qué actividad sigue — no el LLM.

### 9.3 Evaluación de pronunciación (puerto desacoplado)

Tres capas, sin atajos (ADR-011):

1. **Evaluador** (`PronunciationEvaluator`): analiza el audio y devuelve evidencia fonética normalizada.
2. **Motor pedagógico**: decide si corrige, cuándo y cómo (nunca por un score aislado).
3. **Interfaz**: presenta solo la retroalimentación autorizada.

Contrato — esquema `1.0` (detalle en `docs/fase1/contrato-evaluador.md`):

```python
class PronunciationEvaluator(Protocol):
    name: str
    version: str

    async def evaluate(
        self,
        *,
        audio: AudioRef,                          # storage_key, sha256, duration_ms
        expected_text: str,
        language: str = "en-US",
        context: EvaluationContext | None = None,  # CEFR, lección, palabra foco
    ) -> PronunciationResult: ...
```

```json
{
  "schema_version": "1.0",
  "status": "completed | pending | disabled | failed",
  "engine": {"name": "openpronounce", "version": "0.1.0", "mode": "local"},
  "overall": {"score": null, "scale": "0-100", "confidence": null,
               "reliability": "validated | experimental | unvalidated"},
  "words": [{"index": 0, "word": "three", "expected_ipa": "θɹiː", "actual_ipa": "tɹi",
              "status": "ok | mispronounced | omitted | unintelligible | unknown",
              "confidence": null, "phonemes": []}],
  "phonemes": [{"ipa": "θ", "actual": "t", "error_type": "substitution",
                 "start_ms": 120, "end_ms": 210, "severity": "high"}],
  "evidence": {"per": null, "wer": null},
  "latency_ms": 0,
  "cost_usd": 0.0
}
```

Reglas:

- `status=disabled` mientras el gate §13.5 no esté aprobado; `pending` solo
  durante el procesamiento asíncrono. La UI muestra «Práctica libre» **sin puntaje**.
- `reliability` es obligatorio: sin `validated`, el score no se muestra al alumno.
- El evaluador **no emite juicio pedagógico**; aporta `words[]`, `phonemes[]` y
  `evidence`. El motor pedagógico decide la corrección.
- Se persisten `engine`, `version` y `audio_sha256` para reproducibilidad.
- La puntuación del ejercicio educativo (`exercise_attempts.score`) y la
  fonética (`pronunciation_attempts`) están separadas (ADR-013).

Motores candidatos (adaptadores): OpenPronounce (referencia local), Azure Speech,
Speechace, ELSA (condicionado a acceso), GOP local (investigación).

---

## 10. Motor visual (profesor 3D)

- Three.js + **VRM**: expresiones estandarizadas (aa, ih, ou, ee, oh + blink),
  morphTargets, blendshapes. El modelo VRM se sirve desde el almacenamiento S3 y se cachea en el cliente.
- **Lip-sync:** timeline de visemas del TTS (o derivada del texto por un
  heurístico fonema→visema si el TTS no la emite) → pesos aplicados por frame
  al blendshape correspondiente. Objetivo: desfase < 100 ms respecto al audio.
- **Expresiones y gestos:** alegría, sorpresa, confusión, aprobación; animaciones
  de escucha (inclinación, cejas) y de habla (gestos ilustradores); felicitar al completar lección.
- **Fallback:** si se pierde el DataChannel, el cliente puede animar la boca
  derivada del volumen/análisis del stream remoto (lip-sync "a ciegas", menor
  calidad, sin eventos pedagógicos). Nunca se bloquea la conversación por el avatar.
- **Render en el dispositivo:** costo servidor ≈ 0 por respuesta visual.

---

## 11. Modelo de negocio y control de consumo

Freemium con suscripción como objetivo comercial (precios **hipotéticos** a
validar, no de mercado):

| Plan | Precio | Incluye |
|---|---|---|
| Gratuito | $0 MXN/mes | Evaluación de nivel · lecciones básicas · conversaciones limitadas · avatar básico |
| **Plus** (principal) | **$149 MXN/mes** | Conversaciones ampliadas · profesor 3D · corrección gramatical · práctica de pronunciación · seguimiento personalizado |
| Premium | $249 MXN/mes | Conversaciones más extensas · modelos avanzados · profesores y voces adicionales · simulaciones profesionales · evaluaciones avanzadas |

Control de consumo por usuario (`ai_usage` + contadores Redis):
- Minutos de conversación WebRTC · segundos de síntesis TTS · tokens de API externa · evaluaciones fonéticas · créditos adicionales.
- **No ofrecer conversaciones ilimitadas** hasta conocer el costo real por concurrencia.
- Cobro en México: **Mercado Pago** y **Stripe**, con webhooks
  (`/billing/webhook/*`) para activar, renovar, marcar past_due y cancelar.
- Límites por plan se aplican en el API Gateway **antes** de abrir la sesión WebRTC;
  el cliente muestra consumo restante (`usage_warning` / `plan_limit_reached`).

---

## 12. SLOs y telemetría

Objetivos iniciales (metas, no garantías; se medirán en equipos y redes reales):

| Indicador | Objetivo | Cómo se mide |
|---|---|---|
| Transcripción parcial inicial | < 700 ms | `metrics.t_stt_first_ms` (server) |
| Primera respuesta textual | < 1.5 s | `metrics.t_llm_first_ms` |
| Inicio de reproducción de voz | < 2.5 s | `metrics.t_tts_first_ms` + RTCP del cliente |
| Desfase labial | < 100 ms | offset visemas vs playback (dev tools) |
| Barge-in (interrupción efectiva) | < 300 ms | VAD server → cancelación TTS + `interrupt` |
| Éxito ICE conexión inicial | > 95% (con TURN) | `ice_telemetry` candidateType/connected |
| Sesiones estables ≥ 15 min | sin corte | `conversation_sessions` |
| Costo por minuto de conversación | medible (no objetivo) | `ai_usage` agregado |
| Referencia TTS (caché) | primer byte < 200 ms (hit) / < 1.5 s (miss) | `tts_cache.hit_count` + `metrics.t_tts_ref_ms` |
| Subida de grabación (≤ 15 s) | < 2 s en 4G | cliente + `speech_assets.bytes` |
| Evaluación fonética (cuando esté activa) | p95 ≤ 1.5 s local / ≤ 2.5 s remoto | `pronunciation_attempts.latency_ms` |

Telemetría: cada sesión registra por etapa (STT/LLM/TTS/avatar) en
`conversation_sessions.metrics` y `ai_usage`; red en `ice_telemetry`. En el MVP,
dashboard SQL simple + logs estructurados; Grafana/Prometheus como evolución.

---

## 13. Fase 0 — Laboratorio de voz (BLOQUEANTE)

**Objetivo:** demostrar con evidencia en dispositivos reales que el ciclo
**WebRTC → STT → LLM → TTS → RTP de regreso → sincronización de visemes**
funciona de extremo a extremo. Si no pasa, no se avanza a Fase 1+.

### 13.1 Alcance de la matriz de pruebas

| Dimensión | Cobertura mínima |
|---|---|
| Clientes | Chrome escritorio (Fedora) · Android real (Chrome/WebView Capacitor) · iPhone real (Safari/WKWebView Capacitor) |
| Redes | Wi-Fi · datos móviles · NAT restrictivo (forzando relay TURN con `iceTransportPolicy: 'relay'` en prueba) |
| Audio | Permisos de micrófono · audífonos con/sin mic · interrupción de llamada telefónica · suspensión y reanudación de la app |
| Sesión | Reconexión tras pérdida de conectividad (corte de 10 s y de 60 s) · barge-in · cancelación TTS |
| Modelos | faster-whisper (base, small) es-MX + inglés · Kokoro 82M EN + evaluación ES · Qwen3-TTS 0.6B · Qwen3.5-4B (calidad pedagógica con prompt pedagógico estructurado) |

### 13.2 Criterios de aprobación (go)

1. STT acierta suficientemente en es-MX y en frases en inglés de A1–A2 (tasa de hipótesis utilizables ≥ 90% en frases controladas).
2. Voz TTS comprensible y aceptablemente natural (evaluación subjetiva 2 personas, ≥ 4/5).
3. Respuestas del LLM pedagógicamente correctas en el 80% de los casos de un set de 30 prompts curados.
4. Lip-sync convincente (visemas recibidos por DataChannel descuadrados < 100 ms).
5. Latencias dentro de objetivos §12 o con plan claro de optimización.
6. Sesión estable ≥ 15 minutos sin fugas ni desconexiones anómalas.
7. Costo por minuto de conversación (local vs externa) medido y documentado.

### 13.3 Criterios de no-go y plan B

- **iOS/WKWebView no sostiene audio bidireccional:** documentar; plan B = plugin Capacitor de WebRTC mantenido (evaluar `@capacitor-community/webrtc` u opción nativa) antes de continuar.
- **Latencia local > objetivo en P100 compartida:** no usar P100 para producción; presupuesto para GPU dedicada o API externa.
- **Calidad pedagógica del LLM pequeño insuficiente:** externas por defecto con router híbrido; Qwen local solo para tareas baratas (corrección, traducción).

### 13.4 Entregables

`docs/LABORATORIO_FASE0.md`: hardware, versiones exactas de modelos e
imágenes, comandos de arranque, matriz de resultados por dispositivo/red,
métricas, decisiones go/no-go firmadas por el equipo. **La Fase 1 no comienza
sin este documento aprobado** (ya aprobado para el ciclo de voz).

### 13.5 Fase 0b — Evaluador fonético (investigación paralela, NO bloqueante)

Corre en paralelo a F1–F6. No bloquea ninguna fase de construcción; su resultado
decide **cuándo se habilita** la evaluación fonética como función de producto
(flag `PRONUNCIATION_EVAL_ENABLED`, Apéndice A).

**Gate de adopción** (debe cumplirse antes de mostrar cualquier puntaje):

| Criterio | Umbral |
|---|---|
| Etiquetas humanas | 245 audios reales + 90 sintéticos, 3 jueces, adjudicados |
| Concordancia | κ ≥ 0.60 vs cada juez (revisión) · reportar α de Krippendorff |
| Binario por palabra | precision ≥ 0.75 · recall ≥ 0.80 · **FPR ≤ 0.20** |
| Por fonema | solo se reporta con n ≥ 20 e IC95 |
| Latencia | p95 ≤ 1.5 s local / ≤ 2.5 s remoto |
| Costo | dentro del presupuesto por 1k evaluaciones |

Si ningún motor supera el gate, el producto se lanza **sin puntaje** (práctica
libre: escuchar, grabar, repetir, autocomparar). Ver `docs/fase0/poc-pronunciacion.md`.

---

## 14. Plan de desarrollo — Fases 0–6

Estimación para 2 desarrolladores + apoyo de diseño y QA: **14–18 semanas**
(la Fase 0 de voz ya está cerrada; la Fase 0b corre en paralelo sin bloquear).

**Orden de ejecución oficial (v1.1).** No se renumeroan IDs `TD-F*`; cambia el
orden y se parte Fase 4 y Fase 5.

1. **F1 — Fundamentos** (semanas 1–2): monorepo, backend + JWT, esquema SQL +
   Alembic, Vue base + auth, Docker Compose **propio** (`issitek-language`),
   contrato `PronunciationEvaluator` + `FakeEvaluator`, modelo de voz y
   consentimientos, TTS de referencia con caché y **vertical slice**: login →
   curso A1 → lección → escuchar palabra (Kokoro) → grabar (MediaRecorder) →
   almacenamiento S3 → intento registrado → progreso visible, con evaluación fonética
   desactivada. Resultado: primera pieza real del producto.
2. **F4a — Núcleo educativo y práctica** (semanas 3–5): cursos, lecciones,
   ejercicios, reglas de avance, repetición, historial de intentos, progreso,
   repetición espaciada, admin mínimo de contenido. Resultado: 10 lecciones A1
   jugables de punta a punta.
3. **F2 — Conversación** (semanas 6–8): VAD, faster-whisper, Kokoro/Qwen3-TTS,
   AI Router, orquestador, barge-in, cancelación TTS, visemas por DataChannel y
   corrección contextual. Resultado: conversación hablada funcional.
   **WebRTC es el transporte desde el primer día; no se construye una ruta
   WebSocket paralela de audio.**
4. **F3 — Profesor virtual 3D** (semanas 9–11): VRM, Three.js, expresiones
   (aa/ih/ou/ee/oh + blink), head-look, visemas, emociones y gestos. Resultado:
   profesor que habla y gesticula.
5. **F5a — Administración** (semanas 12–13): alumnos, contenido, estadísticas y
   seguimiento del aprendizaje.
6. **F5b — Integración del evaluador validado** (semanas 13–14): adaptador del
   motor que supere el gate §13.5, activación por cohorte y retroalimentación
   fonética avanzada.
7. **F6 — Pruebas y lanzamiento** (semanas 15–18): pilotos con estudiantes
   mexicanos reales, benchmark de modelos, optimización de latencia, pruebas de
   carga, seguridad (JWT, TURN HMAC, OWASP básico, LFPDPPP), lanzamiento
   controlado.

**Línea paralela — Fase 0b:** juez 3, etiquetado del Set B, calibración de
OpenPronounce y comparación de motores. No bloquea ninguna fase.

Criterios de aceptación por fase: ver `BACKLOG.md`.

---

## 15. Riesgos y mitigaciones

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| R1 | WKWebView/WebView con WebRTC defectuoso o sin permiso mic | Alto (iOS) | Fase 0 en iPhone real; plugin Capacitor WebRTC como plan B; detección de capacidades + mensaje claro |
| R2 | NAT restrictivo sin TURN funcional | Medio-Alto | coturn propio con HMAC (ADR-003); Fase 0 fuerza `relay`; telemetría `candidateType` desde día 1 |
| R3 | Latencia LLM local (P100 compartida) rompe el objetivo de 2.5 s | Medio | Externa como fallback automático; P100 solo lab; presupuestar GPU dedicada si el costo lo justifica |
| R4 | aiortc + ciclo de vida de sesión (fugas, buffers, cancelación) | Medio | Tests de soak (15+ min), límites de sesión, watchdog, limpieza garantizada en `finally`, métricas de memoria por sesión |
| R5 | Whisper falla con acento mexicano y penaliza al alumno | Medio-Alto | Clasificar error `stt_attributable` (confianza STT baja → no penalizar); fine-tuning/modelo es-MX si aplica; revisión humana en pilotos |
| R6 | Costo por minuto inviable para $149 MXN | Alto (negocio) | Medir en Fase 0/2; límites por plan desde diseño; sin "ilimitado"; créditos extra; modelos pequeños primero |
| R7 | Privacidad de voz / menores | Alto (legal) | Consentimiento explícito, retención configurable, borrado, controles parentales, aviso LFPDPPP, minimización |
| R8 | Licencias de modelos (Kokoro/Qwen/whisper) | Bajo-Medio | Revisar licencias antes de producción comercial; atribución; sustitución vía AI Router si cambia licencia |
| R9 | Pérdida de DataChannel degrada avatar (sin visemas) | Bajo | Fallback lip-sync derivado del stream; evento `error` y degradación elegante |
| R10 | TURN relé forzado satura coturn (tráfico relay) | Medio | Medir % relay en telemetría; dimensionar coturn; alertar; considerar TURN geográfico si crece |
| R11 | faster-whisper/CTranslate2 (CUDA 12) no soporta Pascal (P100, sm_60) → STT en CPU en el host actual | Medio | STT CPU en desarrollo (~2.2 s/utterance medidos); en producción: GPU sm_70+, build CT2 compatible, o servidor STT externo; revisar al dimensionar infra |
| R12 | Mostrar un puntaje fonético no validado como si fuera objetivo | Alto (pedagógico/legal) | Flag `PRONUNCIATION_EVAL_ENABLED=false` hasta el gate §13.5; `reliability=validated` obligatorio; práctica libre sin puntaje mientras tanto |
| R13 | El contenido (10 lecciones A1) es la ruta crítica real, no el código | Alto (calendario) | Plan de autoría + QA pedagógica en F4a; plantillas de lección; revisión por docente |
| R14 | Enviar grabaciones de alumnos a proveedores externos sin base legal | Alto (legal) | Consentimiento separado `third_party_processing`; motores externos solo con audio sintético o consentimiento específico; revisar DPA de cada proveedor |
| R15 | Cambiar de motor fonético obliga a rehacer lecciones | Medio | Puerto/adaptador (ADR-011) + contrato versionado + contract tests desde F1 |
| R16 | MinIO archivó su edición comunitaria y ya no distribuye imagen/binarios; el proveedor S3 definitivo no está decidido | Medio (infra) | Código usa cliente S3 (`minio-py`) y `MINIO_ENDPOINT`/`MINIO_PUBLIC_ENDPOINT`: en desarrollo moto; antes de producción decidir MinIO autorizado, Garage, SeaweedFS o S3 gestionado y migrar datos |

> **Nota R16 (2026-11):** `dl.min.io` responde 410 y los registros de MinIO
> devuelven 401. Para no bloquear F1, el Compose de desarrollo usa **moto**
> (`services/storage-dev`) como emulador S3. moto **no** es apto para
> producción. La decisión del proveedor definitivo queda abierta y debe
> resolverse antes del despliegue del piloto; el cambio es de configuración,
> no de código.

---

## 16. Privacidad, voz y menores

- **Consentimiento (dos actos separados):** `recording` (grabar y almacenar la voz en el almacenamiento S3) y `third_party_processing` (enviar audio a un proveedor externo de evaluación). Autorizar uno **no** implica el otro. Sin `recording`, la conversación funciona sin persistir voz (STT solo en memoria).
- **Evidencia:** cada consentimiento guarda versión del aviso, fecha, método y hash de IP/user-agent en `consents`; revocable en cualquier momento con borrado efectivo.
- **Retención:** por defecto, borrado de audios de conversación a los **30 días** (`retention_until`); transcripciones se conservan; el alumno puede borrar su historial (soft delete + borrado físico diferido ≤ 30 días).
- **Cifrado:** TLS en tránsito (HTTP/WS), DTLS-SRTP obligatorio en WebRTC, S3 con cifrado en reposo, secretos en `.env`/vault.
- **Acceso:** URLs de `speech_assets` firmadas y de vida corta (`MINIO_PRESIGN_TTL_S`); verificación `sha256` al completar subida; admin con audit log; nada público.
- **Separación de audios:** `speech_assets.source` distingue `tts_reference` (material del sistema) de `student_recording` (dato personal); políticas y retención independientes.
- **Borrado:** `DELETE /recordings/{id}` marca `deleted_at` y un worker elimina el objeto del almacenamiento S3 en ≤ 24 h; la referencia queda anonimizada.
- **Menores:** si `birth_year` indica < 18, se requiere flujo de consentimiento parental, sesiones más cortas, sin compras in-app directas, y retención reducida.
- **LFPDPPP (México):** aviso de privacidad, derechos ARCO, responsable y domicilio identificables, antes del piloto abierto.

---

## 17. Backlog

Ver **`docs/BACKLOG.md`**: items `TD-F<fase>-<nnn>` con fase, prioridad,
estimación, dependencias y criterios de aceptación. La Fase 0 (voz) es
bloqueante y ya está aprobada; la **Fase 0b (fonética) no es bloqueante** y se
rige por el gate §13.5.

---

## 18. Definición global de hecho (DoD)

1. Código con tests (unitarios para lógica; integración para señalización y pipelines; e2e mínimo del loop de conversación en CI).
2. Contratos actualizados (OpenAPI + JSON Schema de eventos DataChannel en `packages/shared`).
3. Telemetría visible (latencias por etapa; nada "a ciegas").
4. Sin secretos en git; `.env.example` al día.
5. Documentación: README del servicio + sección en `BACKLOG.md` marcada.
6. Revisado por al menos 1 persona distinta al autor (o auto-revisión con checklist en solitario).
7. Contrato del evaluador con **contract tests** y `FakeEvaluator`; cada intento
   guarda `engine`, `version` y `audio_sha256` (reproducibilidad).
8. Toda funcionalidad experimental detrás de **feature flag** documentado en
   `.env.example` y desactivada por defecto en producción.

---

## 19. Referencias

- Capacitor: https://capacitorjs.com/docs · WebRTC/WKWebView: comportamiento por versión de iOS (probar en dispositivo).
- VRM: https://vrm.dev/ (expresiones aa/ih/ou/ee/oh, blink).
- WebRTC: RFC 8825/8827 · Opus RFC 6716 · DTLS-SRTP RFC 5764.
- coturn: https://github.com/coturn/coturn (modo REST `use-auth-secret`, `rest-api-separator`).
- aiortc: https://aiortc.io/
- whisper.cpp: https://github.com/ggml-org/whisper.cpp · faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Kokoro 82M: https://github.com/thewh1teagle/kokoro-onnx / modelos onnx quantization · Qwen3-TTS: Hugging Face · Qwen(3.5): https://huggingface.co/
- Montreal Forced Aligner: https://montreal-forced-aligner.readthedocs.io/
- CEFR: Marco Común Europeo de Referencia para las Lenguas (Council of Europe).
- LFPDPPP (México): Ley Federal de Protección de Datos Personales en Posesión de los Particulares.
- Infraestructura previa del equipo: `mxerp` (coturn REST-only, HMAC ICE, telemetría ICE, `useWebRTCCall.js`), `VozNativa` (whisper.cpp local), `llamaCppP100`, `strata-p100-deploy`, `Qwen36-35B-A3B`, `LFM25-24B-A2B` — se reutilizan **patrones y conocimiento**, no código acoplado.

---

## Apéndice A — Variables de entorno clave (`infra/.env.example`)

```bash
# Proyecto Compose propio (aislado de otros proyectos del VPS)
COMPOSE_PROJECT_NAME=issitek-language
# App
APP_ENV=development
APP_BASE_URL=https://talkdrill.local
JWT_SECRET=change-me
JWT_ACCESS_TTL_MIN=15
JWT_REFRESH_TTL_DAYS=30
# Postgres / Redis / almacenamiento S3-compatible
DATABASE_URL=postgresql+psycopg://issitek:issitek@postgres:5432/issitek_language
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=storage:9000
MINIO_PUBLIC_ENDPOINT=localhost:8090/s3   # host que ve el navegador
MINIO_ACCESS_KEY=issitek
MINIO_SECRET_KEY=change-me
MINIO_BUCKET=talkdrill-assets
MINIO_PRESIGN_TTL_S=300
# Evaluación fonética (Fase 0b — desactivada hasta aprobar el gate §13.5)
PRONUNCIATION_EVAL_ENABLED=false
PRONUNCIATION_EVAL_ENGINE=none
# Retención de grabaciones del alumno (días)
RECORDING_RETENTION_DAYS=30
# coturn (REST-only HMAC) — NUNCA subir el secreto real
TURN_ENABLED=true
TURN_HOST=turn.example.com
TURN_PORT=3478
TURN_TLS_PORT=5349
TURN_REALM=talkdrill
TURN_SHARED_SECRET=change-me-long-random
TURN_CRED_TTL_S=300
TURN_REST_SEPARATOR=_
STUN_URL=stun:stun.l.google.com:19302
# IA local (laboratorio P100) — red de confianza solamente
LLM_LOCAL_BASE_URL=http://192.168.x.x:8080/v1   # llama.cpp OpenAI-compatible
LLM_LOCAL_MODEL=qwen3.5-4b-instruct-q4
STT_LOCAL_URL=http://192.168.x.x:9001           # faster-whisper server
TTS_LOCAL_URL=http://192.168.x.x:9002           # Kokoro / Qwen3-TTS server
# IA externa (respaldo)
LLM_EXTERNAL_PROVIDER=openai-compatible
LLM_EXTERNAL_BASE_URL=https://api.example.com/v1
LLM_EXTERNAL_API_KEY=change-me
LLM_EXTERNAL_MODEL=external-model-id
# Pagos
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_WEBHOOK_SECRET=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
# Correo
SMTP_HOST= SMTP_PORT= SMTP_USER= SMTP_PASSWORD= SMTP_FROM=
```

## Apéndice B — Objetivos de negocio (hipotéticos, a validar)

PLUS $149 MXN/mes como plan principal; objetivo de conversión free→plus 3–6%
(cohortes piloto); retención M30 > 60% en activos de primera conversación
exitosa; sin compromisos de SLA hasta Fase 6.
