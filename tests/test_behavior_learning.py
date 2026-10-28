from app.engine.behavior_learning import (
    BehavioralLearningEngine,
)

from app.engine.behavior_verifier import (
    BehavioralVerifier,
)

from app.models.profile import UserProfile

from app.models.signals import (
    BehaviorObservation,
)


def create_normal_observation():

    return BehaviorObservation(
        typing_speed=5.0,
        typing_interval_variance=0.8,
        mouse_speed=400.0,
        click_interval=1.5,
        navigation_interval=10.0,
    )


def test_profile_learns():

    profile = UserProfile(
        user_id="user-001"
    )

    learner = BehavioralLearningEngine(
        required_observations=10
    )

    for _ in range(10):

        learner.update_profile(
            profile,
            create_normal_observation(),
        )

    assert profile.state == "established"

    assert profile.observation_count == 10


def test_normal_behavior_scores_high():

    profile = UserProfile(
        user_id="user-001"
    )

    learner = BehavioralLearningEngine(
        required_observations=10
    )

    for _ in range(10):

        learner.update_profile(
            profile,
            create_normal_observation(),
        )

    verifier = BehavioralVerifier()

    score = verifier.verify(
        profile,
        create_normal_observation(),
    )

    assert score > 0.8


def test_anomalous_behavior_scores_lower():

    profile = UserProfile(
        user_id="user-001"
    )

    learner = BehavioralLearningEngine(
        required_observations=10
    )

    for _ in range(10):

        learner.update_profile(
            profile,
            create_normal_observation(),
        )

    unusual = BehaviorObservation(
        typing_speed=20.0,
        typing_interval_variance=8.0,
        mouse_speed=2000.0,
        click_interval=0.1,
        navigation_interval=0.5,
    )

    verifier = BehavioralVerifier()

    score = verifier.verify(
        profile,
        unusual,
    )

    assert score < 0.5