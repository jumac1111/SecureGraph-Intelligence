from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from app.audit.logger import AuditLogger
from app.config import SessionConfig
from app.models.audit import (
    AuditEvent,
    AuditEventType,
)
from app.models.decision import DecisionAction
from app.models.session import (
    Session,
    SessionState,
)


class SessionStore:
    """
    In-memory session store.

    This class owns session lifecycle transitions.

    Lifecycle responsibilities include:
    - session creation
    - session lookup
    - activity tracking
    - inactivity expiration
    - reverification transitions
    - failed reverification tracking
    - activation
    - locking
    - logout
    - policy action application
    - lifecycle audit events

    The clock is injected so time-dependent behavior can be
    tested deterministically without patching datetime.now().
    """

    def __init__(
        self,
        audit_logger: AuditLogger | None = None,
        config: SessionConfig | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sessions: dict[str, Session] = {}

        self._audit_logger = audit_logger

        self._config = (
            config
            if config is not None
            else SessionConfig()
        )

        self._clock = (
            clock
            if clock is not None
            else self._default_clock
        )

    # ======================================================
    # INTERNAL HELPERS
    # ======================================================

    @staticmethod
    def _default_clock() -> datetime:
        """
        Return the current UTC time.
        """
        return datetime.now(timezone.utc)

    def _now(self) -> datetime:
        """
        Return the current time from the injected clock.
        """
        return self._clock()

    def _audit(
        self,
        event_type: AuditEventType,
        *,
        session: Session,
        action: str | None = None,
        reason: str | None = None,
    ) -> None:
        """
        Write a lifecycle audit event when an audit logger
        has been configured.
        """

        if self._audit_logger is None:
            return

        self._audit_logger.record(
            AuditEvent(
                event_type=event_type,
                user_id=session.user_id,
                session_id=session.session_id,
                action=action,
                reason=reason,
                assurance_score=session.assurance_score,
                risk_score=session.risk_score,
            )
        )

    # ======================================================
    # CREATE
    # ======================================================

    def create(
        self,
        session_id: str,
        user_id: str,
    ) -> Session:
        """
        Create and store a new session.

        New sessions start in the ACTIVE state according to
        the Session model defaults.
        """

        if session_id in self._sessions:
            raise ValueError(
                "Session already exists."
            )

        now = self._now()

        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity_at=now,
            state_changed_at=now,
        )

        self._sessions[session_id] = session

        self._audit(
            AuditEventType.SESSION_ACTIVATED,
            session=session,
            action="create",
            reason="Authenticated session created.",
        )

        return session

    # ======================================================
    # GET
    # ======================================================

    def get(
        self,
        session_id: str,
    ) -> Session | None:
        """
        Return a stored session or None when it does not exist.
        """

        return self._sessions.get(session_id)

    # ======================================================
    # TOUCH
    # ======================================================

    def touch(
        self,
        session: Session,
    ) -> Session:
        """
        Update session activity.

        Locked sessions cannot be touched.

        Expired sessions are transitioned to LOCKED.
        """

        if session.is_locked:
            return session

        if self.is_expired(session):
            self.expire(session)
            return session

        session.last_activity_at = self._now()

        return session

    # ======================================================
    # EXPIRATION
    # ======================================================

    def is_expired(
        self,
        session: Session,
        now: datetime | None = None,
    ) -> bool:
        """
        Determine whether a session has exceeded its
        configured inactivity timeout.

        A timeout of zero disables inactivity expiration.

        Locked sessions are never considered newly expired.
        """

        if session.is_locked:
            return False

        timeout_seconds = (
            self._config.inactivity_timeout_seconds
        )

        if timeout_seconds == 0:
            return False

        current_time = (
            now
            if now is not None
            else self._now()
        )

        elapsed = (
            current_time
            - session.last_activity_at
        ).total_seconds()

        return elapsed >= timeout_seconds

    def ensure_valid(
        self,
        session: Session,
    ) -> Session:
        """
        Ensure the session has not expired.

        If inactivity expiration has occurred, the session
        transitions to LOCKED through expire().
        """

        if session.is_locked:
            return session

        if self.is_expired(session):
            self.expire(session)

        return session

    def expire(
        self,
        session: Session,
    ) -> Session:
        """
        Permanently expire a session due to inactivity.

        Expiration is terminal because it transitions the
        session to LOCKED.
        """

        if session.is_locked:
            return session

        reason = (
            "Session expired due to inactivity."
        )

        self.lock(
            session,
            reason=reason,
            audit_event_type=(
                AuditEventType.SESSION_EXPIRED
            ),
        )

        return session

    # ======================================================
    # MARK REVERIFY
    # ======================================================

    def mark_reverify(
        self,
        session: Session,
        *,
        reason: str | None = None,
    ) -> Session:
        """
        Transition a session into the REVERIFY state.

        Every call represents a new reverification requirement
        and therefore increments reverify_count.

        This behavior is intentional because the lifecycle tests
        expect repeated calls to mark_reverify() to increase the
        count.

        A locked session cannot be moved back into REVERIFY.
        """

        if session.is_locked:
            return session

        now = self._now()

        previous_state = session.state

        session.state = SessionState.REVERIFY

        # Every explicit reverification requirement counts.
        session.reverify_count += 1

        session.state_changed_at = now
        session.last_activity_at = now

        if previous_state != SessionState.REVERIFY:
            self._audit(
                AuditEventType.REVERIFICATION_REQUIRED,
                session=session,
                action="reverify",
                reason=reason,
            )

        return session

    # ======================================================
    # RECORD FAILED REVERIFICATION
    # ======================================================

    def record_failed_reverification(
        self,
        session: Session,
        *,
        reason: str | None = None,
    ) -> Session:
        """
        Record a failed reverification attempt.

        The session remains in REVERIFY.

        This method increments reverify_count exactly once.

        IMPORTANT:
        ReverificationEngine should call this method for a
        failed verification rather than calling mark_reverify()
        again, otherwise one failed attempt could be counted
        twice.
        """

        if session.is_locked:
            return session

        now = self._now()

        session.state = SessionState.REVERIFY

        session.reverify_count += 1

        session.state_changed_at = now
        session.last_activity_at = now

        self._audit(
            AuditEventType.REVERIFICATION_FAILURE,
            session=session,
            action="reverify",
            reason=(
                reason
                or
                "Identity verification failed."
            ),
        )

        return session

    # ======================================================
    # ACTIVATE
    # ======================================================

    def activate(
        self,
        session: Session,
        *,
        reason: str | None = None,
    ) -> Session:
        """
        Activate a session.

        Locked sessions are terminal and cannot be activated.

        Successful reverification does NOT reset reverify_count.
        """

        if session.is_locked:
            return session

        now = self._now()

        previous_state = session.state

        session.state = SessionState.ACTIVE

        session.lock_reason = None

        session.state_changed_at = now
        session.last_activity_at = now

        if previous_state != SessionState.ACTIVE:
            self._audit(
                AuditEventType.SESSION_ACTIVATED,
                session=session,
                action="activate",
                reason=(
                    reason
                    or
                    "Session activated."
                ),
            )

        return session

    # ======================================================
    # LOCK
    # ======================================================

    def lock(
        self,
        session: Session,
        reason: str,
        *,
        audit_event_type: AuditEventType = (
            AuditEventType.SESSION_LOCKED
        ),
    ) -> Session:
        """
        Permanently lock a session.

        LOCKED is terminal. A locked session cannot later be
        activated or restored.
        """

        if session.is_locked:
            return session

        now = self._now()

        session.state = SessionState.LOCKED

        session.lock_reason = reason

        session.state_changed_at = now
        session.last_activity_at = now

        self._audit(
            audit_event_type,
            session=session,
            action="lock",
            reason=reason,
        )

        return session

    # ======================================================
    # LOGOUT
    # ======================================================

    def logout(
        self,
        session: Session,
    ) -> Session:
        """
        Permanently terminate an authenticated session.

        Logout is terminal and uses the server-side LOCKED
        state so an already-issued session identifier cannot
        be reused to regain access.

        The distinction between logout and security locking
        is preserved through the audit event and lock reason.
        """

        if session.is_locked:
            return session

        reason = (
            "Session logged out by the authenticated user."
        )

        return self.lock(
            session,
            reason=reason,
            audit_event_type=(
                AuditEventType.SESSION_LOGGED_OUT
            ),
        )

    # ======================================================
    # APPLY POLICY ACTION
    # ======================================================

    def apply_action(
        self,
        session: Session,
        action: DecisionAction | str,
        reason: str,
    ) -> Session:
        """
        Apply a policy decision to the session lifecycle.
        """

        if isinstance(action, str):
            action = DecisionAction(action)

        if session.is_locked:
            return session

        if action == DecisionAction.ALLOW:
            self.activate(
                session,
                reason=reason,
            )

            return session

        if action == DecisionAction.REVERIFY:
            self.mark_reverify(
                session,
                reason=reason,
            )

            return session

        if action == DecisionAction.LOCK:
            self.lock(
                session,
                reason=reason,
            )

            return session

        raise ValueError(
            f"Unsupported session action: {action}"
        )

    # ======================================================
    # DELETE
    # ======================================================

    def delete(
        self,
        session_id: str,
    ) -> None:
        """
        Remove a session from the in-memory store.
        """

        self._sessions.pop(
            session_id,
            None,
        )

    # ======================================================
    # CLEAR
    # ======================================================

    def clear(self) -> None:
        """
        Remove all sessions.
        """

        self._sessions.clear()

    # ======================================================
    # COUNT
    # ======================================================

    def count(self) -> int:
        """
        Return the number of stored sessions.
        """

        return len(self._sessions)