"""Contract tests del evaluador de pronunciación (sin red ni GPU)."""

import pytest
from pydantic import ValidationError

from app.pronunciation.base import (
    AudioRef,
    EngineInfo,
    Overall,
    PronunciationResult,
    Reliability,
    Status,
)
from app.pronunciation.factory import build_evaluator
from app.pronunciation.fake import FakeEvaluator


def _audio() -> AudioRef:
    return AudioRef(storage_key="student/x.wav", sha256="a" * 64, duration_ms=1200)


async def test_flag_off_devuelve_disabled_sin_score():
    result = await FakeEvaluator().evaluate(audio=_audio(), expected_text="three")
    assert result.schema_version == "1.0"
    assert result.status is Status.DISABLED
    assert result.overall.score is None
    assert result.overall.confidence is None
    assert result.overall.reliability is Reliability.UNVALIDATED


def test_score_se_anula_sin_reliability_validated():
    result = PronunciationResult(
        status=Status.COMPLETED,
        engine=EngineInfo(name="x", version="1"),
        overall=Overall(score=90, confidence=0.9, reliability=Reliability.EXPERIMENTAL),
    )
    assert result.overall.score is None


def test_score_se_conserva_si_esta_validado():
    result = PronunciationResult(
        status=Status.COMPLETED,
        engine=EngineInfo(name="x", version="1"),
        overall=Overall(score=90, confidence=0.9, reliability=Reliability.VALIDATED),
    )
    assert result.overall.score == 90


def test_failed_exige_codigo_de_error():
    result = PronunciationResult(
        status=Status.FAILED,
        engine=EngineInfo(name="x", version="1"),
        overall=Overall(),
    )
    assert result.error == "evaluation_failed"
    assert result.overall.score is None


@pytest.mark.parametrize("sha256", ["", "no-es-un-hash", "A" * 64, "a" * 63])
def test_audioref_rechaza_hash_invalido(sha256):
    with pytest.raises(ValidationError):
        AudioRef(storage_key="x", sha256=sha256, duration_ms=1000)


def test_audioref_rechaza_duracion_fuera_de_rango():
    with pytest.raises(ValidationError):
        AudioRef(storage_key="x", sha256="a" * 64, duration_ms=0)
    with pytest.raises(ValidationError):
        AudioRef(storage_key="x", sha256="a" * 64, duration_ms=60_001)


def test_factory_flag_off_usa_fake():
    evaluator = build_evaluator(enabled=False, engine="azure")
    assert isinstance(evaluator, FakeEvaluator)


def test_factory_flag_on_con_motor_no_implementado_falla():
    with pytest.raises(RuntimeError):
        build_evaluator(enabled=True, engine="azure")
