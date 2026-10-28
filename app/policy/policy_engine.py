from __future__ import annotations

from app.config import PolicyConfig
from app.models.assurance import AssuranceResult
from app.models.decision import (
    DecisionAction,
    PolicyDecision,
)


class PolicyEngine:
    """
    Converts a normalized assurance result into a policy decision.

    Policy is deliberately separate from signal generation and
    signal fusion.

    Decision model:

        assurance >= allow_threshold
            -> ALLOW

        assurance >= reverify_threshold
            -> REVERIFY

        assurance < reverify_threshold
            -> LOCK

    The policy layer does not inspect raw identity, biometric,
    behavioral, or contextual evidence.
    """

    def __init__(
        self,
        config: PolicyConfig | None = None,
    ) -> None:
        self.config = (
            config
            if config is not None
            else PolicyConfig()
        )

    def evaluate(
        self,
        assurance: AssuranceResult,
    ) -> PolicyDecision:
        """
        Convert an assurance result into a policy decision.
        """

        score = assurance.assurance_score

        if score >= self.config.allow_threshold:
            return self._build_decision(
                assurance=assurance,
                action=DecisionAction.ALLOW,
                reason=(
                    "Assurance score is above "
                    "the allow threshold."
                ),
            )

        if score >= self.config.reverify_threshold:
            return self._build_decision(
                assurance=assurance,
                action=DecisionAction.REVERIFY,
                reason=(
                    "Assurance score is below "
                    "the allow threshold and "
                    "requires reverification."
                ),
            )

        return self._build_decision(
            assurance=assurance,
            action=DecisionAction.LOCK,
            reason=(
                "Assurance score is below "
                "the reverification threshold."
            ),
        )

    @staticmethod
    def _build_decision(
        assurance: AssuranceResult,
        action: DecisionAction,
        reason: str,
    ) -> PolicyDecision:
        """
        Construct a policy decision while preserving the
        normalized assurance result.
        """

        return PolicyDecision(
            action=action,
            reason=reason,
            assurance_score=assurance.assurance_score,
            risk_score=assurance.risk_score,
            behavior_score=assurance.behavior_score,
            face_score=assurance.face_score,
            context_score=assurance.context_score,
        )

    def should_lock_after_failed_reverification(
        self,
        reverify_count: int,
    ) -> bool:
        """
        Determine whether the supplied failed-attempt count
        has reached the configured maximum.

        Example with max_reverify_attempts = 2:

            count = 0 -> False
            count = 1 -> False
            count = 2 -> True
            count = 3 -> True

        The reverification engine should pass the count AFTER
        the failed attempt when making this decision.
        """

        if reverify_count < 0:
            raise ValueError(
                "reverify_count must be greater than "
                "or equal to 0."
            )

        return (
            reverify_count
            >= self.config.max_reverify_attempts
        )