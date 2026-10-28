from __future__ import annotations

from app.models.assurance import AssuranceResult
from app.models.signals import (
    SignalResult,
    SignalStatus,
)


class RiskFusionEngine:
    """
    Combines available assurance signals into a normalized
    assurance and risk result.

    Important properties:

    - Signal score is affected by confidence and quality.
    - UNAVAILABLE signals do not contribute negative evidence.
    - Available signals retain their configured weights.
    - Remaining weights are renormalized when a signal is
      unavailable.
    - Identity is supported as an independent assurance signal.
    - Assurance and risk scores are normalized to [0.0, 1.0].
    """

    def __init__(
        self,
        behavior_weight: float = 0.60,
        identity_weight: float = 0.0,
        face_weight: float = 0.25,
        context_weight: float = 0.15,
    ) -> None:
        weights = (
            (
                "behavior_weight",
                behavior_weight,
            ),
            (
                "identity_weight",
                identity_weight,
            ),
            (
                "face_weight",
                face_weight,
            ),
            (
                "context_weight",
                context_weight,
            ),
        )

        for name, value in weights:
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0.0 and 1.0."
                )

        total_weight = sum(
            value
            for _, value in weights
        )

        if total_weight <= 0.0:
            raise ValueError(
                "At least one signal weight must "
                "be greater than 0."
            )

        self.behavior_weight = behavior_weight
        self.identity_weight = identity_weight
        self.face_weight = face_weight
        self.context_weight = context_weight

    @staticmethod
    def _is_available(
        signal: SignalResult | None,
    ) -> bool:
        """
        Determine whether a signal can participate in fusion.

        A missing signal and an explicitly unavailable signal
        are both excluded from the weighted calculation.

        Neither case creates negative evidence.
        """

        return (
            signal is not None
            and signal.status != SignalStatus.UNAVAILABLE
        )

    @staticmethod
    def _normalize_score(
        value: float,
    ) -> float:
        """
        Clamp and normalize a floating-point assurance score.

        Rounding prevents insignificant floating-point artifacts
        from leaking through the public assurance API.

        Example:

            1.0 - 0.8

        can otherwise produce:

            0.19999999999999996

        The public result is therefore rounded to 10 decimal
        places after clamping.
        """

        value = max(
            0.0,
            min(
                1.0,
                value,
            ),
        )

        return round(
            value,
            10,
        )

    def fuse(
        self,
        behavior: SignalResult | None = None,
        identity: SignalResult | None = None,
        face: SignalResult | None = None,
        context: SignalResult | None = None,
    ) -> AssuranceResult:
        """
        Fuse all available assurance signals.

        Only signals that are both available and configured with
        a positive weight participate in the calculation.

        If one or more signals are unavailable, the weights of
        the remaining available signals are renormalized.

        For example, with:

            behavior = 0.60
            face = 0.25
            context = 0.15

        if context is unavailable, the effective calculation is:

            behavior: 0.60 / 0.85
            face:     0.25 / 0.85

        This prevents unavailable signals from reducing assurance.
        """

        weighted_total = 0.0
        total_weight = 0.0

        signals = (
            (
                behavior,
                self.behavior_weight,
            ),
            (
                identity,
                self.identity_weight,
            ),
            (
                face,
                self.face_weight,
            ),
            (
                context,
                self.context_weight,
            ),
        )

        for signal, weight in signals:
            if not self._is_available(signal):
                continue

            if weight <= 0.0:
                continue

            weighted_total += (
                signal.effective_score
                * weight
            )

            total_weight += weight

        if total_weight <= 0.0:
            assurance_score = 0.0
        else:
            assurance_score = (
                weighted_total
                / total_weight
            )

        assurance_score = (
            self._normalize_score(
                assurance_score
            )
        )

        risk_score = (
            self._normalize_score(
                1.0 - assurance_score
            )
        )

        return AssuranceResult(
            assurance_score=assurance_score,
            risk_score=risk_score,

            behavior_score=(
                behavior.score
                if behavior is not None
                else 0.0
            ),

            face_score=(
                face.score
                if face is not None
                else 0.0
            ),

            context_score=(
                context.score
                if context is not None
                else 0.0
            ),
        )