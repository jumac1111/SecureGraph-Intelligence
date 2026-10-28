from app.models.signals import SignalResult


class SignalValidator:

    REQUIRED_SOURCES = {"face", "behavior", "context"}

    def validate(self, signals: list[SignalResult]) -> list[SignalResult]:
        """
        Validate and normalize incoming signals.

        Missing signals are allowed. An unavailable signal is
        different from a mismatch.
        """

        validated = []

        for signal in signals:
            if not 0.0 <= signal.score <= 1.0:
                raise ValueError(
                    f"Invalid score from {signal.source}"
                )

            if not 0.0 <= signal.confidence <= 1.0:
                raise ValueError(
                    f"Invalid confidence from {signal.source}"
                )

            if not 0.0 <= signal.quality <= 1.0:
                raise ValueError(
                    f"Invalid quality from {signal.source}"
                )

            validated.append(signal)

        return validated