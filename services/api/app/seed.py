"""Seed idempotente del curso A1 (10 lecciones en borrador)."""

import json
from pathlib import Path

from sqlalchemy import select

from .db import SessionLocal
from .models import Course, Exercise, Lesson

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "a1"
COURSE_SLUG = "a1-english"


def seed_content() -> int:
    with SessionLocal() as db:
        course = db.scalars(select(Course).where(Course.slug == COURSE_SLUG)).first()
        if course is None:
            course = Course(
                slug=COURSE_SLUG,
                title="English A1 — Primeros pasos",
                level="A1",
                description="Curso inicial: saludos, presentaciones, números y vida diaria.",
                published=True,
            )
            db.add(course)
            db.flush()

        files = sorted(CONTENT_DIR.glob("*.json"))
        for lesson_pos, path in enumerate(files):
            data = json.loads(path.read_text(encoding="utf-8"))
            lesson = db.scalars(
                select(Lesson).where(
                    Lesson.course_id == course.id, Lesson.slug == data["slug"]
                )
            ).first()
            if lesson is None:
                lesson = Lesson(course_id=course.id, slug=data["slug"])
                db.add(lesson)
            lesson.title = data["title"]
            lesson.description = data.get("description", "")
            lesson.position = lesson_pos
            lesson.published = True
            db.flush()

            exercises = data.get("exercises", [])
            for exercise_pos, exercise in enumerate(exercises):
                row = db.scalars(
                    select(Exercise).where(
                        Exercise.lesson_id == lesson.id, Exercise.position == exercise_pos
                    )
                ).first()
                if row is None:
                    row = Exercise(lesson_id=lesson.id, position=exercise_pos)
                    db.add(row)
                row.type = exercise["type"]
                row.prompt = exercise["prompt"]
                row.payload = exercise.get("payload", {})
                row.published = True

            for extra in db.scalars(
                select(Exercise).where(
                    Exercise.lesson_id == lesson.id,
                    Exercise.position >= len(exercises),
                )
            ).all():
                extra.published = False

        db.commit()
        return len(files)


if __name__ == "__main__":
    total = seed_content()
    print(f"Seed A1 listo: {total} lecciones.")
