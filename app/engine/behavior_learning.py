from datetime import datetime, timezone
import math

from app.config import BehavioralConfig
from app.models.profile import (
    FeatureStatistics,
    UserProfile,
)
from app.models.signals import BehaviorObservation


class BehavioralLearningEngine:
    """
    Incrementally learns a behavioral profile.

    Important security properties:

    - Raw history is not retained.
    - Statistics are updated online.
    - Extreme observations are prevented from dominating
      established profiles.
    - Missing features do not reset existing statistics.
    - Learning stops treating the profile as untrusted once
      sufficient observations have been collected.
    """

    def __init__(
        self,
        required_observations: int = 50,
        behavioral_config: BehavioralConfig | None = None,
    ) -> None:

        self.config = (
            behavioral_config
            or BehavioralConfig(
                required_observations=(
                    required_observations
                )
            )
        )

        self.required_observations = (
            self.config.required_observations
        )

    def update_profile(
        self,
        profile: UserProfile,
        observation: BehaviorObservation,
    ) -> UserProfile:

        profile.required_observations = (
            self.required_observations
        )

        values = observation.feature_values()

        if not values:
            return profile

        accepted_features = 0

        for feature_name, value in values.items():

            if not math.isfinite(value):
                continue

            statistics = profile.features.get(
                feature_name
            )

            if statistics is None:
                statistics = FeatureStatistics()

                profile.features[
                    feature_name
                ] = statistics

            accepted = self._update_feature(
                statistics,
                value,
            )

            if accepted:
                accepted_features += 1

        if accepted_features == 0:
            return profile

        profile.observation_count += 1

        profile.last_updated = (
            datetime.now(timezone.utc)
        )

        profile.last_behavior_observation_at = (
            observation.timestamp
        )

        if (
            profile.observation_count
            >= self.required_observations
        ):
            profile.state = "established"

            if profile.established_at is None:
                profile.established_at = (
                    datetime.now(timezone.utc)
                )

        else:
            profile.state = "learning"

        return profile

    def _update_feature(
        self,
        statistics: FeatureStatistics,
        value: float,
    ) -> bool:

        old_count = statistics.count

        if old_count >= (
            self.config.minimum_feature_observations
        ):

            standard_deviation = math.sqrt(
                max(
                    statistics.variance,
                    0.0,
                )
            )

            standard_deviation = max(
                standard_deviation,
                0.001,
            )

            z_score = abs(
                value - statistics.mean
            ) / standard_deviation

            if (
                z_score
                > self.config.maximum_update_z_score
            ):
                return False

        new_count = old_count + 1

        if old_count == 0:

            statistics.count = 1
            statistics.mean = value
            statistics.variance = 0.0
            statistics.minimum = value
            statistics.maximum = value
            statistics.last_updated = (
                datetime.now(timezone.utc)
            )

            return True

        delta = (
            value
            - statistics.mean
        )

        new_mean = (
            statistics.mean
            + delta / new_count
        )

        delta2 = (
            value
            - new_mean
        )

        old_m2 = (
            statistics.variance
            * old_count
        )

        new_m2 = (
            old_m2
            + delta * delta2
        )

        new_variance = (
            new_m2 / new_count
        )

        statistics.count = new_count

        statistics.mean = new_mean

        statistics.variance = max(
            0.0,
            new_variance,
        )

        if statistics.minimum is None:
            statistics.minimum = value
        else:
            statistics.minimum = min(
                statistics.minimum,
                value,
            )

        if statistics.maximum is None:
            statistics.maximum = value
        else:
            statistics.maximum = max(
                statistics.maximum,
                value,
            )

        statistics.last_updated = (
            datetime.now(timezone.utc)
        )

        return True