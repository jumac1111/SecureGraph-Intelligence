from app.models.signals import (
    SignalResult,
    SignalStatus,
)


class ContextProvider:
    """
    Simulated contextual assurance provider.

    The interface is intentionally independent of the eventual
    implementation.

    A production implementation can later provide evidence such
    as:

    - device consistency
    - session timing
    - network consistency
    - navigation consistency
    - session activity

    Raw sensitive information is not exposed through this
    interface.

    The default simulated result represents consistent context.
    """

    def generate(
        self,
        score: float = 1.0,
        confidence: float = 1.0,
        quality: float = 1.0,
        status: SignalStatus = SignalStatus.CONSISTENT,
    ) -> SignalResult:
        return SignalResult(
            source="context",
            score=score,
            confidence=confidence,
            quality=quality,
            status=status,
        )