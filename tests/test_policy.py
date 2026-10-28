from app.config import PolicyConfig
from app.engine.policy import PolicyEngine

from app.models.assurance import (
    AssuranceResult,
)

from app.models.decision import (
    DecisionAction,
)


def make_assurance(
    score: float,
) -> AssuranceResult:
    return AssuranceResult(
        assurance_score=score,
        risk_score=round(
            1.0 - score,
            10,
        ),
        behavior_score=score,
        face_score=score,
        context_score=score,
    )


def test_strong_assurance_allows():
    policy = PolicyEngine()

    assurance = make_assurance(0.90)

    decision = policy.evaluate(
        assurance
    )

    assert (
        decision.action
        == DecisionAction.ALLOW
    )

    assert decision.assurance_score == 0.90

    assert decision.risk_score == 0.10


def test_allow_threshold_allows():
    policy = PolicyEngine()

    assurance = make_assurance(0.75)

    decision = policy.evaluate(
        assurance
    )

    assert (
        decision.action
        == DecisionAction.ALLOW
    )


def test_uncertain_assurance_requires_reverification():
    policy = PolicyEngine()

    assurance = make_assurance(0.60)

    decision = policy.evaluate(
        assurance
    )

    assert (
        decision.action
        == DecisionAction.REVERIFY
    )


def test_reverify_threshold_requires_reverification():
    policy = PolicyEngine()

    assurance = make_assurance(0.45)

    decision = policy.evaluate(
        assurance
    )

    assert (
        decision.action
        == DecisionAction.REVERIFY
    )


def test_low_assurance_locks():
    policy = PolicyEngine()

    assurance = make_assurance(0.20)

    decision = policy.evaluate(
        assurance
    )

    assert (
        decision.action
        == DecisionAction.LOCK
    )


def test_policy_preserves_signal_scores():
    policy = PolicyEngine()

    assurance = AssuranceResult(
        assurance_score=0.80,
        risk_score=0.20,
        behavior_score=0.75,
        face_score=0.90,
        context_score=0.85,
    )

    decision = policy.evaluate(
        assurance
    )

    assert decision.behavior_score == 0.75

    assert decision.face_score == 0.90

    assert decision.context_score == 0.85


def test_policy_preserves_assurance_and_risk_scores():
    policy = PolicyEngine()

    assurance = AssuranceResult(
        assurance_score=0.63,
        risk_score=0.37,
        behavior_score=0.70,
        face_score=0.55,
        context_score=0.80,
    )

    decision = policy.evaluate(
        assurance
    )

    assert decision.assurance_score == 0.63

    assert decision.risk_score == 0.37


def test_custom_policy_thresholds_are_respected():
    policy = PolicyEngine(
        PolicyConfig(
            allow_threshold=0.85,
            reverify_threshold=0.50,
            max_reverify_attempts=3,
        )
    )

    allow = policy.evaluate(
        make_assurance(0.85)
    )

    reverify = policy.evaluate(
        make_assurance(0.70)
    )

    lock = policy.evaluate(
        make_assurance(0.49)
    )

    assert (
        allow.action
        == DecisionAction.ALLOW
    )

    assert (
        reverify.action
        == DecisionAction.REVERIFY
    )

    assert (
        lock.action
        == DecisionAction.LOCK
    )


def test_failed_reverification_below_limit_does_not_lock():
    policy = PolicyEngine()

    assert (
        policy.should_lock_after_failed_reverification(
            0
        )
        is False
    )

    assert (
        policy.should_lock_after_failed_reverification(
            1
        )
        is False
    )

    assert (
        policy.should_lock_after_failed_reverification(
            2
        )
        is False
    )


def test_failed_reverification_at_limit_locks():
    policy = PolicyEngine()

    assert (
        policy.should_lock_after_failed_reverification(
            3
        )
        is True
    )


def test_failed_reverification_above_limit_locks():
    policy = PolicyEngine()

    assert (
        policy.should_lock_after_failed_reverification(
            4
        )
        is True
    )


def test_negative_reverification_count_is_rejected():
    policy = PolicyEngine()

    try:
        policy.should_lock_after_failed_reverification(
            -1
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Negative reverification count must "
            "raise ValueError."
        )