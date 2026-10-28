from app.models.signals import (
    BehaviorObservation,
    SignalResult,
    SignalStatus,
)


class BehaviorProvider:

    def create_observation(
        self,
        typing_speed: float,
        typing_interval_variance: float,
        mouse_speed: float,
        click_interval: float,
        navigation_interval: float,
    ) -> BehaviorObservation:

        return BehaviorObservation(
            typing_speed=typing_speed,
            typing_interval_variance=typing_interval_variance,
            mouse_speed=mouse_speed,
            click_interval=click_interval,
            navigation_interval=navigation_interval,
        )

    def create_signal(
        self,
        score: float,
        confidence: float = 0.90,
        quality: float = 0.95,
        status: SignalStatus = SignalStatus.CONSISTENT,
    ) -> SignalResult:

        return SignalResult(
            source="behavior",
            score=score,
            confidence=confidence,
            quality=quality,
            status=status,
        )