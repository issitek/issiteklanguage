"""Catálogo de cursos, lecciones y finalización de lección."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..errors import AppError
from ..models import Course, Exercise, LearningEvent, Lesson, StudentProgress, User
from ..schemas import (
    CourseOut,
    ExerciseOut,
    LessonCompleteOut,
    LessonOut,
    LessonSummary,
)

router = APIRouter(tags=["courses"])


def _lesson_summary(lesson: Lesson) -> LessonSummary:
    return LessonSummary.model_validate(lesson)


def _course_out(db: Session, course: Course) -> CourseOut:
    lessons = db.scalars(
        select(Lesson)
        .where(Lesson.course_id == course.id, Lesson.published.is_(True))
        .order_by(Lesson.position)
    ).all()
    return CourseOut(
        id=course.id,
        slug=course.slug,
        title=course.title,
        level=course.level,
        description=course.description,
        lessons=[_lesson_summary(lesson) for lesson in lessons],
    )


@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[CourseOut]:
    courses = db.scalars(
        select(Course).where(Course.published.is_(True)).order_by(Course.level, Course.title)
    ).all()
    return [_course_out(db, course) for course in courses]


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CourseOut:
    course = db.get(Course, course_id)
    if course is None or not course.published:
        raise AppError(404, "course_not_found", "Curso no encontrado.")
    return _course_out(db, course)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(
    lesson_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonOut:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None or not lesson.published:
        raise AppError(404, "lesson_not_found", "Lección no encontrada.")

    exercises = db.scalars(
        select(Exercise)
        .where(Exercise.lesson_id == lesson.id, Exercise.published.is_(True))
        .order_by(Exercise.position)
    ).all()
    return LessonOut(
        id=lesson.id,
        course_id=lesson.course_id,
        slug=lesson.slug,
        title=lesson.title,
        description=lesson.description,
        position=lesson.position,
        exercises=[ExerciseOut.model_validate(exercise) for exercise in exercises],
    )


@router.post("/lessons/{lesson_id}/complete", response_model=LessonCompleteOut)
def complete_lesson(
    lesson_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LessonCompleteOut:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None or not lesson.published:
        raise AppError(404, "lesson_not_found", "Lección no encontrada.")

    now = datetime.now(timezone.utc)
    progress = db.get(StudentProgress, (user.id, lesson.id))
    if progress is None:
        progress = StudentProgress(
            user_id=user.id,
            lesson_id=lesson.id,
            status="completed",
            attempts=0,
            completed_at=now,
            last_attempt_at=now,
            updated_at=now,
        )
    else:
        progress.status = "completed"
        progress.completed_at = progress.completed_at or now
        progress.last_attempt_at = now
        progress.updated_at = now
    db.add(progress)
    db.add(
        LearningEvent(
            user_id=user.id,
            type="lesson.completed",
            payload={"lesson_id": str(lesson.id)},
        )
    )
    db.commit()
    return LessonCompleteOut(
        lesson_id=lesson.id, status=progress.status, completed_at=progress.completed_at or now
    )
