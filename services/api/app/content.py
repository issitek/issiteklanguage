"""Validación del contenido de lecciones (JSON Schema + reglas semánticas)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "a1"
SCHEMA_PATH = CONTENT_DIR.parent / "lesson.schema.json"
SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)


def validate_lesson(data: dict[str, Any], source: str = "lección") -> None:
    """Lanza ValueError con un mensaje accionable si la lección no es válida."""
    errors = sorted(VALIDATOR.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or 'raíz'}: {error.message}"
            for error in errors[:5]
        )
        raise ValueError(f"Contenido inválido en {source}: {details}")

    for exercise in data["exercises"]:
        payload = exercise["payload"]
        if exercise["type"] == "multiple_choice":
            options = payload["options"]
            if payload["answer"] >= len(options):
                raise ValueError(
                    f"Contenido inválido en {source}: la respuesta de opción múltiple "
                    "apunta fuera de las opciones."
                )
            if len(options) != len(set(options)):
                raise ValueError(
                    f"Contenido inválido en {source}: hay opciones repetidas."
                )
        if exercise["type"] == "translate":
            answers = [str(answer).strip().casefold() for answer in payload["answers"]]
            if len(answers) != len(set(answers)) or not all(answers):
                raise ValueError(
                    f"Contenido inválido en {source}: respuestas de traducción "
                    "vacías o repetidas."
                )
