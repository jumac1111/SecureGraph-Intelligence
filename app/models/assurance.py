from pydantic import BaseModel, Field


class AssuranceResult(BaseModel):
    """
    Combined assurance evidence before security policy
    is applied.

    This model deliberately contains no security action.

    The fusion layer calculates evidence.
    The policy layer determines the action.
    """

    assurance_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    risk_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    behavior_score: float | None = None

    face_score: float | None = None

    context_score: float | None = None