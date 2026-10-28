from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SignalStatus(str, Enum):
    """
    Status of an individual assurance signal.
    """

    CONSISTENT = "consistent"
    UNCERTAIN = "uncertain"
    MISMATCH = "mismatch"
    UNAVAILABLE = "unavailable"


class SignalResult(BaseModel):
    """
    Result produced by an individual assurance provider.
    """

    source: str

    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    quality: float = Field(
        ge=0.0,
        le=1.0,
    )

    status: SignalStatus

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    @property
    def effective_score(self) -> float:
        """
        Score adjusted for confidence and observation quality.
        """

        return (
            self.score
            * self.confidence
            * self.quality
        )


class BehaviorObservation(BaseModel):
    """
    Privacy-conscious numerical representation of user behavior.

    Raw sensitive content is deliberately excluded.

    We do not store:

    - keyboard characters
    - passwords
    - mouse coordinates
    - page contents
    """

    typing_speed: Optional[float] = None

    typing_interval_variance: Optional[float] = None

    mouse_speed: Optional[float] = None

    click_interval: Optional[float] = None

    navigation_interval: Optional[float] = None

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    @property
    def feature_count(self) -> int:
        """
        Number of behavioral features currently available.

        Timestamp is metadata and is deliberately excluded.
        """

        return sum(
            value is not None
            for value in (
                self.typing_speed,
                self.typing_interval_variance,
                self.mouse_speed,
                self.click_interval,
                self.navigation_interval,
            )
        )

    @property
    def completeness(self) -> float:
        """
        Fraction of supported behavioral features that
        are currently available.

        Timestamp is metadata and is deliberately excluded.
        """

        total_features = 5

        if total_features == 0:
            return 0.0

        return (
            self.feature_count
            / total_features
        )

    def feature_values(self) -> dict[str, float]:
        """
        Return only behavioral features that have values.

        Metadata such as timestamp is deliberately excluded.
        """

        values: dict[str, float] = {}

        if self.typing_speed is not None:
            values["typing_speed"] = self.typing_speed

        if self.typing_interval_variance is not None:
            values["typing_interval_variance"] = (
                self.typing_interval_variance
            )

        if self.mouse_speed is not None:
            values["mouse_speed"] = self.mouse_speed

        if self.click_interval is not None:
            values["click_interval"] = self.click_interval

        if self.navigation_interval is not None:
            values["navigation_interval"] = (
                self.navigation_interval
            )

        return values


class IdentityEvidence(BaseModel):
    """
    Privacy-conscious identity verification evidence.

    This model contains verification results rather than raw
    biometric or credential material.

    Raw identity material must never be stored here.
    """

    claimed_user_id: Optional[str] = None

    authenticated_user_id: Optional[str] = None

    verification_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    verification_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    verification_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    status: SignalStatus = (
        SignalStatus.UNAVAILABLE
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )