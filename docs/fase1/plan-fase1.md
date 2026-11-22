# Fase 1 — Plan de ejecución (Fundamentos)

| Campo | Valor |
|---|---|
| Producto | Issitek Language (talkdrill.com) |
| Fase | **F1 — Fundamentos** |
| Versión | 1.0 |
| Fecha | 2026-11-21 |
| Estado | Aprobado para ejecución |
| Depende de | Fase 0 (voz) aprobada · Maestro v1.1 |
| No depende de | Fase 0b (evaluación fonética) — investigación paralela |

> **Regla de la fase:** F1 termina con **una lección real funcionando de punta a
> punta**, no con un conjunto de módulos aislados. La evaluación fonética queda
> desactivada (`PRONUNCIATION_EVAL_ENABLED=false`) y no se muestra ningún
> puntaje.

## 0. Estado de ejecución (2026-11-21)

**Hecho y verificado**

- [x] Compose propio (`infra/`): web `8090`, API `8000`, Postgres `5433`,
  Redis `6380`, almacenamiento S3 de desarrollo `9100`, worker de retención.
- [x] API FastAPI + SQLAlchemy 2 + Alembic; migraciones `5ebfd9175ba2` y
  `b7c1e2f3a4d5`; seed idempotente del curso A1 (**10 lecciones / 30 ejercicios**).
- [x] Auth JWT + refresh rotativo + argon2 + límite de intentos de login.
- [x] Contrato `PronunciationEvaluator` + `FakeEvaluator` + contract tests
  (**38 pruebas de API en verde**).
- [x] TTS de referencia con caché, autorreparación y clave que incluye el
  proveedor. Kokoro real verificado en el overlay del Compose; los 10 audios de
  las lecciones A1 quedaron pregenerados y la segunda pasada fue caché.
- [x] Worker de retención con `speech_assets.retention_until`, purga idempotente
  de vencidas/revocadas, anonimización de `storage_key` y healthcheck.
- [x] Contenido A1 validado por JSON Schema + reglas semánticas (respuestas,
  duplicados y tipos de ejercicio).
- [x] Consentimientos separados, `presign → PUT → SHA-256 → complete`, borrado
  y revocación independiente.
- [x] Vue 3: registro/login, catálogo, lección, reproductor, grabadora y
  progreso; `typecheck` y build de producción en verde.
- [x] E2E Playwright del recorrido completo con micrófono sintético, TTS,
  consentimiento, subida y progreso; en verde localmente.
- [x] `packages/shared`: snapshot OpenAPI, tipos TS generados y contrato v1 de
  eventos del DataChannel; CI verifica que no haya drift.
- [x] CI: migración + pruebas de API; tipos, OpenAPI TS y build del frontend;
  job E2E con Docker Compose y Chromium.

**Pendiente para cerrar F1**

- [ ] Revisión pedagógica **humana** del contenido A1 (QA técnica y de formato
  ya hecha; el texto sigue siendo un borrador jugable).
- [ ] Decisión del proveedor S3 definitivo (riesgo R16 del maestro).
- [ ] Lint/format en CI (ruff/black/eslint/prettier). Deuda de estilo, no
  bloquea la vertical slice.

---

## 1. Objetivo

Construir la plataforma base de Issitek Language y demostrarla con una **vertical
slice** que un alumno pueda recorrer en el navegador:

1. Inicia sesión.
2. Accede a un curso A1.
3. Abre una lección.
4. Escucha una palabra mediante Kokoro (audio de referencia).
5. Graba su pronunciación con `MediaRecorder`.
6. El audio se almacena en S3-compatible con URL firmada y verificación SHA-256.
7. Se registra el intento educativo.
8. El sistema muestra su progreso.
9. La evaluación fonética permanece desactivada.

## 2. Resultado esperado

Al cierre de F1 debe existir:

- Monorepo operativo (`apps/web`, `services/api`, `services/worker`, `packages/shared`, `infra`).
- API FastAPI con JWT (access + refresh), healthchecks y OpenAPI.
- PostgreSQL con migraciones Alembic (esquema educativo + voz).
- Vue 3 + Vite + TypeScript con login, catálogo A1, lección y progreso.
- Audio Service mínimo: TTS de referencia cacheado y grabación de alumno.
- Contrato `PronunciationEvaluator` implementado con `FakeEvaluator` y
  contract tests.
- Docker Compose **independiente** (`issitek-language`) que convive con los
  demás proyectos del VPS sin interferir.
- Suite de pruebas (unitarias, integración, E2E del recorrido) en CI.

## 3. Alcance

### Dentro de F1

| Área | Incluye |
|---|---|
| Infraestructura | Compose propio, redes/volúmenes/nombres aislados, healthchecks, `.env.example` |
| Backend | Auth (registro, login, refresh, logout), usuarios, cursos/lecciones (lectura), intentos, progreso |
| Datos | Alembic + tablas educativas base + `consents`, `exercise_attempts`, `tts_cache` + deltas de voz |
| Audio | TTS de referencia Kokoro con caché; `MediaRecorder` → presign → S3 → complete |
| Evaluador | Puerto + `FakeEvaluator` (siempre `disabled`), JSON Schema 1.0, contract tests |
| Frontend | Login, curso A1, lección, reproductor de referencia, grabadora, progreso |
| Calidad | Tests unitarios/integración, E2E del recorrido, OpenAPI snapshot, lint/format |
| Privacidad | Consentimiento de grabación y de procesamiento por terceros; URLs firmadas; borrado |

### Fuera de F1 (explícito)

- Conversación en tiempo real (F2): WebRTC, VAD, STT, LLM, barge-in.
- Avatar 3D (F3).
- Contenido definitivo de las 10 lecciones y repetición espaciada (F4a).
- Pagos y apps Capacitor (F5a).
- Integración de un evaluador fonético real (F5b, condicionada al gate).
- Cualquier puntaje fonético visible para el alumno.

## 4. Orden de trabajo

Dos desarrolladores, dos semanas. El orden está pensado para que la vertical
slice se pueda demostrar al final de la semana 2 sin depender de Fase 0b.

| Día | Backend / datos | Frontend / audio | Calidad |
|---|---|---|---|
| 1 | Monorepo, tooling, Compose independiente, healthchecks | Scaffold Vue + router + layout | CI base (lint, typecheck, tests) |
| 2 | Auth JWT + usuarios + migración inicial | Login/registro + sesión | Tests de auth |
| 3 | Cursos/lecciones (lectura) + seeds borrador | Catálogo A1 + lección | Tests de API |
| 4 | Contrato evaluador + `FakeEvaluator` + contract tests | Cliente del contrato (sin puntaje) | JSON Schema + contract tests |
| 5 | Migraciones de voz (`consents`, `exercise_attempts`, `tts_cache`, deltas) | Consentimiento (dos actos) | Tests de migración |
| 6 | TTS de referencia + `tts_cache` + almacenamiento S3 | Reproductor de referencia + presign/upload | Tests de audio |
| 7 | Intento educativo + progreso | Grabadora + intento + progreso | Tests de integración |
| 8 | E2E, hardening, documentación | E2E del recorrido | E2E + revisión |

## 5. Arquitectura de Fase 1

```
                Issitek Language
                  talkdrill.com
                       |
                 Vue 3 / Web
                       |
                    FastAPI
        +--------------+--------------+
        |              |              |
     Usuarios       Lecciones       Progreso
        |              |              |
        +--------------+--------------+
                       |
                 Audio Service
                       |
             +---------+---------+
             |                   |
          Kokoro          S3-compatible
           TTS             Grabaciones
             |                   |
             +---------+---------+
                       |
            PronunciationEvaluator
                       |
                Feature Flag OFF
                       |
               Investigación F0b
```

Tres capas, sin atajos:

1. **Evaluador** (`PronunciationEvaluator`): analiza el audio.
2. **Motor pedagógico**: decide qué corrección ofrecer.
3. **Interfaz**: presenta la retroalimentación autorizada.

En F1 el evaluador devuelve siempre `status=disabled`; no hay puntaje.

## 6. Compose independiente

Requisito explícito: **no interferir** con los otros proyectos del VPS.

| Recurso | Nombre propio |
|---|---|
| Proyecto Compose | `COMPOSE_PROJECT_NAME=issitek-language` |
| Contenedores | `issitek-api`, `issitek-web`, `issitek-postgres`, `issitek-redis`, `issitek-storage`, `issitek-worker`; `issitek-tts` solo con el overlay Kokoro (coturn en fases posteriores) |
| Red | `issitek_net` |
| Volúmenes | `issitek_pgdata`, `issitek_redis` |
| Base de datos | `issitek_language` (usuario `issitek`) |
| Puertos host (dev) | `8090` (web/nginx), `8000` (API), `9100` (S3 dev), `5433` (Postgres), `6380` (Redis) |
| Producción | `server_name talkdrill.com` dedicado; Coturn existente con realm `talkdrill` |

Reglas:

- Ningún servicio publica `80/443` en desarrollo; el contenedor `web` escucha en
  `8090` y se pone detrás del proxy existente en producción.
- Coturn se reutiliza (REST-only HMAC) o se levanta con el proyecto; jamás se
  comparte el secreto entre proyectos.
- Los secretos viven en `infra/.env` (chmod 600) y `.env.example` documenta
  cada variable. Nunca se suben a git.
- Healthchecks obligatorios en `postgres`, `redis`, `storage` y `api`.
- El almacenamiento de desarrollo es **moto**, no MinIO: ver riesgo R16.

## 7. Detalle técnico

### 7.1 Monorepo y tooling

- `pnpm workspaces` para JS/TS; `uv` para Python.
- `packages/shared`: tipos TS generados desde OpenAPI + JSON Schema de eventos.
- Sin Nx/Turborepo en el MVP.
- Formato: `ruff` + `black` (Python), `eslint` + `prettier` (TS).

### 7.2 API de F1

Prefijo `/api/v1`.

| Dominio | Endpoints |
|---|---|
| Auth | `POST /auth/register` · `POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` |
| Perfil | `GET /users/me` · `PATCH /users/me` |
| Cursos | `GET /courses` · `GET /courses/{id}` · `GET /lessons/{id}` · `GET /lessons/{id}/exercises` |
| Intentos | `POST /exercises/{id}/attempts` · `GET /exercises/{id}/attempts` · `GET /me/history` |
| Progreso | `GET /me/progress` · `POST /lessons/{id}/complete` |
| Audio | `GET /tts/reference?text=&voice_id=` · `GET /tts/voices` |
| Grabaciones | `POST /recordings/presign` · `POST /recordings/{id}/complete` · `GET /recordings/{id}` · `DELETE /recordings/{id}` |
| Consentimientos | `GET /consents` · `POST /consents` · `DELETE /consents/{kind}` |
| Salud | `GET /health` · `GET /health/ready` |

Errores: `{"error": {"code", "message", "request_id"}}`. Toda respuesta incluye
`request_id` para trazabilidad.

### 7.3 Datos

- Alembic con migración inicial y deltas de voz descritos en
  [`modelo-datos-voz.md`](modelo-datos-voz.md).
- `exercise_attempts.score` es **educativo**; la evidencia fonética vive en
  `pronunciation_attempts` (ADR-013).
- Seeds de contenido: 10 lecciones A1 en borrador, validadas por JSON Schema.
- `down_revision` probado: `alembic downgrade base` y `upgrade head` limpios.

### 7.4 Audio

**TTS de referencia (Kokoro):**

1. `GET /tts/reference?text=...&voice_id=...`
2. Hash `sha256(text + voice_id + locale + provider)`.
3. Hit → URL firmada del almacenamiento S3 (TTL 300 s) + `duration_ms`.
4. Miss → Kokoro genera, sube a `reference-audio`, guarda en `tts_cache`.
5. Pregenerar las palabras/frases de las 10 lecciones A1.

**Grabación del alumno (`MediaRecorder`):**

1. `POST /recordings/presign` (mime, duración estimada, `exercise_id`, consentimiento).
2. `PUT` directo al almacenamiento S3 con URL firmada.
3. `POST /recordings/{id}/complete` con `sha256` y tamaño.
4. API verifica hash/tamaño, crea `speech_assets` (`source=student_recording`) y
   el intento.
5. Límites: 15 s por defecto (configurable), 5 MB, `audio/webm;codecs=opus`
   (fallback `audio/wav`).
6. Reintentos con backoff; nunca se pierde la grabación local hasta confirmar.

### 7.5 Evaluador

- Puerto `PronunciationEvaluator` + modelos pydantic versionados.
- `FakeEvaluator` devuelve `status=disabled` y `reliability=unvalidated`.
- Contract tests obligatorios (ver [`contrato-evaluador.md`](contrato-evaluador.md)).
- `PRONUNCIATION_EVAL_ENABLED=false` por defecto en todos los entornos.

### 7.6 Frontend

- Vue 3 + Vite + TypeScript + Pinia + Vue Router.
- Vistas: Login/Registro, Catálogo A1, Lección, Progreso.
- La lección muestra: palabra, traducción, audio de referencia, grabadora,
  estado del intento y progreso. **Nunca** un puntaje fonético.
- Accesibilidad: navegación por teclado, foco visible, textos alternativos.
- Responsive móvil primero (es el dispositivo del alumno).

## 8. Criterios de aceptación (DoD de F1)

- [x] `docker compose -p issitek-language up` levanta todo con healthchecks en verde.
- [x] Registro, login, refresh y logout funcionan; tokens expiran correctamente.
- [x] Un alumno ve el curso A1 y abre una lección.
- [x] Escucha una palabra de referencia generada por Kokoro y el segundo request
  sale de caché. _Verificado con `docker-compose.kokoro.yml`; los 10 audios de
  las lecciones quedaron pregenerados._
- [x] Graba, sube al almacenamiento S3 y la grabación se reproduce en la UI.
  _E2E con micrófono sintético; el límite de 15 s se aplica en UI y API._
- [x] El intento queda en `exercise_attempts`; el progreso se refleja en la UI.
- [x] Los dos consentimientos se registran y revocan por separado.
- [x] `DELETE /recordings/{id}` elimina el objeto y anonimiza la referencia (204/410 verificados).
- [x] `PronunciationEvaluator` pasa contract tests; con el flag off no hay puntaje.
- [x] `alembic upgrade head` y `downgrade base` pasan en CI.
- [x] E2E del recorrido completo en verde.
- [x] OpenAPI y tipos compartidos sin drift.
- [x] Ningún secreto en git; `.env.example` completo.

## 9. Riesgos de F1

| Riesgo | Mitigación |
|---|---|
| El contenido A1 se vuelve el cuello de botella | Seeds en borrador en F1; contenido definitivo y QA en F4a |
| `MediaRecorder` con códecs distintos por navegador | Detección de capacidades + fallback WAV; validar en Chrome, Safari y Firefox |
| CORS/firmas S3 mal configuradas | Prueba de integración con bucket real en CI local; TTL corto; `/s3` same-origin en dev |
| Acoplar la UI al evaluador | La UI consume un estado `disabled` explícito; contract tests |
| Fuga de datos de voz | Buckets privados, URLs firmadas, consentimiento y retención documentados |

## 10. Handoff a F4a

Al cerrar F1 se entrega:

- Recorrido vertical demostrable y reproducible.
- Esquema de datos estable (educativo + voz).
- Contrato del evaluador congelado en `1.0`.
- Lista priorizada de contenido A1 pendiente.
- Deuda técnica conocida y estimación revisada de F4a.

## 11. Trazabilidad con el backlog

| Item | Entregable de F1 |
|---|---|
| TD-F1-001…006 | Monorepo, FastAPI, Compose, DB, auth, Vue base |
| TD-F1-014 | Contrato del evaluador + `FakeEvaluator` + contract tests |
| TD-F1-015 | Migraciones de voz y consentimientos |
| TD-F1-016 | Almacenamiento S3, URLs firmadas, SHA-256, retención |
| TD-F1-017 | TTS de referencia con caché |
| TD-F1-018 | Grabación con `MediaRecorder` |
| TD-F1-019 | Vertical slice completo |
| TD-F1-020 | Harness y seed de contenido A1 |

Los items heredados de F1 en el maestro (WebRTC de eco, señalización mínima)
quedan como **deuda trasladada a F2**: F1 ya no construye WebRTC porque la
conversación no es su objetivo. Esta es una consecuencia directa del reorden
aprobado (F1 → F4a → F2).
