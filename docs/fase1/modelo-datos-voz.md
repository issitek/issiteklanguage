# Modelo de datos de voz y consentimiento

| Campo | Valor |
|---|---|
| Producto | Issitek Language (talkdrill.com) |
| Componente | Datos de voz, grabaciones y consentimiento |
| Versión | 1.0 |
| Fecha | 2026-11-21 |
| Estado | Aprobado para F1 |
| Relacionado | ADR-010, ADR-011, ADR-013, ADR-014 · §6 y §16 del maestro |

---

## 1. Principios

1. **La voz del alumno es dato personal sensible en la práctica.** Se minimiza,
   se cifra en tránsito, se accede por URL firmada y se borra a solicitud.
2. **Grabar no es lo mismo que enviar a terceros.** Son dos consentimientos
   distintos e independientes.
3. **Audio de referencia ≠ grabación del alumno.** Se almacenan, retienen y
   auditan por separado.
4. **La puntuación educativa y la fonética no se mezclan** (ADR-013).
5. **Todo es reproducible y auditable:** hash, motor, versión, fecha.

## 2. Clasificación de datos

| Dato | Origen | Sensibilidad | Retención por defecto |
|---|---|---|---|
| `tts_reference` | Kokoro (sistema) | Baja (material del producto) | Permanente / versionada |
| `student_recording` | Alumno (`MediaRecorder`) | Alta (dato personal) | 30 días o revocación |
| `pronunciation_attempts` | Evaluador | Media (metadatos; sin audio) | Según cuenta |
| `exercise_attempts` | Motor educativo | Media (progreso) | Según cuenta |
| `consents` | Alumno/tutor | Alta (evidencia legal) | Mientras exista la cuenta + plazo legal |
| `tts_cache` | Sistema | Baja | Permanente (derivado del texto) |

Regla: **ningún audio de referencia se mezcla con grabaciones del alumno** en el
mismo prefijo, bucket o política de ciclo de vida.

## 3. Modelo relacional

Las tablas educativas base (`users`, `courses`, `lessons`, `exercises`,
`student_progress`, `learning_events`) se definen en el maestro §6. Aquí se
detallan las tablas y deltas introducidos en F1.

### 3.1 `consents`

```sql
CREATE TABLE consents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,     -- recording | third_party_processing | parental
  version       TEXT NOT NULL,     -- versión del aviso de privacidad
  granted_at    TIMESTAMPTZ,
  revoked_at    TIMESTAMPTZ,
  evidence      JSONB NOT NULL DEFAULT '{}',
  UNIQUE (user_id, kind, version),
  CHECK (granted_at IS NOT NULL OR revoked_at IS NOT NULL)
);

CREATE INDEX idx_consents_active
  ON consents (user_id, kind)
  WHERE revoked_at IS NULL;
```

- `kind` separa los actos: `recording` (grabar/almacenar) y
  `third_party_processing` (enviar a proveedor externo). `parental` cubre
  menores de edad.
- `evidence` guarda método (`web_checkbox`), `ip_hash` con sal, `user_agent_hash`
  y `policy_version`; nunca IP en claro.
- Revocar no borra la fila: fija `revoked_at` y dispara el borrado efectivo del
  audio asociado. Volver a otorgar crea una **nueva versión**.

### 3.2 `speech_assets` (deltas)

```sql
ALTER TABLE speech_assets
  ADD COLUMN sha256 TEXT,
  ADD COLUMN source TEXT NOT NULL DEFAULT 'student_recording',
  ADD COLUMN consent_id UUID REFERENCES consents(id),
  ADD COLUMN mime TEXT,
  ADD COLUMN deleted_at TIMESTAMPTZ;

CREATE INDEX idx_speech_assets_user_source
  ON speech_assets (user_id, source, created_at DESC);

CREATE INDEX idx_speech_assets_purge
  ON speech_assets (deleted_at)
  WHERE deleted_at IS NOT NULL;
```

`source`:

| Valor | Uso |
|---|---|
| `tts_reference` | Audio generado por Kokoro para una lección |
| `student_recording` | Grabación del alumno |
| `exercise` | Material de ejercicio (si aplica) |

`consent_id` apunta al consentimiento `recording` vigente en el momento de la
subida. `deleted_at` marca borrado lógico; el worker elimina el objeto físico.

### 3.3 `exercise_attempts`

```sql
CREATE TABLE exercise_attempts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  exercise_id   UUID NOT NULL REFERENCES exercises(id),
  attempt_no    INT NOT NULL DEFAULT 1,
  response      JSONB NOT NULL DEFAULT '{}',
  score         NUMERIC(5,2),      -- EDUCATIVO (0-100), no fonético
  is_correct    BOOLEAN,
  hints_used    INT NOT NULL DEFAULT 0,
  time_ms       INT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, exercise_id, attempt_no)
);

CREATE INDEX idx_attempts_user_recent
  ON exercise_attempts (user_id, created_at DESC);
```

- `score` es la **puntuación educativa**: alimenta progreso, rachas y reglas de
  avance.
- **Nunca** se escribe aquí el puntaje fonético. Si el ejercicio es de
  pronunciación, el intento educativo registra participación/tiempo y la
  evidencia acústica va a `pronunciation_attempts`.
- `response` contiene la respuesta estructurada del ejercicio (p. ej. opción
  elegida); no incluye audio.

### 3.4 `pronunciation_attempts` (deltas)

```sql
ALTER TABLE pronunciation_attempts
  ADD COLUMN exercise_id UUID REFERENCES exercises(id),
  ADD COLUMN attempt_no INT NOT NULL DEFAULT 1,
  ADD COLUMN evaluator TEXT,
  ADD COLUMN engine_version TEXT,
  ADD COLUMN status TEXT NOT NULL DEFAULT 'disabled',
  ADD COLUMN confidence NUMERIC(4,3),
  ADD COLUMN reliability TEXT NOT NULL DEFAULT 'unvalidated',
  ADD COLUMN result_json JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN latency_ms INT,
  ADD COLUMN cost_usd NUMERIC(10,6),
  ADD COLUMN audio_sha256 TEXT,
  ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1.0';

CREATE INDEX idx_pron_attempts_user
  ON pronunciation_attempts (user_id, created_at DESC);
```

- `status`: `disabled | pending | completed | failed`.
- `reliability`: `validated | experimental | unvalidated`.
- `result_json` guarda el resultado normalizado (ver
  [`contrato-evaluador.md`](contrato-evaluador.md)); `evidence.raw` se elimina
  antes de persistir si contiene datos personales.
- `audio_sha256` enlaza con `speech_assets.sha256` para reproducibilidad.

### 3.5 `tts_cache`

```sql
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

- `text_hash = sha256(normalize(text) + "|" + voice_id + "|" + locale)`.
- El objeto vive en el bucket `reference-audio`; `storage_key` es estable.
- `hit_count` alimenta la métrica de caché (SLO: hit < 200 ms).

## 4. Flujos

### 4.1 Consentimiento (dos actos)

```
Alumno abre lección con práctica de voz
        |
        +--> ¿consent recording vigente?
        |        no -> modal 1 (grabar y almacenar)
        |        sí -> continúa
        |
        +--> ¿el motor elegido es remoto?
                 sí -> ¿consent third_party_processing vigente?
                          no -> modal 2 (enviar a proveedor externo)
                                o se usa solo motor local
```

- Aceptar el modal 1 **no** implica el 2.
- Sin `recording`, la práctica funciona sin persistir audio (si el navegador lo
  permite) o se deshabilita la grabación con mensaje claro.
- Sin `third_party_processing`, el adaptador remoto devuelve `disabled`.

### 4.2 Subida de grabación

```
Cliente                         API                         MinIO
  |  POST /recordings/presign ->  |
  |  <- { id, url, fields, ttl }  |
  |  PUT (bytes) -------------------------------------------->|
  |  POST /recordings/{id}/complete { sha256, bytes } ------> |
  |                               |  verifica hash/tamaño    |
  |                               |  crea speech_assets      |
  |  <- 201 { asset_id }          |                          |
```

- TTL de URL: `MINIO_PRESIGN_TTL_S=300`.
- Límites: 15 s (configurable), 5 MB, MIME permitido.
- Si el hash no coincide, 422 y el objeto se elimina.
- La grabación local no se descarta hasta recibir 201.

### 4.3 Borrado

```
DELETE /recordings/{id}
   -> speech_assets.deleted_at = now()
   -> encola purge en worker
   -> worker elimina objeto de MinIO (<= 24 h)
   -> referencia queda anonimizada (sin user_id reversible)
```

Revocar `consent recording` dispara el mismo flujo para todas las grabaciones
del usuario.

### 4.4 TTS de referencia

```
GET /tts/reference?text&voice_id
   -> hash
   -> hit: URL firmada (300 s) + duration_ms + hit_count++
   -> miss: Kokoro -> MinIO reference-audio -> tts_cache
```

Pregeneración: al publicar una lección se generan sus palabras/frases para que
el primer alumno no pague la latencia.

## 5. MinIO

### 5.1 Buckets

| Bucket | Contenido | Acceso |
|---|---|---|
| `reference-audio` | TTS de referencia | Privado; lectura por URL firmada |
| `student-recordings` | Grabaciones del alumno | Privado; URL firmada de vida corta |

Nunca se sirve un bucket como público. No se comparte un bucket entre
referencia y alumno.

### 5.2 Claves

```
reference-audio/{locale}/{voice_id}/{sha256}.opus
student-recordings/{user_id}/{yyyy}/{mm}/{uuid}.webm
```

### 5.3 Ciclo de vida

- `reference-audio`: versionado, sin expiración automática.
- `student-recordings`: expiración a `RECORDING_RETENTION_DAYS` (30) salvo
  retención legal; el borrado lógico manda sobre la fecha.
- Objetos huérfanos (sin fila) se reconcilian semanalmente.

## 6. Retención

| Dato | Retención | Excepción |
|---|---|---|
| Grabación del alumno | 30 días | Revocación (borrado inmediato) o requerimiento legal |
| `pronunciation_attempts` | Vida de la cuenta | — |
| `exercise_attempts` | Vida de la cuenta | — |
| `consents` | Vida de la cuenta + 5 años (evidencia) | — |
| `tts_cache` | Permanente (derivado) | — |

La retención es configurable por entorno; producción no puede superar el máximo
aprobado en el aviso de privacidad.

## 7. Acceso y seguridad

- URLs firmadas con TTL corto; nunca enlaces permanentes.
- Verificación SHA-256 al completar la subida.
- Acceso administrativo con audit log; un admin no puede descargar audio sin
  motivo registrado.
- Cifrado en tránsito (TLS) y en reposo (MinIO/volumen cifrado).
- Sin audio ni texto completo en logs; solo IDs y hashes.
- Respaldos cifrados y con la misma política de retención.

## 8. Separación de puntajes

| Puntaje | Tabla | Alimenta | Visible |
|---|---|---|---|
| Educativo | `exercise_attempts.score` | Progreso, rachas, avance | Sí |
| Fonético | `pronunciation_attempts.result_json` | Investigación / F5b | Solo si `reliability=validated` |

El progreso académico **solo** se calcula desde `exercise_attempts` y
`student_progress`. Un cambio de motor fonético no altera el progreso.

## 9. Menores y LFPDPPP

- Menores de edad requieren consentimiento `parental` verificable.
- Minimización: se guarda solo el audio del ejercicio, no audio ambiente.
- Aviso de privacidad con finalidades, retención y derechos ARCO.
- Derecho de acceso, rectificación, cancelación y oposición: endpoints y
  procedimiento documentado antes del piloto.
- Proveedores externos solo con consentimiento específico y contrato de
  tratamiento de datos (DPA).

## 10. Migraciones (Alembic)

Orden propuesto:

1. `0001_initial_education` — usuarios, cursos, lecciones, ejercicios, progreso.
2. `0002_voice_consents` — `consents` + deltas de `speech_assets`.
3. `0003_pronunciation_deltas` — deltas de `pronunciation_attempts`.
4. `0004_exercise_attempts_tts_cache` — `exercise_attempts`, `tts_cache`.
5. `0005_indexes` — índices parciales y de consulta.

Reglas:

- Toda migración tiene `downgrade` funcional.
- No se renombran columnas existentes sin migración de datos.
- Los seeds de contenido no van en migraciones; van en scripts idempotentes.

## 11. Criterios de aceptación

- [ ] `alembic upgrade head` y `downgrade base` limpios en CI.
- [ ] `consents` permite dos consentimientos independientes y revocación.
- [ ] Una grabación sin `consent recording` vigente no se persiste.
- [ ] Un adaptador remoto sin `third_party_processing` devuelve `disabled`.
- [ ] `DELETE /recordings/{id}` borra el objeto en ≤ 24 h y anonimiza la referencia.
- [ ] `exercise_attempts.score` nunca contiene puntaje fonético.
- [ ] `tts_cache` evita una segunda llamada a Kokoro para el mismo texto/voz.
- [ ] Los audios de referencia y las grabaciones no comparten bucket.
- [ ] Ningún audio ni texto completo aparece en logs.
