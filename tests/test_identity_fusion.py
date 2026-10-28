from app.engine.fusion import RiskFusionEngine
from app.models.signals import (
    SignalResult,
    SignalStatus,
)


def test_identity_signal_can_participate_in_fusion():
    engine = RiskFusionEngine(
        behavior_weight=0.50,
        identity_weight=0.20,
        face_weight=0.20,
        context_weight=0.10,
    )

    behavior = SignalResult(
        source="behavior",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    identity = SignalResult(
        source="identity",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    face = SignalResult(
        source="face",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    context = SignalResult(
        source="context",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    result = engine.fuse(
        behavior=behavior,
        identity=identity,
        face=face,
        context=context,
    )

    assert result.assurance_score == 1.0
    assert result.risk_score == 0.0


def test_identity_mismatch_reduces_assurance():
    engine = RiskFusionEngine(
        behavior_weight=0.50,
        identity_weight=0.20,
        face_weight=0.20,
        context_weight=0.10,
    )

    behavior = SignalResult(
        source="behavior",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    identity = SignalResult(
        source="identity",
        score=0.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.MISMATCH,
    )

    face = SignalResult(
        source="face",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    context = SignalResult(
        source="context",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    result = engine.fuse(
        behavior=behavior,
        identity=identity,
        face=face,
        context=context,
    )

    assert result.assurance_score == 0.80
    assert result.risk_score == 0.20


def test_unavailable_identity_is_renormalized():
    engine = RiskFusionEngine(
        behavior_weight=0.50,
        identity_weight=0.20,
        face_weight=0.20,
        context_weight=0.10,
    )

    behavior = SignalResult(
        source="behavior",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    identity = SignalResult(
        source="identity",
        score=0.0,
        confidence=0.0,
        quality=0.0,
        status=SignalStatus.UNAVAILABLE,
    )

    face = SignalResult(
        source="face",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    context = SignalResult(
        source="context",
        score=1.0,
        confidence=1.0,
        quality=1.0,
        status=SignalStatus.CONSISTENT,
    )

    result = engine.fuse(
        behavior=behavior,
        identity=identity,
        face=face,
        context=context,
    )

    assert result.assurance_score == 1.0
    assert result.risk_score == 0.0