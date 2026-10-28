from pydantic import BaseModel

from app.models.decision import (
    DecisionAction,
)

from app.models.session import (
    SessionState,
)


class ReverificationResult(BaseModel):
    """
    Result produced by the reverification engine.

    This model describes the outcome of one reverification
    attempt without directly exposing the Session object.
    """

    verified: bool

    action: DecisionAction

    session_state: SessionState

    reverify_count: int

    session_active: bool

    reason: str