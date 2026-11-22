"""Evaluador falso: F1 y pruebas. Siempre desactivado, nunca puntúa."""

from .base import (
    AudioRef,
    EngineInfo,
    EvaluationContext,
    Overall,
    PronunciationResult,
    Reliability,
    Status,
)


class FakeEvaluator:
    name = "fake"
    version = "1.0.0"

    async def evaluate(
        self,
        *,
        audio: AudioRef,
        expected_text: str,
        language: str = "en-US",
        context: EvaluationContext | None = None,
    ) -> PronunciationResult:
        return PronunciationResult(
            status=Status.DISABLED,
            engine=EngineInfo(name=self.name, version=self.version, mode="local"),
            overall=Overall(
                score=None,
                confidence=None,
                reliability=Reliability.UNVALIDATED,
            ),
        )
