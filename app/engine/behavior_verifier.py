from app.config import BehavioralConfig
from app.engine.behavior_signals import (
    BehavioralSignalsEngine,
)
from app.models.profile import UserProfile
from app.models.signals import (
    BehaviorObservation,
    SignalResult,
)


class BehavioralVerifier:
    """
    Backwards-compatible behavioral verifier.

    The actual behavioral signal generation is delegated to
    BehavioralSignalsEngine.
    """

    def __init__(
        self,
        config: BehavioralConfig | None = None,
    ) -> None:

        self.signal_engine = (
            BehavioralSignalsEngine(
                config=config,
            )
        )

    def verify(
        self,
        profile: UserProfile,
        observation: BehaviorObservation,
    ) -> float:
        """
        Return only the behavioral score.

        This method remains for compatibility with existing
        callers and tests.
        """

        signal = self.verify_signal(
            profile,
            observation,
        )

        return signal.score

    def verify_signal(
        self,
        profile: UserProfile,
        observation: BehaviorObservation,
    ) -> SignalResult:
        """
        Produce the complete behavioral signal.
        """

        return self.signal_engine.evaluate(
            profile,
            observation,
        )