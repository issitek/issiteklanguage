"""Contrato del evaluador de pronunciación (puerto y resultado normalizado 1.0)."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


class Status(str, Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    DISABLED = "disabled"
    FAILED = "failed"


class Reliability(str, Enum):
    VALIDATED = "validated"
    EXPERIMENTAL = "experimental"
    UNVALIDATED = "unvalidated"


class WordStatus(str, Enum):
    OK = "ok"
    MISPRONOUNCED = "mispronounced"
    OMITTED = "omitted"
    UNINTELLIGIBLE = "unintelligible"
    UNKNOWN = "unknown"


class ErrorType(str, Enum):
    SUBSTITUTION = "substitution"
    OMISSION = "omission"
    INSERTION = "insertion"
    DISTORTION = "distortion"


class AudioRef(BaseModel):
    storage_key: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    duration_ms: int = Field(gt=0, le=60_000)
    mime: str = "audio/webm;codecs=opus"


class EvaluationContext(BaseModel):
    cefr: str | None = None
    lesson_id: str | None = None
    exercise_id: str | None = None
    focus_phonemes: list[str] = Field(default_factory=list)
    attempt_no: int = 1
    locale: str = "es-MX"


class EngineInfo(BaseModel):
    name: str
    version: str
    mode: str = "local"


class Overall(BaseModel):
    score: float | None = Field(default=None, ge=0, le=100)
    scale: str = "0-100"
    confidence: float | None = Field(default=None, ge=0, le=1)
    reliability: Reliability = Reliability.UNVALIDATED


class PhonemeError(BaseModel):
    ipa: str
    actual: str | None = None
    error_type: ErrorType
    start_ms: int | None = None
    end_ms: int | None = None
    severity: str | None = None


class WordResult(BaseModel):
    index: int = Field(ge=0)
    word: str
    expected_ipa: str | None = None
    actual_ipa: str | None = None
    status: WordStatus = WordStatus.UNKNOWN
    confidence: float | None = Field(default=None, ge=0, le=1)
    phonemes: list[PhonemeError] = Field(default_factory=list)


class Evidence(BaseModel):
    per: float | None = None
    wer: float | None = None
    raw: dict | None = None


class PronunciationResult(BaseModel):
    schema_version: str = "1.0"
    status: Status
    engine: EngineInfo
    overall: Overall
    words: list[WordResult] = Field(default_factory=list)
    phonemes: list[PhonemeError] = Field(default_factory=list)
    evidence: Evidence = Field(default_factory=Evidence)
    latency_ms: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def _enforce_reliability(self) -> "PronunciationResult":
        """Invariante: sin validación no se expone un score al alumno."""
        if self.overall.reliability is not Reliability.VALIDATED:
            self.overall.score = None
        if self.status in (Status.DISABLED, Status.PENDING, Status.FAILED):
            self.overall.score = None
            self.overall.confidence = None
        if self.status is Status.FAILED and not self.error:
            self.error = "evaluation_failed"
        return self


class PronunciationEvaluator(Protocol):
    name: str
    version: str

    async def evaluate(
        self,
        *,
        audio: AudioRef,
        expected_text: str,
        language: str = "en-US",
        context: EvaluationContext | None = None,
    ) -> PronunciationResult: ...
