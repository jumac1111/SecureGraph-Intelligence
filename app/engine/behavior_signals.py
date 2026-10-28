from __future__ import annotations

import math
from datetime import datetime, timezone

from app.config import BehavioralConfig
from app.models.profile import (
    UserProfile,
)
from app.models.signals import (
    BehaviorObservation,
    SignalResult,
    SignalStatus,
)


class BehavioralSignalsEngine:
    """
    Behavioral Signals Engine.

    Converts behavioral observations and a learned profile
    into a bounded SignalResult.

    Security goals:

    - complete feature mediation
    - no trust in raw behavioral input
    - bounded numerical output
    - missing-feature awareness
    - temporal consistency
    - outlier resistance
    - conservative confidence handling
    """

    def __init__(
        self,
        config: BehavioralConfig | None = None,
    ) -> None:

        self.config = (
            config
            or BehavioralConfig()
        )

    def evaluate(
        self,
        profile: UserProfile,
        observation: BehaviorObservation,
    ) -> SignalResult:

        values = observation.feature_values()

        if not values:

            return SignalResult(
                source="behavior",
                score=0.5,
                confidence=0.0,
                quality=0.0,
                status=SignalStatus.UNAVAILABLE,
            )

        finite_values = {
            name: value
            for name, value in values.items()
            if math.isfinite(value)
        }

        if not finite_values:

            return SignalResult(
                source="behavior",
                score=0.5,
                confidence=0.0,
                quality=0.0,
                status=SignalStatus.UNAVAILABLE,
            )

        feature_scores: list[float] = []

        feature_weights: list[float] = []

        for (
            feature_name,
            value,
        ) in finite_values.items():

            statistics = profile.features.get(
                feature_name
            )

            if statistics is None:
                continue

            if (
                statistics.count
                < self.config.minimum_feature_observations
            ):
                continue

            score = self._feature_score(
                statistics.mean,
                statistics.variance,
                value,
            )

            reliability = self._feature_reliability(
                statistics.count
            )

            feature_scores.append(
                score
            )

            feature_weights.append(
                reliability
            )

        if not feature_scores:

            return SignalResult(
                source="behavior",
                score=0.5,
                confidence=0.25,
                quality=self._observation_quality(
                    profile,
                    finite_values,
                ),
                status=SignalStatus.UNCERTAIN,
            )

        behavioral_score = self._weighted_average(
            feature_scores,
            feature_weights,
        )

        observation_quality = (
            self._observation_quality(
                profile,
                finite_values,
            )
        )

        temporal_score = (
            self._temporal_consistency(
                profile,
                observation.timestamp,
            )
        )

        combined_score = (
            behavioral_score
            * (0.80 + 0.20 * temporal_score)
        )

        combined_score = max(
            0.0,
            min(
                1.0,
                combined_score,
            ),
        )

        confidence = self._confidence(
            profile,
            len(feature_scores),
            observation_quality,
            temporal_score,
        )

        status = self._status(
            combined_score,
            confidence,
        )

        return SignalResult(
            source="behavior",
            score=combined_score,
            confidence=confidence,
            quality=observation_quality,
            status=status,
        )

    def _feature_score(
        self,
        mean: float,
        variance: float,
        value: float,
    ) -> float:

        standard_deviation = math.sqrt(
            max(
                variance,
                0.0,
            )
        )

        deviation = abs(
            value - mean
        )

        if deviation == 0.0:
            return 1.0

        standard_deviation = max(
            standard_deviation,
            0.001,
        )

        z_score = (
            deviation
            / standard_deviation
        )

        # Huber-like transition:
        #
        # small deviations remain smooth,
        # large deviations become increasingly
        # suspicious without numerical instability.
        if z_score <= 2.0:

            score = math.exp(
                -0.5
                * (
                    z_score ** 2
                )
            )

        else:

            score = math.exp(
                -2.0
                - (
                    0.5
                    * (
                        z_score
                        - 2.0
                    )
                )
            )

        return max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

    @staticmethod
    def _feature_reliability(
        count: int,
    ) -> float:

        if count <= 0:
            return 0.0

        # Reliability approaches 1 asymptotically.
        return min(
            1.0,
            math.log1p(count)
            / math.log1p(50),
        )

    def _observation_quality(
        self,
        profile: UserProfile,
        values: dict[str, float],
    ) -> float:

        known_features = 0

        for feature_name in values:

            if feature_name in profile.features:
                known_features += 1

        total_expected = max(
            len(profile.features),
            1,
        )

        known_ratio = (
            known_features
            / total_expected
        )

        finite_ratio = (
            len(values)
            / max(
                len(
                    profile.features
                ),
                len(values),
                1,
            )
        )

        quality = (
            0.60 * known_ratio
            + 0.40 * finite_ratio
        )

        return max(
            0.0,
            min(
                1.0,
                quality,
            ),
        )

    def _temporal_consistency(
        self,
        profile: UserProfile,
        timestamp: datetime,
    ) -> float:

        previous = (
            profile.last_behavior_observation_at
        )

        if previous is None:
            return 1.0

        current = timestamp

        if current.tzinfo is None:
            current = current.replace(
                tzinfo=timezone.utc
            )

        if previous.tzinfo is None:
            previous = previous.replace(
                tzinfo=timezone.utc
            )

        gap = abs(
            (
                current
                - previous
            ).total_seconds()
        )

        if gap <= 0.0:
            return 0.5

        if (
            gap
            > self.config.maximum_temporal_gap_seconds
        ):
            return 0.75

        return math.exp(
            -gap
            / self.config.temporal_decay_seconds
        )

    @staticmethod
    def _weighted_average(
        scores: list[float],
        weights: list[float],
    ) -> float:

        if not scores:
            return 0.5

        total_weight = sum(weights)

        if total_weight <= 0.0:
            return sum(scores) / len(scores)

        return (
            sum(
                score * weight
                for score, weight
                in zip(
                    scores,
                    weights,
                )
            )
            / total_weight
        )

    @staticmethod
    def _confidence(
        profile: UserProfile,
        feature_count: int,
        quality: float,
        temporal_score: float,
    ) -> float:

        maturity = min(
            1.0,
            profile.observation_count
            / max(
                profile.required_observations,
                1,
            ),
        )

        coverage = min(
            1.0,
            feature_count / 3.0,
        )

        confidence = (
            0.40 * maturity
            + 0.25 * coverage
            + 0.20 * quality
            + 0.15 * temporal_score
        )

        return max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

    def _status(
        self,
        score: float,
        confidence: float,
    ) -> SignalStatus:

        if confidence < 0.30:
            return SignalStatus.UNCERTAIN

        if score >= self.config.consistency_threshold:
            return SignalStatus.CONSISTENT

        if score >= self.config.uncertainty_threshold:
            return SignalStatus.UNCERTAIN

        return SignalStatus.MISMATCH