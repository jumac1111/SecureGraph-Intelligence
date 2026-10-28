from app.engine.identity_signals import (
    IdentitySignalsEngine,
)
from app.models.signals import (
    SignalStatus,
)


def test_verified_identity_produces_strong_signal():
    engine = IdentitySignalsEngine()

    signal = engine.evaluate(
        verified=True,
        confidence=1.0,
        quality=1.0,
    )

    assert signal.source == "identity"
    assert signal.score == 1.0
    assert signal.confidence == 1.0
    assert signal.quality == 1.0
    assert signal.status == SignalStatus.CONSISTENT
    assert signal.effective_score == 1.0


def test_identity_mismatch_produces_zero_signal():
    engine = IdentitySignalsEngine()

    signal = engine.evaluate(
        verified=False,
        confidence=1.0,
        quality=1.0,
    )

    assert signal.source == "identity"
    assert signal.score == 0.0
    assert signal.status == SignalStatus.MISMATCH
    assert signal.effective_score == 0.0


def test_unavailable_identity_does_not_create_negative_evidence():
    engine = IdentitySignalsEngine()

    signal = engine.evaluate(
        verified=None,
        confidence=1.0,
        quality=1.0,
    )

    assert signal.source == "identity"
    assert signal.score == 0.0
    assert signal.confidence == 0.0
    assert signal.status == SignalStatus.UNAVAILABLE
    assert signal.effective_score == 0.0


def test_identity_confidence_affects_effective_score():
    engine = IdentitySignalsEngine()

    signal = engine.evaluate(
        verified=True,
        confidence=0.5,
        quality=1.0,
    )

    assert signal.score == 1.0
    assert signal.confidence == 0.5
    assert signal.effective_score == 0.5


def test_identity_quality_affects_effective_score():
    engine = IdentitySignalsEngine()

    signal = engine.evaluate(
        verified=True,
        confidence=1.0,
        quality=0.4,
    )

    assert signal.score == 1.0
    assert signal.quality == 0.4
    assert signal.effective_score == 0.4


def test_identity_values_are_clamped():
    engine = IdentitySignalsEngine()

    signal = engine.evaluate(
        verified=True,
        confidence=5.0,
        quality=-5.0,
    )

    assert signal.confidence == 1.0
    assert signal.quality == 0.0
    assert signal.effective_score == 0.0


def test_identity_mismatch_remains_mismatch_with_low_confidence():
    engine = IdentitySignalsEngine()

    signal = engine.evaluate(
        verified=False,
        confidence=0.2,
        quality=0.8,
    )

    assert signal.status == SignalStatus.MISMATCH
    assert signal.score == 0.0
    assert signal.effective_score == 0.0