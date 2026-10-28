import pytest

from app.engine.fusion import (
    RiskFusionEngine,
)

from app.models.signals import (
    SignalResult,
    SignalStatus,
)


def signal(
    source: str,
    score: float,
    confidence: float = 1.0,
    quality: float = 1.0,
    status: SignalStatus = SignalStatus.CONSISTENT,
):
    return SignalResult(
        source=source,
        score=score,
        confidence=confidence,
        quality=quality,
        status=status,
    )


def test_single_signal_fusion():

    engine = RiskFusionEngine(
        behavior_weight=1.0,
        face_weight=0.0,
        context_weight=0.0,
    )

    result = engine.fuse(
        behavior=signal(
            "behavior",
            0.80,
        )
    )

    assert result.assurance_score == pytest.approx(
        0.80
    )

    assert result.risk_score == pytest.approx(
        0.20
    )


def test_confidence_and_quality_affect_score():

    engine = RiskFusionEngine(
        behavior_weight=1.0,
        face_weight=0.0,
        context_weight=0.0,
    )

    result = engine.fuse(
        behavior=signal(
            "behavior",
            score=1.0,
            confidence=0.8,
            quality=0.5,
        )
    )

    assert result.assurance_score == pytest.approx(
        0.40
    )


def test_unavailable_signal_is_ignored():

    engine = RiskFusionEngine(
        behavior_weight=0.6,
        face_weight=0.4,
        context_weight=0.0,
    )

    behavior = signal(
        "behavior",
        score=0.80,
    )

    face = signal(
        "face",
        score=0.0,
        confidence=0.0,
        quality=0.0,
        status=SignalStatus.UNAVAILABLE,
    )

    result = engine.fuse(
        behavior=behavior,
        face=face,
    )

    assert result.assurance_score == pytest.approx(
        0.80
    )


def test_weights_are_renormalized_when_signal_unavailable():

    engine = RiskFusionEngine(
        behavior_weight=0.6,
        face_weight=0.4,
        context_weight=0.0,
    )

    result = engine.fuse(
        behavior=signal(
            "behavior",
            0.50,
        ),
        face=signal(
            "face",
            0.0,
            confidence=0.0,
            quality=0.0,
            status=SignalStatus.UNAVAILABLE,
        ),
    )

    assert result.assurance_score == pytest.approx(
        0.50
    )


def test_multiple_signals_are_weighted():

    engine = RiskFusionEngine(
        behavior_weight=0.6,
        face_weight=0.25,
        context_weight=0.15,
    )

    result = engine.fuse(
        behavior=signal(
            "behavior",
            0.80,
        ),
        face=signal(
            "face",
            0.90,
        ),
        context=signal(
            "context",
            1.00,
        ),
    )

    expected = (
        0.80 * 0.60
        + 0.90 * 0.25
        + 1.00 * 0.15
    )

    assert result.assurance_score == pytest.approx(
        expected
    )


def test_zero_weights_are_rejected():

    with pytest.raises(ValueError):

        RiskFusionEngine(
            behavior_weight=0.0,
            face_weight=0.0,
            context_weight=0.0,
        )