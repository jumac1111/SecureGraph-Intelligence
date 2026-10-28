import pytest

from app.config import (
    AssuranceConfig,
    PolicyConfig,
)


def test_default_assurance_weights_sum_to_one():

    config = AssuranceConfig()

    total = (
        config.behavior_weight
        + config.face_weight
        + config.context_weight
    )

    assert total == pytest.approx(1.0)


def test_invalid_assurance_weights_are_rejected():

    with pytest.raises(ValueError):

        AssuranceConfig(
            behavior_weight=0.50,
            face_weight=0.50,
            context_weight=0.50,
        )


def test_policy_thresholds_are_valid():

    config = PolicyConfig()

    assert (
        config.reverify_threshold
        < config.allow_threshold
    )

    assert (
        config.max_reverify_attempts
        >= 1
    )


def test_invalid_policy_thresholds_are_rejected():

    with pytest.raises(ValueError):

        PolicyConfig(
            allow_threshold=0.40,
            reverify_threshold=0.50,
        )