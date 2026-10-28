from datetime import datetime, timedelta, timezone

import pytest

from app.config import BehavioralConfig
from app.engine.behavior_learning import (
    BehavioralLearningEngine,
)
from app.engine.behavior_signals import (
    BehavioralSignalsEngine,
)
from app.models.profile import (
    FeatureStatistics,
    UserProfile,
)
from app.models.signals import (
    BehaviorObservation,
    SignalStatus,
)


def established_profile():
    profile = UserProfile(
        user_id="researcher",
        state="established",
        observation_count=50,
        required_observations=50,
    )

    profile.features = {
        "typing_speed": FeatureStatistics(
            count=50,
            mean=1.2,
            variance=0.01,
        ),
        "mouse_speed": FeatureStatistics(
            count=50,
            mean=20.0,
            variance=4.0,
        ),
        "click_interval": FeatureStatistics(
            count=50,
            mean=38.0,
            variance=4.0,
        ),
    }

    return profile


def test_exact_match_produces_strong_signal():

    engine = BehavioralSignalsEngine()

    profile = established_profile()

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
        click_interval=38.0,
    )

    signal = engine.evaluate(
        profile,
        observation,
    )

    assert signal.score >= 0.95

    assert signal.confidence > 0.75

    assert signal.quality > 0.75

    assert (
        signal.status
        == SignalStatus.CONSISTENT
    )


def test_large_deviation_produces_mismatch():

    engine = BehavioralSignalsEngine()

    profile = established_profile()

    observation = BehaviorObservation(
        typing_speed=5.0,
        mouse_speed=100.0,
        click_interval=2.0,
    )

    signal = engine.evaluate(
        profile,
        observation,
    )

    assert signal.score < 0.45

    assert (
        signal.status
        == SignalStatus.MISMATCH
    )


def test_missing_observation_is_not_trusted():

    engine = BehavioralSignalsEngine()

    profile = established_profile()

    observation = BehaviorObservation()

    signal = engine.evaluate(
        profile,
        observation,
    )

    assert (
        signal.status
        == SignalStatus.UNAVAILABLE
    )

    assert signal.confidence == 0.0

    assert signal.quality == 0.0


def test_unknown_feature_does_not_create_confidence():

    engine = BehavioralSignalsEngine()

    profile = established_profile()

    observation = BehaviorObservation(
        navigation_interval=2.0,
    )

    signal = engine.evaluate(
        profile,
        observation,
    )

    assert (
        signal.status
        == SignalStatus.UNCERTAIN
    )

    assert signal.confidence <= 0.30


def test_learning_engine_rejects_extreme_poisoning():

    config = BehavioralConfig(
        required_observations=5,
        maximum_update_z_score=4.0,
    )

    learner = BehavioralLearningEngine(
        behavioral_config=config,
    )

    profile = UserProfile(
        user_id="researcher",
        required_observations=5,
    )

    normal = BehaviorObservation(
        typing_speed=1.2,
    )

    for _ in range(5):
        learner.update_profile(
            profile,
            normal,
        )

    statistics = profile.features[
        "typing_speed"
    ]

    original_mean = statistics.mean

    poisoned = BehaviorObservation(
        typing_speed=1000000.0,
    )

    learner.update_profile(
        profile,
        poisoned,
    )

    assert (
        profile.features[
            "typing_speed"
        ].mean
        == pytest.approx(
            original_mean
        )
    )


def test_learning_is_incremental():

    learner = BehavioralLearningEngine(
        required_observations=3,
    )

    profile = UserProfile(
        user_id="researcher",
    )

    observations = [
        BehaviorObservation(
            typing_speed=1.0,
        ),
        BehaviorObservation(
            typing_speed=2.0,
        ),
        BehaviorObservation(
            typing_speed=3.0,
        ),
    ]

    for observation in observations:
        learner.update_profile(
            profile,
            observation,
        )

    statistics = profile.features[
        "typing_speed"
    ]

    assert statistics.count == 3

    assert statistics.mean == pytest.approx(
        2.0
    )

    assert statistics.variance == pytest.approx(
        2.0 / 3.0
    )

    assert profile.state == "established"


def test_temporal_gap_does_not_create_false_confidence():

    engine = BehavioralSignalsEngine()

    profile = established_profile()

    profile.last_behavior_observation_at = (
        datetime.now(timezone.utc)
        - timedelta(
            seconds=300
        )
    )

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
        click_interval=38.0,
    )

    signal = engine.evaluate(
        profile,
        observation,
    )

    assert 0.0 <= signal.score <= 1.0

    assert 0.0 <= signal.confidence <= 1.0

    assert 0.0 <= signal.quality <= 1.0


def test_scores_are_always_bounded():

    engine = BehavioralSignalsEngine()

    profile = established_profile()

    observation = BehaviorObservation(
        typing_speed=-999999.0,
        mouse_speed=999999.0,
        click_interval=-999999.0,
    )

    signal = engine.evaluate(
        profile,
        observation,
    )

    assert 0.0 <= signal.score <= 1.0

    assert 0.0 <= signal.confidence <= 1.0

    assert 0.0 <= signal.quality <= 1.0