"""Esquemas pydantic de entrada/salida (contratos HTTP)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth / usuarios ----------


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    role: str
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)


# ---------- Cursos / lecciones ----------


class LessonSummary(ORMModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str
    position: int


class CourseOut(ORMModel):
    id: uuid.UUID
    slug: str
    title: str
    level: str
    description: str
    lessons: list[LessonSummary] = []


class ExerciseOut(ORMModel):
    id: uuid.UUID
    type: str
    prompt: str
    payload: dict[str, object]
    position: int


class LessonOut(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    slug: str
    title: str
    description: str
    position: int
    exercises: list[ExerciseOut] = []


# ---------- Intentos / progreso ----------


class AttemptIn(BaseModel):
    response: dict[str, object] = Field(default_factory=dict)
    hints_used: int = Field(default=0, ge=0, le=20)
    time_ms: int | None = Field(default=None, ge=0)
    recording_id: uuid.UUID | None = None


class AttemptOut(ORMModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    attempt_no: int
    score: float | None
    is_correct: bool | None
    created_at: datetime
    feedback: str | None = None


class ProgressItem(BaseModel):
    lesson_id: uuid.UUID
    lesson_title: str
    status: str
    score: float | None
    attempts: int
    completed_at: datetime | None


class ProgressOut(BaseModel):
    completed_lessons: int
    total_lessons: int
    attempts: int
    items: list[ProgressItem]
    pronunciation_eval_enabled: bool


class LessonCompleteOut(BaseModel):
    lesson_id: uuid.UUID
    status: str
    completed_at: datetime


# ---------- Consentimientos ----------

ConsentKind = Literal["recording", "third_party_processing", "parental"]


class ConsentIn(BaseModel):
    kind: ConsentKind
    version: str = "2026-11-01"
    granted: bool = True


class ConsentOut(BaseModel):
    kind: str
    version: str
    granted_at: datetime | None
    revoked_at: datetime | None
    active: bool


# ---------- Grabaciones / TTS ----------


class PresignIn(BaseModel):
    exercise_id: uuid.UUID | None = None
    duration_ms: int = Field(gt=0, le=60_000)
    mime: Literal[
        "audio/webm",
        "audio/webm;codecs=opus",
        "audio/wav",
        "audio/ogg",
        "audio/mp4",
    ] = "audio/webm;codecs=opus"


class PresignOut(BaseModel):
    recording_id: uuid.UUID
    url: str
    method: str = "PUT"
    headers: dict[str, str] = Field(default_factory=dict)
    expires_in: int


class CompleteIn(BaseModel):
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    bytes: int = Field(gt=0, le=10_000_000)


class RecordingOut(BaseModel):
    id: uuid.UUID
    url: str
    expires_in: int
    sha256: str | None
    duration_ms: int
    mime: str


class TtsOut(BaseModel):
    url: str
    duration_ms: int | None
    cached: bool
    provider: str
    expires_in: int


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
