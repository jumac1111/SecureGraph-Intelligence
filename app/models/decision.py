from enum import Enum

from pydantic import BaseModel, Field


class DecisionAction(str, Enum):
    """
    Action selected by the policy engine.
    """

    ALLOW = "allow"
    REVERIFY = "reverify"
    LOCK = "lock"


class AssuranceResult(BaseModel):
    """
    Result produced by the assurance/fusion layer.

    This model intentionally contains no policy action.
    """

    assurance_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    risk_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    behavior_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    face_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    context_score: float = Field(
        ge=0.0,
        le=1.0,
    )


class PolicyDecision(BaseModel):
    """
    Policy interpretation of an assurance result.
    """

    action: DecisionAction

    reason: str

    assurance_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    risk_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    behavior_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    face_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    context_score: float = Field(
        ge=0.0,
        le=1.0,
    )


# Backwards-compatible name used by the existing application.
AssuranceDecision = PolicyDecision