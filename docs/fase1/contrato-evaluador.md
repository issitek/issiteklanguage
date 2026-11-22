# Contrato del evaluador de pronunciación

| Campo | Valor |
|---|---|
| Producto | Issitek Language (talkdrill.com) |
| Componente | `PronunciationEvaluator` (puerto) |
| Versión del contrato | **1.0** |
| Fecha | 2026-11-21 |
| Estado | Congelado para F1; cambios requieren nueva versión |
| Relacionado | ADR-011, ADR-012, ADR-013 · §9.3 y §13.5 del maestro |

---

## 1. Propósito

Definir la frontera entre **quien analiza el audio** y **quien decide qué
corrección ofrecer**. El evaluador es un puerto con adaptadores intercambiables:
OpenPronounce, Azure Speech, Speechace, ELSA y GOP local no deben filtrar sus
formatos ni sus decisiones pedagógicas al resto del producto.

Reglas de diseño:

1. El evaluador devuelve **evidencia**, no juicio pedagógico.
2. Un resultado sin `reliability=validated` **no se muestra como puntaje**.
3. El contrato es versionado, serializable y testeable sin red.
4. Un fallo del evaluador **nunca** rompe la lección ni el progreso académico.

## 2. Las tres capas

```
audio + texto esperado
        |
        v
[1] Evaluador  ->  PronunciationResult (evidencia normalizada)
        |
        v
[2] Motor pedagógico -> decide si corrige, cuándo y cómo
        |
        v
[3] Interfaz -> muestra solo la retroalimentación autorizada
```

- **Capa 1** no conoce lecciones, rachas ni CEFR. Solo acústica y texto.
- **Capa 2** aplica confianza, evolución del alumno, contexto de la lección y
  política pedagógica. Puede decidir **no corregir** aunque el evaluador marque
  un error.
- **Capa 3** jamás recibe un score crudo sin la decisión de la capa 2.

## 3. Puerto

```python
from typing import Protocol

class PronunciationEvaluator(Protocol):
    name: str          # "openpronounce" | "azure" | "speechace" | "elsa" | "gop" | "fake"
    version: str       # versión del motor, no del contrato

    async def evaluate(
        self,
        *,
        audio: AudioRef,
        expected_text: str,
        language: str = "en-US",
        context: EvaluationContext | None = None,
    ) -> PronunciationResult:
        ...
```

### 3.1 Entradas

```python
from pydantic import BaseModel, Field

class AudioRef(BaseModel):
    storage_key: str = Field(min_length=1)   # objeto en MinIO
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    duration_ms: int = Field(gt=0, le=60_000)
    mime: str = "audio/webm;codecs=opus"

class EvaluationContext(BaseModel):
    cefr: str | None = None                 # A1..C1
    lesson_id: str | None = None
    exercise_id: str | None = None
    focus_phonemes: list[str] = []          # p. ej. ["θ", "ð", "ɪ", "ɹ"]
    attempt_no: int = 1
    locale: str = "es-MX"                   # L1 del alumno (para sesgos conocidos)
```

### 3.2 Salida normalizada

```python
from enum import Enum

class Status(str, Enum):
    COMPLETED = "completed"
    PENDING = "pending"        # en cola / procesamiento asíncrono
    DISABLED = "disabled"      # flag off o motor no habilitado
    FAILED = "failed"          # error del motor (no del alumno)

class Reliability(str, Enum):
    VALIDATED = "validated"        # pasó el gate §13.5
    EXPERIMENTAL = "experimental"  # útil para investigación, no para el alumno
    UNVALIDATED = "unvalidated"    # sin evidencia; nunca se muestra

class WordStatus(str, Enum):
    OK = "ok"
    MISPRONOUNCED = "mispronounced"
    OMITTED = "omitted"
    UNINTELLIGIBLE = "unintelligible"
    UNKNOWN = "unknown"            # el motor no pudo decidir

class ErrorType(str, Enum):
    SUBSTITUTION = "substitution"
    OMISSION = "omission"
    INSERTION = "insertion"
    DISTORTION = "distortion"

class EngineInfo(BaseModel):
    name: str
    version: str
    mode: str                        # local | remote

class Overall(BaseModel):
    score: float | None = None       # 0-100; None si no validado
    scale: str = "0-100"
    confidence: float | None = None  # 0-1
    reliability: Reliability = Reliability.UNVALIDATED

class PhonemeError(BaseModel):
    ipa: str
    actual: str | None = None
    error_type: ErrorType
    start_ms: int | None = None
    end_ms: int | None = None
    severity: str | None = None      # low | medium | high

class WordResult(BaseModel):
    index: int
    word: str
    expected_ipa: str | None = None
    actual_ipa: str | None = None
    status: WordStatus = WordStatus.UNKNOWN
    confidence: float | None = None
    phonemes: list[PhonemeError] = []

class Evidence(BaseModel):
    per: float | None = None
    wer: float | None = None
    raw: dict | None = None          # solo para depuración interna, nunca a UI

class PronunciationResult(BaseModel):
    schema_version: str = "1.0"
    status: Status
    engine: EngineInfo
    overall: Overall
    words: list[WordResult] = []
    phonemes: list[PhonemeError] = []
    evidence: Evidence = Evidence()
    latency_ms: int = 0
    cost_usd: float = 0.0
    error: str | None = None         # código legible si status=failed
```

## 4. Invariantes

El motor y los adaptadores deben garantizar:

1. `schema_version` es `"1.0"` mientras el contrato no cambie de versión.
2. `status=disabled` ⇒ `overall.score=None` y `reliability=unvalidated`.
3. `reliability != validated` ⇒ `overall.score=None` en la respuesta que llega
   a la capa 2 (el adaptador puede conservar el score interno en `evidence`).
4. `status=failed` ⇒ `error` no nulo y **cero** impacto en `exercise_attempts`.
5. `words[].index` es creciente y cubre las palabras evaluables del texto.
6. `phonemes[].start_ms <= end_ms` cuando ambos existen.
7. `latency_ms` se mide dentro del adaptador; `cost_usd` es estimado.
8. Nunca se registra el audio ni el texto completo en logs.

> Nota: en F1 el `FakeEvaluator` cumple las invariantes devolviendo siempre
> `disabled`; las demás ramas se prueban con fixtures.

## 5. Estados y semántica de producto

| `status` | Significado | UI |
|---|---|---|
| `disabled` | Flag off o motor no habilitado | «Práctica libre» sin puntaje |
| `pending` | En cola / proceso asíncrono | «Procesando…» (sin bloquear) |
| `completed` + `validated` | Evaluación usable | Retroalimentación autorizada |
| `completed` + `experimental` | Solo investigación | No se muestra al alumno |
| `failed` | Error técnico | «No pudimos evaluar; tu intento se guardó» |

`failed` **no** es un error del alumno. No descuenta progreso ni racha.

## 6. Adaptadores

| Motor | Modo | Uso | Estado |
|---|---|---|---|
| `fake` | local | F1, tests, flag off | Implementado |
| `openpronounce` | local | Referencia de investigación | F0b |
| `gop` | local | Segunda prioridad / spike | F0b |
| `azure` | remoto | Candidato comercial | F0b (credenciales pendientes) |
| `speechace` | remoto | Candidato comercial | F0b (credenciales pendientes) |
| `elsa` | remoto | Condicionado a acceso comercial | F0b |

### 6.1 Reglas por adaptador

- Cada adaptador traduce su respuesta al modelo normalizado; **no** expone JSON
  del proveedor hacia arriba.
- Cada adaptador declara `name`, `version`, `mode` y su `reliability` base.
- Los adaptadores remotos exigen consentimiento `third_party_processing`
  vigente. Sin él, devuelven `status=disabled` con `error="consent_required"`.
- Los adaptadores locales pueden operar con audio real bajo consentimiento
  `recording` únicamente.

## 7. `FakeEvaluator`

```python
class FakeEvaluator:
    name = "fake"
    version = "1.0.0"

    async def evaluate(self, *, audio, expected_text, language="en-US", context=None):
        return PronunciationResult(
            status=Status.DISABLED,
            engine=EngineInfo(name=self.name, version=self.version, mode="local"),
            overall=Overall(score=None, confidence=None,
                            reliability=Reliability.UNVALIDATED),
        )
```

Selección por configuración:

```python
def build_evaluator(settings) -> PronunciationEvaluator:
    if not settings.pronunciation_eval_enabled:
        return FakeEvaluator()
    return ADAPTERS[settings.pronunciation_eval_engine]()
```

## 8. Contract tests

Obligatorios en CI. Deben correr sin red y sin GPU.

| # | Caso | Esperado |
|---|---|---|
| 1 | Flag off | `status=disabled`, `score=None` |
| 2 | Motor no disponible | `status=failed`, `error` no nulo |
| 3 | Resultado válido | `status=completed`, invariantes 1–6 |
| 4 | Score con `reliability=unvalidated` | se anula antes de la capa 2 |
| 5 | Texto vacío | error de validación (no excepción no controlada) |
| 6 | Audio > 60 s | error de validación |
| 7 | `sha256` inválido | error de validación |
| 8 | Timeout del adaptador | `status=failed` en ≤ presupuesto |
| 9 | Serialización | JSON válido contra `schema/pronunciation-result-1.0.json` |
| 10 | Determinismo | mismo fixture ⇒ mismo resultado normalizado |

Ejemplo mínimo:

```python
@pytest.mark.asyncio
async def test_flag_off_returns_disabled():
    result = await FakeEvaluator().evaluate(
        audio=AudioRef(storage_key="x", sha256="a"*64, duration_ms=1200),
        expected_text="three",
    )
    assert result.status is Status.DISABLED
    assert result.overall.score is None
    assert result.overall.reliability is Reliability.UNVALIDATED
```

## 9. Errores, timeouts y reintentos

- Presupuesto: 1.5 s local / 2.5 s remoto (p95). Timeout duro: 4 s.
- Reintentos: máximo 1, solo en errores de red/5xx; nunca en 4xx de validación.
- Errores del motor se mapean a `status=failed` con código estable:
  `timeout`, `unavailable`, `invalid_response`, `consent_required`, `quota`.
- Un `failed` no bloquea la lección: el intento educativo ya está guardado.

## 10. Persistencia

Cada evaluación se registra en `pronunciation_attempts` con:

| Campo | Origen |
|---|---|
| `evaluator` | `engine.name` |
| `engine_version` | `engine.version` |
| `status` | `status` |
| `confidence` | `overall.confidence` |
| `reliability` | `overall.reliability` |
| `result_json` | resultado normalizado completo (sin `evidence.raw` si contiene datos personales) |
| `latency_ms`, `cost_usd` | medidos |
| `audio_sha256` | `audio.sha256` |
| `schema_version` | `"1.0"` |

Reproducibilidad: con `audio_sha256 + engine + version + schema_version` se puede
repetir la evaluación y auditar decisiones.

## 11. Versionado

- **Patch** (`1.0.x`): campos opcionales nuevos, sin romper consumidores.
- **Minor** (`1.x.0`): semántica nueva compatible (p. ej. nuevo `WordStatus`).
- **Major** (`2.0.0`): cambio incompatible; requiere migración de
  `result_json` y período de convivencia de adaptadores.

El contrato del puerto y el `schema_version` se mueven juntos. Un adaptador que
no pueda cumplir la versión vigente no se habilita.

## 12. Privacidad

- El evaluador solo recibe un `AudioRef`; el adaptador obtiene una URL firmada
  de vida corta.
- Antes de enviar audio a un proveedor externo se exige consentimiento
  `third_party_processing` **vigente** y distinto del de grabación.
- El texto esperado puede registrarse; el audio nunca en logs.
- Los resultados con `reliability=experimental` se almacenan para investigación
  con acceso restringido.

## 13. Preguntas abiertas (F0b)

1. ¿Qué motor alcanza el gate §13.5 con etiquetas humanas?
2. ¿El puntaje por palabra es suficiente o se necesita por fonema?
3. ¿Cómo se trata el sesgo contra el acento mexicano (L1 español)?
4. ¿Vale la pena GOP local frente a un proveedor externo por costo/latencia?
5. ¿Qué nivel de detalle entiende un alumno A1/A2 sin frustrarse?
