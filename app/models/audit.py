from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """
    Security-relevant lifecycle events.
    """

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"

    BEHAVIOR_OBSERVATION = "behavior_observation"

    ASSURANCE_EVALUATED = "assurance_evaluated"

    REVERIFICATION_REQUIRED = "reverification_required"

    REVERIFICATION_SUCCESS = "reverification_success"

    REVERIFICATION_FAILURE = "reverification_failure"

    SESSION_ACTIVATED = "session_activated"

    SESSION_EXPIRED = "session_expired"

    SESSION_LOCKED = "session_locked"

    SESSION_LOGGED_OUT = "session_logged_out"

    PROTECTED_RESOURCE_ACCESS = "protected_resource_access"


class AuditEvent(BaseModel):
    """
    Privacy-conscious audit record.

    Raw behavioral information must never be placed here.
    """

    event_type: AuditEventType

    user_id: Optional[str] = None

    session_id: Optional[str] = None

    action: Optional[str] = None

    reason: Optional[str] = None

    assurance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    risk_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
