from __future__ import annotations

from app.config import PolicyConfig
from app.models.decision import (
    DecisionAction,
)
from app.models.session import (
    Session,
    SessionState,
)
from app.models.reverification import (
    ReverificationResult,
)
from app.policy.policy_engine import (
    PolicyEngine,
)
from app.storage.session_store import (
    SessionStore,
)


class ReverificationEngine:
    """
    Handles reverification attempts for an existing session.

    Responsibilities:

    1. Validate the session.
    2. Reject locked sessions.
    3. Restore successfully verified sessions.
    4. Count failed reverification attempts.
    5. Lock the session after the configured maximum.
    """

    def __init__(
        self,
        session_store: SessionStore,
        policy_engine: PolicyEngine | None = None,
    ) -> None:

        self.session_store = session_store

        self.policy_engine = (
            policy_engine
            if policy_engine is not None
            else PolicyEngine(
                config=PolicyConfig()
            )
        )

    # ==========================================================
    # VERIFY
    # ==========================================================

    def verify(
        self,
        session: Session,
        verified: bool,
    ) -> ReverificationResult:
        """
        Process one reverification attempt.
        """

        self.session_store.ensure_valid(
            session
        )

        # ------------------------------------------------------
        # LOCKED SESSION
        # ------------------------------------------------------

        if session.is_locked:

            return ReverificationResult(
                verified=False,
                action=DecisionAction.LOCK,
                session_state=session.state,
                reverify_count=(
                    session.reverify_count
                ),
                session_active=session.active,
                reason=(
                    session.lock_reason
                    or
                    "Session is locked and cannot "
                    "be reverified."
                ),
            )

        # ------------------------------------------------------
        # SUCCESSFUL VERIFICATION
        # ------------------------------------------------------

        if verified:

            self.session_store.activate(
                session,
                reason=(
                    "Session successfully reverified."
                ),
            )

            return ReverificationResult(
                verified=True,
                action=DecisionAction.ALLOW,
                session_state=session.state,
                reverify_count=(
                    session.reverify_count
                ),
                session_active=session.active,
                reason=(
                    "Reverification succeeded. "
                    "Session restored to active state."
                ),
            )

        # ------------------------------------------------------
        # FAILED VERIFICATION
        # ------------------------------------------------------

        # Check if the active count has met or exceeded maximum thresholds.
        # If no remaining attempts are left, execute structural lockdown parameters.
        if self.attempts_remaining(session) <= 0:

            self.session_store.record_failed_reverification(
                session,
                reason=(
                    "Reverification failed; "
                    "maximum attempts reached."
                ),
            )

            self.session_store.lock(
                session,
                reason=(
                    "Maximum reverification attempts "
                    "exceeded."
                ),
            )

            return ReverificationResult(
                verified=False,
                action=DecisionAction.LOCK,
                session_state=session.state,
                reverify_count=(
                    session.reverify_count
                ),
                session_active=session.active,
                reason=(
                    "Reverification failed and the maximum "
                    "number of attempts was reached."
                ),
            )

        # ------------------------------------------------------
        # FAILED BUT ATTEMPTS REMAIN
        # ------------------------------------------------------

        self.session_store.record_failed_reverification(
            session,
            reason=(
                "Reverification failed. "
                "Another attempt is required."
            ),
        )

        return ReverificationResult(
            verified=False,
            action=DecisionAction.REVERIFY,
            session_state=session.state,
            reverify_count=session.reverify_count,
            session_active=session.active,
            reason=(
                "Reverification failed. "
                "Another attempt is required."
            ),
        )

    # ==========================================================
    # CAN REVERIFY
    # ==========================================================

    def can_reverify(
        self,
        session: Session,
    ) -> bool:
        """
        Return True only when the session is currently in
        REVERIFY state.
        """

        self.session_store.ensure_valid(
            session
        )

        return (
            session.state
            == SessionState.REVERIFY
            and not session.is_locked
            and session.requires_reverification
        )

    # ==========================================================
    # ATTEMPTS REMAINING
    # ==========================================================

    def attempts_remaining(
        self,
        session: Session,
    ) -> int:
        """
        Return the number of additional failed attempts that
        can occur before the session is locked.
        """

        maximum = (
            self.policy_engine
            .config
            .max_reverify_attempts
        )

        # Because a base session initialization counts as attempt index 1 
        # inside your store, remaining tries map cleanly via direct difference mapping.
        remaining = (
            maximum
            - session.reverify_count
        )

        return max(
            0,
            remaining,
        )
