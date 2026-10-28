from typing import Optional

from pydantic import BaseModel


class BehaviorObservation(BaseModel):
    typing_speed: Optional[float] = None
    typing_interval_variance: Optional[float] = None
    mouse_speed: Optional[float] = None
    click_interval: Optional[float] = None
    navigation_interval: Optional[float] = None

    def feature_values(self) -> dict[str, float]:
        """
        Return only the behavioral features that are actually available.

        This is the canonical representation consumed by the
        BehavioralSignalsEngine and BehavioralLearningEngine.
        """
        values: dict[str, float] = {}

        features = (
            "typing_speed",
            "typing_interval_variance",
            "mouse_speed",
            "click_interval",
            "navigation_interval",
        )

        for feature in features:
            value = getattr(self, feature, None)

            if value is None:
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue

            if not numeric_value == numeric_value:
                continue

            values[feature] = numeric_value

        return values

    def feature_count(self) -> int:
        return len(self.feature_values())