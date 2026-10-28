from __future__ import annotations

import math
from typing import Mapping

from app.models.signals import (
    BehaviorObservation,
    SignalResult,
    SignalStatus,
)


class BehavioralSignalsEngine:
    """
    Converts privacy-conscious behavioral measurements into
    normalized behavioral assurance signals.

    This layer deliberately does NOT process or store:

    - raw keystrokes
    - passwords
    - page contents
    - mouse coordinates
    - screenshots

    It operates only on numerical behavioral measurements.

    Supported measurements:

    - typing_speed
    - typing_interval_variance
    - mouse_speed
    - click_interval
    - navigation_interval
    """

    FEATURE_NAMES = (
        "typing_speed",
        "typing_interval_variance",
        "mouse_speed",
        "click_interval",
        "navigation_interval",
    )

    def __init__(
        self,
        minimum_features: int = 1,
    ) -> None:

        if minimum_features < 1:
            raise ValueError(
                "minimum_features must be at least 1."
            )

        if minimum_features > len(
            self.FEATURE_NAMES
        ):
            raise ValueError(
                "minimum_features cannot exceed "
                "the number of supported behavioral features."
            )

        self.minimum_features = (
            minimum_features
        )

    # ==========================================================
    # OBSERVATION CONSTRUCTION
    # ==========================================================

    def build_observation(
        self,
        *,
        typing_speed: float | None = None,
        typing_interval_variance: float | None = None,
        mouse_speed: float | None = None,
        click_interval: float | None = None,
        navigation_interval: float | None = None,
    ) -> BehaviorObservation:
        """
        Construct a sanitized BehaviorObservation.

        Invalid numerical values such as NaN, infinity, and
        negative measurements are discarded rather than passed
        into the assurance pipeline.
        """

        values = {
            "typing_speed": typing_speed,
            "typing_interval_variance": (
                typing_interval_variance
            ),
            "mouse_speed": mouse_speed,
            "click_interval": click_interval,
            "navigation_interval": (
                navigation_interval
            ),
        }

        sanitized: dict[str, float] = {}

        for name, value in values.items():

            cleaned = self._sanitize_value(
                value
            )

            if cleaned is not None:
                sanitized[name] = cleaned

        return BehaviorObservation(
            **sanitized
        )

    # ==========================================================
    # MAPPING SUPPORT
    # ==========================================================

    def from_mapping(
        self,
        values: Mapping[str, float | None],
    ) -> BehaviorObservation:
        """
        Build an observation from a mapping.

        Unknown fields are ignored.

        This provides a clean boundary between an external
        telemetry collector and the assurance engine.
        """

        supported = {
            name: values.get(name)
            for name in self.FEATURE_NAMES
        }

        return self.build_observation(
            **supported
        )

    # ==========================================================
    # QUALITY
    # ==========================================================

    def calculate_quality(
        self,
        observation: BehaviorObservation,
    ) -> float:
        """
        Calculate observation quality based on feature
        availability.

        The result is always between 0.0 and 1.0.
        """

        return max(
            0.0,
            min(
                1.0,
                observation.completeness,
            ),
        )

    # ==========================================================
    # SIGNAL GENERATION
    # ==========================================================

    def generate(
        self,
        observation: BehaviorObservation,
    ) -> SignalResult:
        """
        Generate a behavioral signal from an observation.

        This signal represents the quality and availability
        of behavioral evidence.

        Actual behavioral consistency is evaluated later by
        BehavioralVerifier against the learned profile.
        """

        quality = self.calculate_quality(
            observation
        )

        feature_count = (
            observation.feature_count
        )

        if feature_count < self.minimum_features:

            return SignalResult(
                source="behavioral_signals",
                score=0.5,
                confidence=0.0,
                quality=quality,
                status=SignalStatus.UNAVAILABLE,
            )

        if quality < 0.5:

            status = SignalStatus.UNCERTAIN

            confidence = 0.3

        else:

            status = SignalStatus.CONSISTENT

            confidence = min(
                1.0,
                0.5 + (quality * 0.5),
            )

        return SignalResult(
            source="behavioral_signals",
            score=1.0,
            confidence=confidence,
            quality=quality,
            status=status,
        )

    # ==========================================================
    # FEATURE EXTRACTION
    # ==========================================================

    def extract_features(
        self,
        observation: BehaviorObservation,
    ) -> dict[str, float]:
        """
        Return only available numerical behavioral features.

        No raw user content is returned.
        """

        values = observation.model_dump(
            exclude_none=True
        )

        result: dict[str, float] = {}

        for name, value in values.items():

            cleaned = self._sanitize_value(
                value
            )

            if cleaned is not None:
                result[name] = cleaned

        return result

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @staticmethod
    def _sanitize_value(
        value: float | None,
    ) -> float | None:
        """
        Validate one behavioral measurement.

        Returns None for unusable values.
        """

        if value is None:
            return None

        try:
            numeric_value = float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

        if not math.isfinite(
            numeric_value
        ):
            return None

        if numeric_value < 0.0:
            return None

        return numeric_value