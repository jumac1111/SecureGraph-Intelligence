from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.models.location import LocationMetadata


class SessionState(str, Enum):
    """
    Explicit session lifecycle states.

    Session lifecycle is intentionally finite:

        ACTIVE
            |
            v
        REVERIFY
            |
            +----> ACTIVE
            |
            v
        LOCKED

    LOCKED is terminal.
    """

    ACTIVE = "active"
    REVERIFY = "reverify"
    LOCKED = "locked"


class Session(BaseModel):
    """
    Server-side authenticated session state.

    The session is the authoritative server-side representation
    of an authenticated user's security lifecycle.

    Lifecycle transitions should be performed through
    SessionStore rather than directly by API routes or middleware.

    Security context such as the last trusted location is retained
    on the server-side session so subsequent observations can be
    compared without trusting client-provided session state.
    """

    session_id: str

    user_id: str

    state: SessionState = SessionState.ACTIVE

    behavior_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    assurance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    risk_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    reverify_count: int = Field(
        default=0,
        ge=0,
    )

    lock_reason: str | None = None

    last_location: LocationMetadata | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    last_activity_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    state_changed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def active(self) -> bool:
        """
        Return True when the session is currently active.
        """

        return self.state == SessionState.ACTIVE

    @property
    def requires_reverification(self) -> bool:
        """
        Return True when the session requires reverification.
        """

        return self.state == SessionState.REVERIFY

    @property
    def is_locked(self) -> bool:
        """
        Return True when the session is permanently locked.
        """

        return self.state == SessionState.LOCKED

    model_config = {
        "arbitrary_types_allowed": True,
    }
