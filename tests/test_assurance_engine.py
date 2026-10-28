from app.engine.engine import (
    ContinuousAssuranceEngine,
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
    )

    profile.features = {

        "typing_speed":
            FeatureStatistics(
                count=50,
                mean=1.2,
                variance=0.01,
            ),

        "mouse_speed":
            FeatureStatistics(
                count=50,
                mean=20.0,
                variance=4.0,
            ),

        "click_interval":
            FeatureStatistics(
                count=50,
                mean=38.0,
                variance=4.0,
            ),
    }

    return profile


def test_consistent_behavior_allows():

    engine = (
        ContinuousAssuranceEngine()
    )

    profile = (
        established_profile()
    )

    observation = (
        BehaviorObservation(
            typing_speed=1.2,
            mouse_speed=20.0,
            click_interval=38.0,
        )
    )

    decision = engine.evaluate(
        profile,
        observation,
    )

    assert (
        decision.action.value
        == "allow"
    )

    assert (
        decision.assurance_score
        >= 0.75
    )

    assert (
        decision.behavior_score
        is not None
    )

    assert (
        decision.face_score
        is not None
    )

    assert (
        decision.context_score
        is not None
    )


def test_unusual_behavior_reduces_assurance():

    engine = (
        ContinuousAssuranceEngine()
    )

    profile = (
        established_profile()
    )

    observation = (
        BehaviorObservation(
            typing_speed=5.0,
            mouse_speed=100.0,
            click_interval=2.0,
        )
    )

    decision = engine.evaluate(
        profile,
        observation,
    )

    assert (
        decision.assurance_score
        < 0.45
    )

    assert (
        decision.action.value
        == "lock"
    )


def test_face_signal_can_be_supplied():

    engine = (
        ContinuousAssuranceEngine()
    )

    profile = (
        established_profile()
    )

    observation = (
        BehaviorObservation(
            typing_speed=1.2,
            mouse_speed=20.0,
            click_interval=38.0,
        )
    )

    face_signal = (
        engine.face_provider.generate(
            score=0.80,
            confidence=1.0,
            quality=1.0,
        )
    )

    decision = engine.evaluate(
        profile,
        observation,
        face_signal=face_signal,
    )

    assert (
        decision.face_score
        == 0.80
    )

    assert (
        decision.action.value
        == "allow"
    )


def test_context_signal_can_be_supplied():

    engine = (
        ContinuousAssuranceEngine()
    )

    profile = (
        established_profile()
    )

    observation = (
        BehaviorObservation(
            typing_speed=1.2,
            mouse_speed=20.0,
            click_interval=38.0,
        )
    )

    context_signal = (
        engine.context_provider.generate(
            score=0.70,
            confidence=1.0,
            quality=1.0,
        )
    )

    decision = engine.evaluate(
        profile,
        observation,
        context_signal=context_signal,
    )

    assert (
        decision.context_score
        == 0.70
    )

    assert (
        decision.action.value
        == "allow"
    )


def test_unavailable_context_is_ignored():

    engine = (
        ContinuousAssuranceEngine()
    )

    profile = (
        established_profile()
    )

    observation = (
        BehaviorObservation(
            typing_speed=1.2,
            mouse_speed=20.0,
            click_interval=38.0,
        )
    )

    context_signal = (
        engine.context_provider.generate(
            score=0.0,
            confidence=0.0,
            quality=0.0,
            status=(
                SignalStatus.UNAVAILABLE
            ),
        )
    )

    decision = engine.evaluate(
        profile,
        observation,
        context_signal=context_signal,
    )

    assert (
        decision.context_score
        == 0.0
    )

    assert (
        decision.action.value
        == "allow"
    )


def test_behavior_remains_primary_signal():

    engine = (
        ContinuousAssuranceEngine()
    )

    profile = (
        established_profile()
    )

    observation = (
        BehaviorObservation(
            typing_speed=5.0,
            mouse_speed=100.0,
            click_interval=2.0,
        )
    )

    face_signal = (
        engine.face_provider.generate(
            score=1.0,
            confidence=1.0,
            quality=1.0,
        )
    )

    context_signal = (
        engine.context_provider.generate(
            score=1.0,
            confidence=1.0,
            quality=1.0,
        )
    )

    decision = engine.evaluate(
        profile,
        observation,
        face_signal=face_signal,
        context_signal=context_signal,
    )

    assert (
        decision.behavior_score
        is not None
    )

    assert (
        decision.face_score
        == 1.0
    )

    assert (
        decision.context_score
        == 1.0
    )

    assert (
        decision.assurance_score
        < 0.75
    )