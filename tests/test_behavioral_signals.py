import math

import pytest

from app.engine.behavioral_signals import (
    BehavioralSignalsEngine,
)

from app.models.signals import (
    BehaviorObservation,
    SignalStatus,
)


def test_build_observation_creates_numeric_observation():

    engine = BehavioralSignalsEngine()

    observation = engine.build_observation(
        typing_speed=1.2,
        mouse_speed=20.0,
        click_interval=38.0,
    )

    assert (
        observation.typing_speed
        == 1.2
    )

    assert (
        observation.mouse_speed
        == 20.0
    )

    assert (
        observation.click_interval
        == 38.0
    )


def test_build_observation_discards_nan():

    engine = BehavioralSignalsEngine()

    observation = engine.build_observation(
        typing_speed=math.nan,
        mouse_speed=20.0,
    )

    assert (
        observation.typing_speed
        is None
    )

    assert (
        observation.mouse_speed
        == 20.0
    )


def test_build_observation_discards_infinity():

    engine = BehavioralSignalsEngine()

    observation = engine.build_observation(
        typing_speed=math.inf,
        mouse_speed=20.0,
    )

    assert (
        observation.typing_speed
        is None
    )

    assert (
        observation.mouse_speed
        == 20.0
    )


def test_build_observation_discards_negative_values():

    engine = BehavioralSignalsEngine()

    observation = engine.build_observation(
        typing_speed=-1.0,
        mouse_speed=20.0,
    )

    assert (
        observation.typing_speed
        is None
    )

    assert (
        observation.mouse_speed
        == 20.0
    )


def test_feature_count():

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
        click_interval=38.0,
    )

    assert (
        observation.feature_count
        == 3
    )


def test_completeness():

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
    )

    assert (
        observation.completeness
        == pytest.approx(0.4)
    )


def test_quality_matches_feature_completeness():

    engine = BehavioralSignalsEngine()

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
    )

    quality = engine.calculate_quality(
        observation
    )

    assert quality == pytest.approx(
        0.4
    )


def test_generate_signal_with_no_features_is_unavailable():

    engine = BehavioralSignalsEngine()

    observation = BehaviorObservation()

    signal = engine.generate(
        observation
    )

    assert (
        signal.status
        == SignalStatus.UNAVAILABLE
    )

    assert (
        signal.confidence
        == 0.0
    )


def test_generate_signal_with_features():

    engine = BehavioralSignalsEngine()

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
        click_interval=38.0,
    )

    signal = engine.generate(
        observation
    )

    assert (
        signal.status
        == SignalStatus.CONSISTENT
    )

    assert (
        signal.score
        == 1.0
    )

    assert (
        signal.quality
        == pytest.approx(0.6)
    )


def test_extract_features_returns_only_available_values():

    engine = BehavioralSignalsEngine()

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
        click_interval=None,
    )

    features = engine.extract_features(
        observation
    )

    assert features == {
        "typing_speed": 1.2,
        "mouse_speed": 20.0,
    }


def test_from_mapping():

    engine = BehavioralSignalsEngine()

    observation = engine.from_mapping(
        {
            "typing_speed": 1.2,
            "mouse_speed": 20.0,
            "click_interval": 38.0,
            "unknown_field": 999.0,
        }
    )

    assert (
        observation.typing_speed
        == 1.2
    )

    assert (
        observation.mouse_speed
        == 20.0
    )

    assert (
        observation.click_interval
        == 38.0
    )

    assert (
        not hasattr(
            observation,
            "unknown_field",
        )
    )


def test_custom_minimum_features():

    engine = BehavioralSignalsEngine(
        minimum_features=3
    )

    observation = BehaviorObservation(
        typing_speed=1.2,
        mouse_speed=20.0,
    )

    signal = engine.generate(
        observation
    )

    assert (
        signal.status
        == SignalStatus.UNAVAILABLE
    )


def test_invalid_minimum_features():

    with pytest.raises(
        ValueError
    ):

        BehavioralSignalsEngine(
            minimum_features=0
        )


def test_minimum_features_cannot_exceed_supported_features():

    with pytest.raises(
        ValueError
    ):

        BehavioralSignalsEngine(
            minimum_features=6
        )