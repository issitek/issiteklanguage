# Issitek Language (talkdrill.com) — Backlog técnico

| Campo | Valor |
|---|---|
| Producto | **Issitek Language** (dominio **talkdrill.com**) |
| Versión | 1.1 |
| Fecha | 2026-11-21 |
| Complementa a | `DOCUMENTO_MAESTRO.md` |
| Idioma | Español (México) |

## Cómo leer este backlog

- **ID:** `TD-F<fase>-<nnn>` (p. ej. `TD-F2-003`).
- **Prioridad:** `P0` = bloqueante · `P1` = necesaria para el alcance del MVP ·
  `P2` = deseable, puede moverse a fase posterior sin romper el MVP.
- **Estimación:** días-hombre aproximados para 1 desarrollador (no cuenta diseño ni QA).
- **Dependencias:** IDs que deben estar completados antes de empezar.
- **CA:** criterios de aceptación verificables.
- La **Fase 0 (voz) es bloqueante** y ya está aprobada (`docs/LABORATORIO_FASE0.md`).
- La **Fase 0b (evaluación fonética) NO es bloqueante**: corre en paralelo y su
  resultado solo decide **cuándo se habilita** el puntaje de pronunciación
  (gate §13.5 del maestro).
- **DoD global:** ver §18 del documento maestro (tests, contratos al día, telemetría, sin secretos).

### Resumen de fases

| Orden | Fase | Alcance | Duración estimada |
|---|---|---|---|
| — | 0 | Laboratorio de voz (WebRTC→STT→LLM→TTS→RTP→visemas) | ✅ aprobada |
| ∥ | 0b | Investigación fonética (juez 3, Set B, calibración, motores) | paralela |
| 1 | 1 | Fundamentos + contrato del evaluador + voz/consentimiento + vertical slice | semanas 1–2 |
| 2 | 4a | Núcleo educativo y práctica (lecciones, intentos, progreso, repaso) | semanas 3–5 |
| 3 | 2 | Conversación (VAD/STT/TTS/AI Router/barge-in) | semanas 6–8 |
| 4 | 3 | Profesor virtual 3D (VRM/Three.js/lip-sync) | semanas 9–11 |
| 5 | 5a | Administración, apps y monetización | semanas 12–13 |
| 6 | 5b | Integración del evaluador fonético validado | semanas 13–14 |
| 7 | 6 | Pruebas, optimización y lanzamiento | semanas 15–18 |

---

## Fase 0 — Laboratorio de validación (BLOQUEANTE)

**Objetivo:** demostrar con evidencia en dispositivos reales el ciclo completo
**WebRTC → STT → LLM → TTS → RTP de regreso → visemes por DataChannel**.

| ID | P | Estimación | Dependencias | Tarea | CA (criterios de aceptación) |
|---|---|---|---|---|---|
| TD-F0-001 | P0 | 0.5d | — | Definir alcance y matriz de pruebas (dispositivos, redes, versiones) | Matriz aprobada en `docs/LABORATORIO_FASE0.md` con hardware exacto y criterios go/no-go §13.3 del maestro |
| TD-F0-002 | P0 | 0.5d | — | coturn de laboratorio en la red del lab P100 (REST-only, `use-auth-secret`, separador `_`, realm `talkdrill-lab`, credenciales HMAC de vida corta) | `turnutils_uclient` (o equivalente) logra Allocate + relay con credencial `<ts>_nombre`; STUN responde; credencial ≤ 5 min de TTL |
| TD-F0-003 | P0 | 1d | TD-F0-002 | Endpoint de cuaje de credenciales ICE HMAC (`/lab/ice-credentials`) + servidor aiortc mínimo (`aiortc` Echo: audio RTP de vuelta al cliente) | Chrome escritorio recibe el audio propio (loopback) < 2 s tras offer; logs muestran `candidateType` elegido |
| TD-F0-004 | P0 | 1d | TD-F0-003 | Página Vue mínima de prueba: `getUserMedia({audio})` + RTCPeerConnection + DataChannel `events` + captura del stream remoto + botones de "forzar relay" (`iceTransportPolicy:'relay'`) | Conecta con STUN y con relay TURN en WiFi y datos móviles; muestra candidato ganador y RTT |
| TD-F0-005 | P0 | 0.5d | TD-F0-004 | VAD servidor sobre el stream decodificado (silero-vad o energía) con segmentación por turnos | Log de inicio/fin de habla del alumno con < 150 ms de error; funciona con ruido de fondo ligero |
| TD-F0-006 | P0 | 1d | TD-F0-005 | STT faster-whisper **base** y **small** cuantizados corriendo en P100 (contenedor propio); bench es-MX y en-US con frases A1–A2 controladas | Latencia p50/p95 documentada; tasa de hipótesis utilizables ≥ 90% en es-MX; sin alterar contenedores Qwen/LFM existentes |
| TD-F0-007 | P1 | 0.5d | TD-F0-005 | Misma prueba STT **en CPU** (fallback de desarrollo) | Funciona en Fedora sin GPU; latencia anotada (no obligatorio que sea rápida) |
| TD-F0-008 | P0 | 1d | — | Qwen3.5-4B (o el Qwen disponible en lab) servido vía llama.cpp API OpenAI-compatible en contenedor aislado; prompt pedagógico estructurado (respuesta JSON maestro §8.3) | TTFT p50 y tok/s medidos; en 30 prompts curados ≥ 80% respuestas pedagógicamente correctas; JSON válido en ≥ 95% de turnos |
| TD-F0-009 | P0 | 1d | — | TTS Kokoro 82M (EN) en CPU/GPU; síntesis chunked/streaming; medir latencia hasta primer byte de audio | TTS EN-US comprensible (2 jueces, ≥ 4/5); tiempo a primer audio < 1.5 s tras texto listo |
| TD-F0-010 | P1 | 1d | TD-F0-009 | TTS español: probar Kokoro ES y Qwen3-TTS 0.6B (contenedor independiente) | Se elige una voz ES usable o se documenta limitación y alternativa (voz EN para el profesor en MVP) |
| TD-F0-011 | P0 | 1d | TD-F0-006, TD-F0-008, TD-F0-009 | **Loop E2E de laboratorio**: alumno habla → VAD → STT → LLM → TTS → RTP de regreso → cliente reproduce + DataChannel `assistant_response` con visemas | Flujo completo en Chrome escritorio; latencia primer RTP→voz del profesor < 2.5 s o plan de optimización documentado |
| TD-F0-012 | P0 | 0.5d | TD-F0-011 | Avatar VRM mínimo en página de prueba (boca por visemas aa/ih/ou/ee/oh del timeline DataChannel; parpadeo automático) | Visemas se reciben y se ven; desfase labial vs audio < 100 ms |
| TD-F0-013 | P0 | 0.5d | TD-F0-011 | Barge-in: alumno habla mientras el profesor responde → servidor cancela TTS en curso, flush RTP, cliente recibe `{"type":"interrupt"}` y corta reproducción/lip-sync | Interrupción efectiva percibida < 300 ms; no hay audio residual del profesor tras interrupt |
| TD-F0-014 | P0 | 1d | TD-F0-011, TD-F0-012, TD-F0-013 | Prueba en **Android real**: Chrome + build Capacitor de prueba; micrófono; WiFi y datos; suspensión/reanudación de app | Sesión ≥ 15 min estable; audio bidireccional; permisos pedidos correctamente; resume tras background < 5 s |
| TD-F0-015 | P0 | 1d | TD-F0-011, TD-F0-012, TD-F0-013 | Prueba en **iPhone real** (Safari/WKWebView): mismo guion que Android | Audio bidireccional funciona o se documenta limitación + plan B (plugin Capacitor WebRTC u otra vía). **Si falla, no-go hasta resolver o cambiar estrategia iOS** |
| TD-F0-016 | P1 | 0.5d | TD-F0-003 | Prueba con **NAT restrictivo** forzando relay (`iceTransportPolicy:'relay'`) con datos móviles y/o firewall de prueba | Conexión por relay estable ≥ 5 min; telemetría reporta `candidateType=relay` a `/ice-report` |
| TD-F0-017 | P1 | 0.5d | TD-F0-011 | Reconexión tras corte de red de 10 s y de 60 s | Cliente recrea offer y retoma sesión en ≤ 3 intentos; historial persiste tras reconexión |
| TD-F0-018 | P1 | 0.5d | TD-F0-011 | Medición de costo por minuto: tokens LLM + segundos TTS + máquina (P100 amortizada) por conversación de prueba de 5 min | Costo por minuto local vs estimado externo documentados (cifras orientativas, sin SLAs) |
| TD-F0-019 | P1 | 0.5d | TD-F0-006 | Set de 30 prompts pedagógicos curados (errores típicos es-MX: past_simple, th, present_perfect, ø-articles, false friends) con respuestas esperadas | Set versionado en `docs/fase0/prompts-es-mx.md`; usado en TD-F0-008 y en regresión futura |
| TD-F0-020 | P0 | 0.5d | TD-F0-001…019 | **Informe go/no-go** en `docs/LABORATORIO_FASE0.md`: resultados, métricas, decisiones, plan B | Decisión explícita go/no-go por criterio §13.2 del maestro; aprobado por las dos personas responsables; si no-go, backlog de fase 1 no se inicia |

---

## Fase 0b — Evaluador fonético (investigación paralela, NO bloqueante)

**Objetivo:** determinar con evidencia qué motor (si alguno) merece habilitar la
evaluación de pronunciación como función de producto. **No bloquea F1–F6.**

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F0b-001 | P0 | 0.5d | — | Respaldar etiquetas de jueces y construir la hoja ciega de discrepancias (144 filas: 140 discrepancias + 4 sin marcar) | `lab/data/pronunciation/labels/backup/` con md5; hoja servida solo a `juez3` |
| TD-F0b-002 | P0 | 0.5d | TD-F0b-001 | Acceso `juez3` con Basic Auth independiente y modo ciego (sin score/confianza/IPA) | 401 con credencial incorrecta; juez3 no ve progreso de juez1/2 |
| TD-F0b-003 | P0 | 1d | TD-F0b-001 | Conjunto B: 90 clips sintéticos (Kokoro `af_heart`, `es-dora`, `es-alex`) etiquetados por los 3 jueces con progreso por tarea | 90/90 etiquetados por cada juez; audio servido con auth |
| TD-F0b-004 | P0 | 1.5d | TD-F0b-001…003 | Fusión y adjudicación: 3/3 directo · 2/3 mayoría · 3 distintos → experto; 4 clases + etiqueta binaria derivada | `labels-final.csv` (335 filas) con origen y observaciones; κ vs cada juez reportado |
| TD-F0b-005 | P0 | 2d | TD-F0b-004 | Medir OpenPronounce sobre A y B con `--json-out`; precision/recall/FPR/AUC + IC95 bootstrap + desglose θ/ð/ɪ/ɹ | Tabla reproducible por script; sin números manuales |
| TD-F0b-006 | P2 | 3d | TD-F0b-004 | Comparación de motores (Azure, Speechace, ELSA condicionado, GOP local) sobre Set B | Tabla comparativa + McNemar + latencia/costo; advertencia de validez (sintético vs real) |
| TD-F0b-007 | P0 | 0.5d | TD-F0b-005…006 | Informe P4 y gate §13.5 del maestro | Decisión adoptar/modificar/descartar por motor; aprobada |

---

## Fase 1 — Fundamentos (semanas 1–2)

**Objetivo:** plataforma base funcional y primera **vertical slice** educativa
(login → curso A1 → lección → escuchar referencia → grabar → S3 → intento → progreso),
con evaluación fonética desactivada. La conversación WebRTC se construye en F2.

> **Estado (2026-11-21):** implementados y probados TD-F1-002, 003, 004, 005,
> 006 (dev), 007, 014, 015, 016 (S3-compatible), 017 (fake/Kokoro
> configurable), 018 y 019 (vertical slice vía proxy web). Pendientes:
> TD-F1-001 (worker/`packages/shared`), 013 (OpenAPI snapshot), Kokoro real en
> Compose, E2E de navegador y proveedor S3 definitivo (R16). Detalle en
> [`docs/fase1/plan-fase1.md`](fase1/plan-fase1.md#0-estado-de-ejecución-2026-11-21).

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F1-001 | P0 | 0.5d | TD-F0-020 | Estructura monorepo (`apps/web`, `services/api`, `services/voice`, `services/worker`, `packages/shared`, `infra/`) + pnpm workspaces + uv para Python | `pnpm -r build` y arranque de servicios OK; CI básico (lint+typecheck) |
| TD-F1-002 | P0 | 0.5d | TD-F1-001 | `.env.example` completo (maestro Apéndice A) + gestión de secretos + `.gitignore` + hook pre-commit sin secretos | Ningún secreto en git; ejemplo documentado |
| TD-F1-003 | P0 | 2d | TD-F1-001 | Backend FastAPI base: estructura de dominios (auth, users, conversation, speech, pronunciation, subscriptions, admin), logging estructurado, request-id, manejo de errores uniforme | `GET /health` OK; errores con `{"error":{code,message,request_id}}` |
| TD-F1-004 | P0 | 1d | TD-F1-003 | Auth JWT: register/login/refresh/logout; password hashing (argon2/bcrypt); rate limit auth | Flujo completo; access 15 min, refresh 30 d; rate limit en `/auth/login` |
| TD-F1-005 | P0 | 2d | TD-F1-003 | Esquema SQL (maestro §6) en Alembic: usuarios, suscripciones, perfiles, niveles, cursos/lecciones/ejercicios, vocabulario, grammar_topics, progreso, learning_events, conversation_sessions, conversation_messages, ice_telemetry, speech_assets, avatars, voice_profiles, ai_usage, model_registry | `alembic upgrade head` limpio; seeds mínimos (planes, voces Kokoro) |
| TD-F1-006 | P0 | 2d | TD-F1-001 | Docker Compose dev all-in-one (nginx, api, worker, postgres, redis, minio, coturn **propio del proyecto**, puertos documentados libres) | `docker compose up` levanta todo; sin colisiones con puertos de proyectos existentes (lista en `infra/README.md`) |
| TD-F1-007 | P0 | 2d | TD-F1-006 | Vue 3 + Vite + TS base: routing, layout, tema, auth (login/registro), `pages/home`, store (Pinia) | App corre en dev; login real contra API |
| TD-F1-013 | P2 | 0.5d | TD-F1-003 | OpenAPI snapshot + `packages/shared` con tipos TS de eventos DataChannel | `pnpm generate` actualiza tipos; CI valida que no hay drift |
| TD-F1-014 | P0 | 1d | TD-F1-003 | Contrato `PronunciationEvaluator` (Protocol + modelos pydantic versionados) + `FakeEvaluator` (`status=disabled`) + contract tests | Contrato en `docs/fase1/contrato-evaluador.md`; JSON Schema `1.0`; tests cubren los 4 estados |
| TD-F1-015 | P0 | 1d | TD-F1-005 | Migraciones de voz: `consents`, `exercise_attempts`, `tts_cache` + deltas de `pronunciation_attempts` y `speech_assets` | `alembic upgrade head` limpio; `downgrade` probado |
| TD-F1-016 | P0 | 1d | TD-F1-006 | Almacenamiento S3-compatible: buckets `reference-audio` y `student-recordings`; presign TTL 300 s; verificación SHA-256; retención | Subida firmada OK; hash verificado; URL vencida → 403 |
| TD-F1-017 | P0 | 1d | TD-F1-003 | TTS de referencia: `GET /tts/reference` con caché `tts_cache` (Kokoro) + `GET /tts/voices` | Segundo request idéntico responde < 200 ms desde caché |
| TD-F1-018 | P0 | 1d | TD-F1-016 | Grabación cliente con `MediaRecorder` (opus/wav): presign → PUT → complete; límites de duración/tamaño y reintentos | Grabación de 15 s sube y se reproduce; reintento tras fallo de red |
| TD-F1-019 | P0 | 2d | TD-F1-004…018 | **Vertical slice**: login → curso A1 → lección → escuchar palabra (Kokoro) → grabar → S3 → intento registrado → progreso; evaluación fonética desactivada | Recorrido E2E en navegador; `exercise_attempts` y `speech_assets` correctos; UI muestra «Práctica libre» sin puntaje |
| TD-F1-020 | P1 | 1d | TD-F1-005 | Harness de contenido: JSON Schema de lección + seed de 10 lecciones A1 (borrador) + validación en CI | Seed carga sin errores; lección inválida falla con mensaje claro |

---

## Fase 2 — Motor de voz + IA con WebRTC (semanas 3–5)

**Objetivo:** conversación hablada funcional alumno↔profesor (sin avatar completo aún), sobre WebRTC desde el día 1.

> **Heredados de F1 (reorden v1.1):** `TD-F1-008`…`TD-F1-012` conservan su ID y se ejecutan en esta fase, porque la conversación es su hogar natural. F1 ya no construye WebRTC.

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F1-008 | P1 | 1d | TD-F1-007 | Pantalla de selección de profesor (avatar estático por ahora) + selección/creación de sesión | La sesión se crea en BD al pulsar "Empezar" |
| TD-F1-009 | P0 | 2d | TD-F1-003, TD-F1-006 | **Señalización WebRTC en API**: `POST /conversation/sessions/{id}/webrtc/offer`, `POST .../webrtc/ice`, `WS .../signaling` (ICE trickle); cuaje de credenciales TURN HMAC (reuso del patrón mxerp,realm propio) | Offer→answer OK en navegador; ICE trickle por WS; credenciales ≤ 5 min; telemetría básica a `ice_telemetry` |
| TD-F1-010 | P0 | 2d | TD-F1-009 | Voice Service aiortc **modo eco** integrado a la sesión: audio RTP de vuelta al cliente + DataChannel `events` abierto (mensajes de prueba) | Alumno oye su propia voz < 2 s; aparece "connected" vía DataChannel |
| TD-F1-011 | P1 | 0.5d | TD-F1-010 | `POST /webrtc/ice-report` + `GET /webrtc/ice-report/recent` (admin) estilo mxerp | Cliente reporta candidateType/RTT; admin ve últimos N reportes |
| TD-F1-012 | P1 | 1d | TD-F1-007 | Captura y reproducción de audio en cliente: worklets, `getUserMedia`, manejo de audífonos e interrupciones (ducking cuando hay llamada) | Audio claro; sin acople con audífonos; detecta pérdida de permiso mic |
| TD-F2-001 | P0 | 1d | TD-F1-010 | Pipeline aiortc: Opus→PCM 16 kHz mono→VAD→segmentación; integración con faster-whisper (contenedor/servicio P100; fallback CPU documentado) | Alumno→texto con < 1 s extra de latencia vs Whisper directo |
| TD-F2-002 | P0 | 2d | TD-F2-001 | Integración AI Router (cliente HTTP a LLM local/externa según §8 maestro): timeouts, fallback ladder, JSON estructurado validado (pydantic), registro en `ai_usage` | Local sano → local; degradado → externa; JSON inválido → reintento 1 vez → error amigable sin romper sesión; **emociones normalizadas contra whitelist (p. ej. `encouraged`→`encouraging`) antes de emitirlas por DataChannel** |
| TD-F2-003 | P0 | 1d | TD-F2-002 | Prompts pedagógicos del sistema (nivel CEFR, es-MX, porcentaje inglés por nivel, tipo de corrección); set de regresión TD-F0-019 | Set de prompts pasa ≥ 80% (reuso del laboratorio) |
| TD-F2-004 | P0 | 1.5d | TD-F2-002 | Orquestador de conversación: contexto (nivel, objetivo, debilidades), historial reciente, presupuesto de tokens, decisión de corregir/no corregir | Respuestas coherentes con historial ≥ 5 turnos; corrección solo cuando aplica (no todo error menor) |
| TD-F2-005 | P0 | 1.5d | TD-F2-001 | TTS Kokoro (EN) + voz ES elegida en Fase 0; síntesis **chunked**; primera-byte-rápido; integración aiortc→RTP | Profesor responde con voz EN y, en modo "mezcla es/en", frases en español; TTS no bloquea el loop |
| TD-F2-006 | P0 | 1.5d | TD-F2-001, TD-F2-005 | **Barge-in**: VAD continuo detecta alumno durante la reproducción del profesor → cancelar síntesis TTS en curso, flush buffers, enviar `interrupt`, registrar en `metrics` | Interrupción efectiva < 300 ms; sin eco residual; tasa de falsos barge-in medida en prueba con 10 interjecciones |
| TD-F2-007 | P1 | 1d | TD-F2-005 | Timeline de visemas: del TTS (si lo emite) o derivado fonema→visema del texto de salida; envío por DataChannel sincronizado con inicio del stream RTP | Visemas recibidos con `t_ms` absolutos; verificado en página de prueba (boca-labial aunque el avatar sea placeholder) |
| TD-F2-008 | P1 | 1d | TD-F2-004 | Persistencia de conversación: cada turno (alumno STT + respuesta, correcciones, emoción, confianza STT, visemas) en `conversation_messages` | Sesión se puede reanudar leyendo historial; confianza STT guardada; errores `stt_attributable` no cuentan contra el alumno |
| TD-F2-009 | P0 | 1d | TD-F2-001…007 | **Loop conversacional completo en staging**: 5 escenarios (A1 saludo, A2 error past simple, th pronunciation, tema libre, mezcla es/en) | Escenarios documentados pasan en Chrome; latencias §12 medibles en `metrics` |
| TD-F2-010 | P1 | 1d | TD-F2-009 | Reconexión y resiliencia: corte de red 10–60 s, caída del Voice Service, reinicio de API — la sesión sigue vía historial o termina limpia con aviso | Sin fugas de memoria/sesión tras 20 ciclos; `session_ended` con razón correcta |
| TD-F2-011 | P2 | 1d | TD-F2-002 | Panel interno mínimo de modelos (`/internal/models`): estado local/externa, latencias p50/p95, consumo del día | Visible solo para admin; alimentado por `ai_usage` |
| TD-F2-012 | P1 | 0.5d | TD-F2-005 | Sí/no es/en por nivel: tabla de porcentajes ES/EN y arranque con 30% inglés en A1 (maestro §9.1) | Verificado con prompts de nivel A1 (respuesta predominantemente en español con inglés dosificado) |

---

## Fase 3 — Profesor virtual 3D (semanas 6–8)

**Objetivo:** el profesor 3D habla, parpadea, reacciona y sincroniza labios con el audio WebRTC.

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F3-001 | P0 | 1d | TD-F1-007 | Escena Three.js en `apps/web/src/avatar/`: render VRM, luz, cámara, resize, dispose correcto | 60 fps en laptop media y 30+ fps en Android de gama media; sin fugas al desmontar |
| TD-F3-002 | P0 | 1d | TD-F3-001 | Cargar VRM desde S3/assets con cache (Cache Storage + fallback dev local); 1 profesor v1 (asset licenciado/propio) | Carga < 3 s en 4G (con caché < 500 ms); skeleton mientras carga |
| TD-F3-003 | P0 | 2d | TD-F3-002 | Lip-sync: aplicar pesos aa/ih/ou/ee/oh (+sil) desde timeline DataChannel a blendshapes VRM; fallback por análisis del stream remoto | Desfase < 100 ms medido con clicker/visemas log; fallback activa si DataChannel cae |
| TD-F3-004 | P1 | 1d | TD-F3-003 | Parpadeo automático + mirada (look-at cámara) + respiración idle + movimiento de cabeza al hablar/escuchar | Se ve natural en demo; configurable intensidad |
| TD-F3-005 | P1 | 1.5d | TD-F3-003 | Expresiones por `emotion` (neutral, encouraging, surprised, confused, approving, playful) + transiciones suaves | Emoción cambia < 200 ms tras `assistant_response`; mezcla sin pops |
| TD-F3-006 | P1 | 1.5d | TD-F3-005 | Animaciones de estado: idle, listening (inclinación), thinking, speaking, celebrating (al terminar lección) | Estados driven por `listening_state`/`turn_end`; probadas todas |
| TD-F3-007 | P1 | 1d | TD-F3-006 | Gestos ilustradores para corregir/Felicidades + subtítulos en pantalla (texto + traducción + corrección destacada) | UI muestra corrección legible en móvil; accesible (contraste, tamaño fuente) |
| TD-F3-008 | P2 | 1d | TD-F3-003 | Segundo profesor (voz + look distintos) y selección en UI | Cambio de profesor sin recargar app |
| TD-F3-009 | P1 | 0.5d | TD-F3-001 | Presupuesto de render en móvil: DPR cap, antialias según dispositivo, LOD del avatar, pausa fuera de viewport | Consumo CPU/GPU documentado; modo "avatar estático" de emergencia |
| TD-F3-010 | P1 | 0.5d | TD-F3-003…008 | E2E avatar en conversación real: 3 sesiones grabadas (pantalla+mic) evaluadas por 2 personas | Checklist de naturalidad aprobada; video de evidencia en `docs/` |

---

## Fase 4a — Núcleo educativo y práctica (semanas 3–5)

**Objetivo:** producto educativo estructurado A1–A2 con práctica, intentos y
progreso, **sin** evaluación fonética ni corrección por IA.

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F4-001 | P0 | 1d | TD-F1-005 | Contenido A1: 8–10 lecciones, con objetivos, vocabulario (lemma, pos, traducción, ejemplo), gramática y ejercicios | Seeds cargados; revisión pedagógica firmada |
| TD-F4-002 | P0 | 2d | TD-F4-001 | Lección player: presentar → ejercicio → feedback; tipos: elegir, traducir, escuchar, repetir (sin puntaje fonético) | Flujo completo usable en móvil |
| TD-F4-005 | P0 | 1.5d | TD-F4-002 | Repetición espaciada SM-2 simplificado (vocabulario + gramática débil): cola en Redis + worker | Palabras dominadas salen de la cola; repaso programado visible |
| TD-F4-007 | P1 | 1d | TD-F4-002 | Estadísticas alumno: rachas, minutos, dominio por área, debilidades top-3, evolución semanal | `/statistics` < 300 ms; vista "progreso" en web |
| TD-F4-008 | P1 | 1d | TD-F4-007 | Recomendador: próxima lección según nivel + debilidades | Recomienda coherentemente en casos de prueba |
| TD-F4-009 | P2 | 1d | TD-F4-001 | Editor interno mínimo de lecciones (JSON + UI simple) | Contenido editable y versionado en BD |
| TD-F4-011 | P0 | 1d | TD-F4-002 | Historial de intentos: `exercise_attempts` con reintentos, pistas usadas y tiempo | Historial por ejercicio y por lección; sobrevive a recarga |
| TD-F4-012 | P0 | 1d | TD-F4-002 | Reglas de avance y estados de lección (`not_started` · `in_progress` · `completed`) + `student_progress` | Completar lección actualiza progreso y desbloquea la siguiente |
| TD-F4-013 | P1 | 1d | TD-F4-001 | QA de contenido: checklist pedagógico y consistencia vocabulario↔ejercicios↔audio | 10/10 lecciones pasan checklist |

---

## Fase 4b — Corrección contextual y memoria (semanas 6–8, tras F2)

**Objetivo:** aprovechar la conversación para memoria del estudiante y
corrección contextual.

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F4-003 | P1 | 1d | TD-F4-002, TD-F2-001 | Evaluación de nivel (placement): quiz hablado adaptativo A1→B1 con STT | Sitúa en A1/A2/B1 coherentemente (validar con 5 personas) |
| TD-F4-004 | P0 | 2d | TD-F2-008 | Memoria del estudiante: perfil (weaknesses, mastery), tipado de error (grammar/pronunciation/vocabulary/comprehension/stt_attributable) post-turno | Tras 3 sesiones con errores past_simple repetidos, aparece en `weaknesses` |
| TD-F4-010 | P1 | 1d | TD-F4-003…008 | Integración educativa en la conversación: el orquestador inyecta debilidad actual y vocabulario en repaso al prompt | Conversación referencia material real del alumno |
| TD-F4-014 | P1 | 1d | TD-F4-004 | Panel de debilidades del alumno (alumno y admin) con evolución | Visible y coherente con `learning_events` |

---

## Fase 5a — Apps, administración y monetización (semanas 12–13)

**Objetivo:** MVP multiplataforma comercializable y operable.

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F5-001 | P0 | 2d | TD-F1-007, TD-F2-010 | Capacitor 8 Android: proyecto, permisos mic, build debug/release, icono/splash, `appUrlOpen`, segundo plano (banner de sesión activa) | APK instalable y conversación estable en 2 Android distintos |
| TD-F5-002 | P0 | 2d | TD-F5-001 | Capacitor 8 iOS: proyecto, permisos, background modes, Interruption handling (llamada telefónica), build TestFlight interna | App corre en iPhone real ≥ 15 min; sesión sobrevive background breve |
| TD-F5-003 | P1 | 1d | TD-F5-001, TD-F5-002 | Verificación WebRTC en ambos builds (matrix TD-F0-014/015): datos móviles, relay forzado, resume | Sin regresiones vs navegador |
| TD-F5-004 | P0 | 2d | TD-F1-004 | Planes y límites: Free/Plus/Premium (maestro §11); contadores Redis (minutos, segundos TTS, evaluaciones); enforcement en apertura de sesión y en TTS | Al alcanzar límite, sesión no inicia (o se corta con aviso) sin cortar de golpe audio del profesor |
| TD-F5-005 | P0 | 2d | TD-F5-004 | Mercado Pago: checkout suscripción, webhook firmado → activar/renovar/past_due/cancelar en `subscriptions` | Ciclo completo en sandbox: alta, renovación, tarjeta rechazada, cancelación |
| TD-F5-006 | P0 | 2d | TD-F5-004 | Stripe: igual que Mercado Pago (segundo rail) | Ciclo completo en/test mode; ambos rail activos |
| TD-F5-007 | P1 | 1d | TD-F5-004 | Página de planes/upgrade + estado de suscripción + consumo restante (barras) | UX clara; sin dark patterns |
| TD-F5-008 | P1 | 2d | TD-F1-003 | Panel administrativo: usuarios, sesiones (trazabilidad de conversación), métricas (DAU, minutos, costo), corte de usuarios, edición de límites | Admin con rol admin; accesos auditados |
| TD-F5-009 | P1 | 1d | TD-F1-005 | Retención y consentimiento en producción: worker borra audio vencido; UI de borrado de historial; aviso de privacidad + aceptación | Tras cumplir `retention_until`, audios no existen en el almacenamiento S3; ARCO request documentado |
| TD-F5-010 | P1 | 1d | TD-F5-001, TD-F5-002 | Analítica mínima: activación (primera sesión completada), retención D1/D7/D30, minutos promedio, conversión free→paid | Eventos a BD/warehouse simple; dashboard SQL |
| TD-F5-011 | P2 | 1d | TD-F5-008 | Rate limiting global + WAF básico (reglas nginx: tamaños, métodos, headers) | Fuzzing básico sin 5xx anómalos |

---

## Fase 5b — Integración del evaluador fonético (semanas 13–14)

**Objetivo:** habilitar la evaluación de pronunciación **solo** si el motor
superó el gate §13.5, con activación gradual por cohorte.

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F5-012 | P0 | 1.5d | TD-F1-014, TD-F0b-007 | Adaptador del motor ganador (OpenPronounce/Azure/Speechace) tras el puerto `PronunciationEvaluator` | Contract tests pasan; mismo resultado normalizado que el motor de referencia |
| TD-F5-013 | P0 | 1d | TD-F5-012 | Activación por cohorte con `PRONUNCIATION_EVAL_ENABLED` + `reliability` por motor | Flag off → `status=disabled`; flag on → puntaje solo con `reliability=validated` |
| TD-F5-014 | P0 | 1.5d | TD-F5-012 | UI de retroalimentación fonética: palabra, fonema, ejemplo y reintento | Alumno entiende el error; sin puntaje crudo sin contexto |
| TD-F5-015 | P1 | 1d | TD-F5-012 | Telemetría y costos del evaluador (`pronunciation_attempts`, `ai_usage`) | Latencia p95 y costo por 1k visibles en admin |
| TD-F4-006 | P1 | 2d | TD-F5-012 | Evaluación de pronunciación v1 sobre ejercicios (evidencia + feedback accionable) | Puntaje coherente en 20 muestras etiquetadas; feedback comprensible para A2 |

---

## Fase 6 — Pruebas y lanzamiento (semanas 15–18)

**Objetivo:** calidad, rendimiento, seguridad y lanzamiento controlado.

| ID | P | Est. | Dependencias | Tarea | CA |
|---|---|---|---|---|---|
| TD-F6-001 | P0 | 3d | TD-F2-010, TD-F3-010 | **Piloto cerrado**: 10–15 estudiantes mexicanos reales (A1–B1), 2 sesiones c/u; graban feedback; se mide latencia real y % sesiones sin corte | ≥ 80% completa la segunda sesión; informe de hallazgos |
| TD-F6-002 | P0 | 2d | TD-F6-001 | Fix-list del piloto (bugs, prompts, voz, UX de correcciones) | Checklist de piloto cerrada o diferida explícitamente |
| TD-F6-003 | P1 | 2d | TD-F2-009 | Benchmark de modelos en condiciones piloto: elegir voces finales (Kokoro vs Qwen3-TTS), STT base vs small endurecido, Qwen local vs externa en costos | Decisión documentada en `model_registry` y maestro §8 |
| TD-F6-004 | P0 | 2d | TD-F2-010 | Pruebas de carga: N sesiones concurrentes por instancia Voice Service (CPU y P100); degradación y límite por instancia | Límite medido (p. ej. sesiones/instancia); autoscaling doc; alertas |
| TD-F6-005 | P0 | 2d | TD-F1-006 | Seguridad: JWT endurecido, TURN HMAC rotado, rate limits, headers (CSP), dependabot, secret scanning, OWASP top-10 pass básico | Reporte sin críticos abiertos; checklist OWASP en repo |
| TD-F6-006 | P1 | 1.5d | TD-F5-009 | Privacidad legal: aviso de privacidad final (LFPDPPP), flujo parental si hay menores, exportar/borrar datos a solicitud | Aviso publicado; proceso ARCO documentado y probado |
| TD-F6-007 | P1 | 1d | TD-F6-001 | Optimización de latencia: medir y recortar cada etapa (VAD, STT, LLM, TTS, DataChannel) según telemetría real | Al menos 1 mejora significativa en primer-voz o documentado por qué no |
| TD-F6-008 | P0 | 1d | TD-F6-001…007 | **Go/no-go de lanzamiento** + plan de lanzamiento controlado (lista cerrada, invitaciones, feature flags, rollback) | Decisión firmada; rollout gradual; rollback probado |
| TD-F6-009 | P2 | 1d | TD-F6-008 | Runbook de operaciones: arranque/parada, backups (pg_dump diario + versioning S3), restore probado, monitoreo y alertas | Restore de backup probado en staging |

---

## Totales orientativos

| Fase | Items | Días-hombre aprox. |
|---|---|---|
| 0 (voz, aprobada) | 20 | 14–16 |
| 0b (paralela) | 7 | 8–9 |
| 1 | 15 | 17 |
| 2 | 17 | 20–22 |
| 3 | 10 | 11 |
| 4a | 9 | 11–12 |
| 4b | 4 | 5–6 |
| 5a | 11 | 17 |
| 5b | 5 | 7–8 |
| 6 | 9 | 15–16 |
| **Total** | **107** | **~125–134 días ≈ 25–27 semanas-persona** |

Con 2 desarrolladores y diseño/QA de apoyo, ~125 días-hombre de desarrollo puro
son coherentes con el calendario del documento maestro (Fase 0 de voz ya
cerrada; Fase 0b en paralelo). Los números son orientación de planificación, no
compromiso; se reestimarán al cierre de F1 (vertical slice).

## Fuera de alcance del MVP (fase posterior)

Cursos B1–C2 completos · profesores personalizables · clases grupales (SFU ya decidido para fase posterior) · certificaciones · app de escritorio · gamificación avanzada ·
marketplace de voces.
