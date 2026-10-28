from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class FeatureStatistics(BaseModel):
    """
    Online robust-enough statistics for one behavioral feature.

    M2 stores the accumulated squared deviation needed for
    numerically stable variance calculation.

    The existing variance field remains part of the public model
    for compatibility.
    """

    count: int = 0

    mean: float = 0.0

    variance: float = 0.0

    minimum: Optional[float] = None

    maximum: Optional[float] = None

    last_updated: Optional[datetime] = None


class UserProfile(BaseModel):
    user_id: str

    state: str = "new"

    observation_count: int = 0

    required_observations: int = 50

    established_at: Optional[datetime] = None

    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    last_behavior_observation_at: Optional[datetime] = None

    behavior_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    features: dict[str, FeatureStatistics] = Field(
        default_factory=dict
    )