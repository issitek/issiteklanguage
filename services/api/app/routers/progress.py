"""Progreso agregado del alumno."""

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user
from ..models import Lesson, StudentProgress, User
from ..schemas import ProgressItem, ProgressOut

router = APIRouter(prefix="/me", tags=["progress"])


@router.get("/progress", response_model=ProgressOut)
def my_progress(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProgressOut:
    rows = db.execute(
        select(Lesson, StudentProgress)
        .outerjoin(
            StudentProgress,
            and_(
                StudentProgress.lesson_id == Lesson.id,
                StudentProgress.user_id == user.id,
            ),
        )
        .where(Lesson.published.is_(True))
        .order_by(Lesson.position)
    ).all()

    items: list[ProgressItem] = []
    completed = 0
    attempts = 0
    for lesson, progress in rows:
        status = progress.status if progress else "not_started"
        if status == "completed":
            completed += 1
        if progress:
            attempts += progress.attempts
        items.append(
            ProgressItem(
                lesson_id=lesson.id,
                lesson_title=lesson.title,
                status=status,
                score=float(progress.score) if progress and progress.score is not None else None,
                attempts=progress.attempts if progress else 0,
                completed_at=progress.completed_at if progress else None,
            )
        )

    settings = get_settings()
    return ProgressOut(
        completed_lessons=completed,
        total_lessons=len(items),
        attempts=attempts,
        items=items,
        pronunciation_eval_enabled=settings.pronunciation_eval_enabled,
    )
