"""Selección del evaluador según configuración (feature flag)."""

from .base import PronunciationEvaluator
from .fake import FakeEvaluator


def build_evaluator(*, enabled: bool, engine: str) -> PronunciationEvaluator:
    if not enabled:
        return FakeEvaluator()
    if engine == "fake":
        return FakeEvaluator()
    # Los adaptadores reales llegan con F5b, solo si el gate §13.5 se aprueba.
    raise RuntimeError(f"Evaluador no implementado todavía: {engine}")
