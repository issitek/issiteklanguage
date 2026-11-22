"""Intentos educativos, progreso por lección e historial."""

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..errors import AppError
from ..models import (
    Exercise,
    ExerciseAttempt,
    LearningEvent,
    SpeechAsset,
    StudentProgress,
    User,
)
from ..schemas import AttemptIn, AttemptOut

router = APIRouter(tags=["attempts"])


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s']", "", text.lower()).strip()


def _evaluate(exercise: Exercise, response: dict) -> tuple[float | None, bool | None, str | None]:
    payload = exercise.payload or {}

    if exercise.type == "multiple_choice":
        try:
            given = int(response.get("answer"))
            expected = int(payload.get("answer"))
        except (TypeError, ValueError):
            return 0.0, False, "Elige una opción."
        ok = given == expected
        return (100.0 if ok else 0.0), ok, payload.get("hint") if not ok else "¡Muy bien!"

    if exercise.type in {"translate", "fill_blank", "short_answer"}:
        answers = payload.get("answers") or [payload.get("answer")]
        candidates = {_normalize(str(a)) for a in answers if a}
        given = _normalize(str(response.get("text", "")))
        ok = bool(given) and given in candidates
        return (100.0 if ok else 0.0), ok, payload.get("hint") if not ok else "¡Muy bien!"

    if exercise.type == "listen_repeat":
        # Práctica libre: no hay puntaje fonético en F1.
        return None, None, "Práctica libre: escucha, repite y compara tu grabación."

    return None, None, None


def _validate_recording(db: Session, user: User, recording_id: uuid.UUID) -> SpeechAsset:
    asset = db.get(SpeechAsset, recording_id)
    if (
        asset is None
        or asset.user_id != user.id
        or asset.deleted_at is not None
        or asset.sha256 is None
    ):
        raise AppError(422, "recording_invalid", "La grabación no existe o no está completa.")
    return asset


@router.post("/exercises/{exercise_id}/attempts", response_model=AttemptOut)
def submit_attempt(
    exercise_id: uuid.UUID,
    payload: AttemptIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptOut:
    exercise = db.get(Exercise, exercise_id)
    if exercise is None or not exercise.published:
        raise AppError(404, "exercise_not_found", "Ejercicio no encontrado.")

    if payload.recording_id is not None:
        _validate_recording(db, user, payload.recording_id)

    response = dict(payload.response)
    if payload.recording_id is not None:
        response["recording_id"] = str(payload.recording_id)

    score, is_correct, feedback = _evaluate(exercise, response)

    last_no = db.scalar(
        select(func.max(ExerciseAttempt.attempt_no)).where(
            ExerciseAttempt.user_id == user.id,
            ExerciseAttempt.exercise_id == exercise.id,
        )
    )
    attempt_no = (last_no or 0) + 1
    now = datetime.now(timezone.utc)

    attempt = ExerciseAttempt(
        user_id=user.id,
        exercise_id=exercise.id,
        attempt_no=attempt_no,
        response=response,
        score=score,
        is_correct=is_correct,
        hints_used=payload.hints_used,
        time_ms=payload.time_ms,
        created_at=now,
    )
    db.add(attempt)

    progress = db.get(StudentProgress, (user.id, exercise.lesson_id))
    if progress is None:
        progress = StudentProgress(
            user_id=user.id,
            lesson_id=exercise.lesson_id,
            status="in_progress",
            score=score,
            attempts=1,
            last_attempt_at=now,
            updated_at=now,
        )
    else:
        progress.attempts += 1
        progress.last_attempt_at = now
        progress.updated_at = now
        if progress.status != "completed":
            progress.status = "in_progress"
        if score is not None:
            progress.score = max(float(progress.score or 0), score)
    db.add(progress)

    db.add(
        LearningEvent(
            user_id=user.id,
            type="exercise.attempt",
            payload={
                "exercise_id": str(exercise.id),
                "lesson_id": str(exercise.lesson_id),
                "score": score,
                "is_correct": is_correct,
                "attempt_no": attempt_no,
            },
        )
    )
    db.commit()
    db.refresh(attempt)

    return AttemptOut(
        id=attempt.id,
        exercise_id=attempt.exercise_id,
        attempt_no=attempt.attempt_no,
        score=float(attempt.score) if attempt.score is not None else None,
        is_correct=attempt.is_correct,
        created_at=attempt.created_at,
        feedback=feedback,
    )


@router.get("/exercises/{exercise_id}/attempts", response_model=list[AttemptOut])
def list_attempts(
    exercise_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AttemptOut]:
    attempts = db.scalars(
        select(ExerciseAttempt)
        .where(
            ExerciseAttempt.user_id == user.id,
            ExerciseAttempt.exercise_id == exercise_id,
        )
        .order_by(ExerciseAttempt.attempt_no.desc())
    ).all()
    return [
        AttemptOut(
            id=a.id,
            exercise_id=a.exercise_id,
            attempt_no=a.attempt_no,
            score=float(a.score) if a.score is not None else None,
            is_correct=a.is_correct,
            created_at=a.created_at,
        )
        for a in attempts
    ]


@router.get("/me/history", response_model=list[AttemptOut])
def my_history(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[AttemptOut]:
    attempts = db.scalars(
        select(ExerciseAttempt)
        .where(ExerciseAttempt.user_id == user.id)
        .order_by(ExerciseAttempt.created_at.desc())
        .limit(50)
    ).all()
    return [
        AttemptOut(
            id=a.id,
            exercise_id=a.exercise_id,
            attempt_no=a.attempt_no,
            score=float(a.score) if a.score is not None else None,
            is_correct=a.is_correct,
            created_at=a.created_at,
        )
        for a in attempts
    ]
