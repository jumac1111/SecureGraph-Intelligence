from app.models.signals import (
    SignalResult,
    SignalStatus,
)


class FaceProvider:
    """
    Simulated face-verification provider.
    """

    def generate(
        self,
        score: float = 1.0,
        confidence: float = 1.0,
        quality: float = 1.0,
        status: SignalStatus = SignalStatus.CONSISTENT,
    ) -> SignalResult:
        return SignalResult(
            source="face",
            score=score,
            confidence=confidence,
            quality=quality,
            status=status,
        )