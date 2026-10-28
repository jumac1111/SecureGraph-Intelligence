from __future__ import annotations

from app.config import SecurityContextConfig
from app.security.request_context import (
    RequestContextProvider,
)


def build_provider() -> RequestContextProvider:
    return RequestContextProvider(
        SecurityContextConfig(
            trusted_proxy_cidrs=(
                "10.0.0.0/8",
            ),
            max_travel_speed_kmh=900.0,
        )
    )


def test_untrusted_peer_cannot_supply_geo_headers():
    provider = build_provider()

    location = provider.resolve_location(
        peer_ip="192.0.2.10",
        headers={
            "x-geo-country": "GB",
            "x-geo-city": "London",
            "x-geo-lat": "51.5074",
            "x-geo-lon": "-0.1278",
        },
    )

    assert location is None


def test_trusted_proxy_can_supply_valid_geo_headers():
    provider = build_provider()

    location = provider.resolve_location(
        peer_ip="10.10.10.10",
        headers={
            "X-Forwarded-For": "203.0.113.20",
            "x-geo-country": "QA",
            "x-geo-city": "Doha",
            "x-geo-lat": "25.2854",
            "x-geo-lon": "51.5310",
        },
    )

    assert location is not None
    assert location.ip_address == "203.0.113.20"
    assert location.country == "QA"
    assert location.city == "Doha"


def test_trusted_proxy_without_forwarded_for_uses_proxy_address():
    provider = build_provider()

    location = provider.resolve_location(
        peer_ip="10.10.10.10",
        headers={
            "x-geo-country": "QA",
            "x-geo-city": "Doha",
            "x-geo-lat": "25.2854",
            "x-geo-lon": "51.5310",
        },
    )

    assert location is not None
    assert location.ip_address == "10.10.10.10"


def test_invalid_latitude_is_rejected():
    provider = build_provider()

    location = provider.resolve_location(
        peer_ip="10.10.10.10",
        headers={
            "x-geo-country": "QA",
            "x-geo-city": "Doha",
            "x-geo-lat": "91.0",
            "x-geo-lon": "51.5310",
        },
    )

    assert location is None


def test_invalid_longitude_is_rejected():
    provider = build_provider()

    location = provider.resolve_location(
        peer_ip="10.10.10.10",
        headers={
            "x-geo-country": "QA",
            "x-geo-city": "Doha",
            "x-geo-lat": "25.2854",
            "x-geo-lon": "181.0",
        },
    )

    assert location is None


def test_empty_trusted_proxy_configuration_fails_closed():
    provider = RequestContextProvider(
        SecurityContextConfig(
            trusted_proxy_cidrs=(),
            max_travel_speed_kmh=900.0,
        )
    )

    location = provider.resolve_location(
        peer_ip="10.10.10.10",
        headers={
            "X-Forwarded-For": "203.0.113.20",
            "x-geo-country": "QA",
            "x-geo-city": "Doha",
            "x-geo-lat": "25.2854",
            "x-geo-lon": "51.5310",
        },
    )

    assert location is None
