from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    """
    Security policy configuration.

    The fusion engine calculates assurance.
    This model defines how assurance translates
    into security actions.
    """

    allow_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
    )

    reverify_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
    )

    max_reverify_attempts: int = Field(
        default=3,
        ge=1,
    )