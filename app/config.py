from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, model_validator


class AssuranceConfig(BaseModel):
    """
    Configuration for continuous assurance signal fusion.

    Default assurance model:

        behavior = 0.60
        face     = 0.20
        context  = 0.20

    Identity assurance is disabled by default.
    """

    behavior_weight: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
    )

    identity_weight: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    face_weight: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
    )

    context_weight: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def validate_weights(self) -> "AssuranceConfig":
        legacy_total = (
            self.behavior_weight
            + self.face_weight
            + self.context_weight
        )

        if self.identity_weight == 0.0:
            if abs(legacy_total - 1.0) > 1e-9:
                raise ValueError(
                    "behavior_weight + face_weight + "
                    "context_weight must equal 1.0 when "
                    "identity_weight is disabled."
                )

            return self

        total = (
            self.behavior_weight
            + self.identity_weight
            + self.face_weight
            + self.context_weight
        )

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "behavior_weight + identity_weight + "
                "face_weight + context_weight must equal 1.0 "
                "when identity assurance is enabled."
            )

        return self


@dataclass(frozen=True)
class BehavioralConfig:
    """
    Configuration for the Behavioral Signals Engine.
    """

    required_observations: int = 50

    minimum_feature_observations: int = 5

    minimum_observation_quality: float = 0.20

    maximum_features_missing_ratio: float = 0.60

    maximum_update_z_score: float = 4.0

    maximum_temporal_gap_seconds: float = 300.0

    temporal_decay_seconds: float = 60.0

    consistency_threshold: float = 0.75

    uncertainty_threshold: float = 0.45

    def __post_init__(self) -> None:
        if self.required_observations < 1:
            raise ValueError(
                "required_observations must be at least 1."
            )

        if self.minimum_feature_observations < 1:
            raise ValueError(
                "minimum_feature_observations must be at least 1."
            )

        if not 0.0 <= self.minimum_observation_quality <= 1.0:
            raise ValueError(
                "minimum_observation_quality must be "
                "between 0.0 and 1.0."
            )

        if not 0.0 <= self.maximum_features_missing_ratio <= 1.0:
            raise ValueError(
                "maximum_features_missing_ratio must be "
                "between 0.0 and 1.0."
            )

        if self.maximum_update_z_score <= 0.0:
            raise ValueError(
                "maximum_update_z_score must be greater than 0."
            )

        if self.maximum_temporal_gap_seconds <= 0.0:
            raise ValueError(
                "maximum_temporal_gap_seconds must be "
                "greater than 0."
            )

        if self.temporal_decay_seconds <= 0.0:
            raise ValueError(
                "temporal_decay_seconds must be greater than 0."
            )

        if not 0.0 <= self.uncertainty_threshold <= 1.0:
            raise ValueError(
                "uncertainty_threshold must be "
                "between 0.0 and 1.0."
            )

        if not 0.0 <= self.consistency_threshold <= 1.0:
            raise ValueError(
                "consistency_threshold must be "
                "between 0.0 and 1.0."
            )

        if self.uncertainty_threshold >= self.consistency_threshold:
            raise ValueError(
                "uncertainty_threshold must be lower "
                "than consistency_threshold."
            )


@dataclass(frozen=True)
class PolicyConfig:
    """
    Centralized policy thresholds.
    """

    allow_threshold: float = 0.75

    reverify_threshold: float = 0.45

    max_reverify_attempts: int = 3

    def __post_init__(self) -> None:
        if not 0.0 <= self.reverify_threshold <= 1.0:
            raise ValueError(
                "reverify_threshold must be between 0.0 and 1.0."
            )

        if not 0.0 <= self.allow_threshold <= 1.0:
            raise ValueError(
                "allow_threshold must be between 0.0 and 1.0."
            )

        if self.reverify_threshold >= self.allow_threshold:
            raise ValueError(
                "reverify_threshold must be lower "
                "than allow_threshold."
            )

        if self.max_reverify_attempts < 1:
            raise ValueError(
                "max_reverify_attempts must be at least 1."
            )


@dataclass(frozen=True)
class SessionConfig:
    """
    Session lifecycle and cookie configuration.
    """

    cookie_name: str = "session_id"

    session_cookie_path: str = "/"

    session_cookie_http_only: bool = True

    session_cookie_secure: bool = False

    session_cookie_same_site: str = "lax"

    inactivity_timeout_seconds: int = 1800

    def __post_init__(self) -> None:
        if self.inactivity_timeout_seconds < 0:
            raise ValueError(
                "inactivity_timeout_seconds must be "
                "greater than or equal to 0."
            )


@dataclass(frozen=True)
class SecurityContextConfig:
    """
    Configuration for request/network security context.

    Geo-location headers are trusted ONLY when the immediate
    network peer belongs to one of the configured trusted
    proxy networks.

    An empty trusted_proxy_cidrs collection means that forwarded
    geo metadata is never trusted.

    This is intentionally fail-closed.
    """

    trusted_proxy_cidrs: tuple[str, ...] = ()

    max_travel_speed_kmh: float = 900.0

    geo_country_header: str = "x-geo-country"

    geo_city_header: str = "x-geo-city"

    geo_latitude_header: str = "x-geo-lat"

    geo_longitude_header: str = "x-geo-lon"

    forwarded_for_header: str = "x-forwarded-for"

    def __post_init__(self) -> None:
        if self.max_travel_speed_kmh <= 0.0:
            raise ValueError(
                "max_travel_speed_kmh must be greater than 0."
            )

        required_headers = (
            self.geo_country_header,
            self.geo_city_header,
            self.geo_latitude_header,
            self.geo_longitude_header,
            self.forwarded_for_header,
        )

        for header in required_headers:
            if not header or header.strip() != header:
                raise ValueError(
                    "Security context header names must be "
                    "non-empty and must not contain surrounding "
                    "whitespace."
                )


@dataclass(frozen=True)
class LearningConfig:
    """
    Backwards-compatible behavioral learning configuration.
    """

    required_observations: int = 50

    def __post_init__(self) -> None:
        if self.required_observations < 1:
            raise ValueError(
                "required_observations must be at least 1."
            )


@dataclass(frozen=True)
class AuditConfig:
    """
    Audit logging configuration.
    """

    enabled: bool = True

    max_events: int = 10_000

    def __post_init__(self) -> None:
        if self.max_events < 1:
            raise ValueError(
                "max_events must be at least 1."
            )


@dataclass(frozen=True)
class AppConfig:
    """
    Root application configuration.
    """

    assurance: AssuranceConfig = field(
        default_factory=AssuranceConfig
    )

    behavioral: BehavioralConfig = field(
        default_factory=BehavioralConfig
    )

    policy: PolicyConfig = field(
        default_factory=PolicyConfig
    )

    session: SessionConfig = field(
        default_factory=SessionConfig
    )

    security_context: SecurityContextConfig = field(
        default_factory=SecurityContextConfig
    )

    learning: LearningConfig = field(
        default_factory=LearningConfig
    )

    audit: AuditConfig = field(
        default_factory=AuditConfig
    )


config = AppConfig()
