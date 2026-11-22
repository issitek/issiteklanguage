"""Validación del contenido A1 contra JSON Schema y reglas semánticas."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.content import CONTENT_DIR, SCHEMA, validate_lesson

LESSON_FILES = sorted(CONTENT_DIR.glob("*.json"))


def test_schema_es_valido():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("path", LESSON_FILES, ids=lambda path: path.name)
def test_leccion_cumple_schema(path: Path):
    lesson = json.loads(path.read_text(encoding="utf-8"))
    validate_lesson(lesson, path.name)


def test_contenido_a1_completo_y_sin_duplicados():
    lessons = [json.loads(path.read_text(encoding="utf-8")) for path in LESSON_FILES]
    assert len(lessons) == 10
    slugs = [lesson["slug"] for lesson in lessons]
    assert len(slugs) == len(set(slugs))

    exercises = [exercise for lesson in lessons for exercise in lesson["exercises"]]
    assert len(exercises) == 30
    for lesson in lessons:
        types = [exercise["type"] for exercise in lesson["exercises"]]
        assert types.count("listen_repeat") == 1, lesson["slug"]
        assert types.count("multiple_choice") == 1, lesson["slug"]
        assert types.count("translate") == 1, lesson["slug"]


def test_leccion_invalida_falla_con_mensaje_claro():
    lesson = json.loads(LESSON_FILES[0].read_text(encoding="utf-8"))
    invalid = copy.deepcopy(lesson)
    invalid["exercises"][1]["payload"]["answer"] = 99
    with pytest.raises(ValueError, match="opción múltiple"):
        validate_lesson(invalid, "prueba.json")


def test_leccion_sin_campo_requerido_falla():
    lesson = json.loads(LESSON_FILES[0].read_text(encoding="utf-8"))
    del lesson["title"]
    with pytest.raises(ValueError, match="Contenido inválido"):
        validate_lesson(lesson, "prueba.json")
