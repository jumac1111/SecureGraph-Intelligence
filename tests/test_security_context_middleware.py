from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import SecurityContextConfig
from app.middleware.security_context import (
    SecurityContextMiddleware,
)
from app.models.location import LocationMetadata
from app.models.session import SessionState
from app.storage.session_store import SessionStore


@pytest.fixture
def test_env():
    """
    Initialize an application with an explicitly trusted
    loopback proxy network.

    This is test infrastructure configuration. Production
    deployments must provide their actual proxy networks.
    """

    app = FastAPI()
    store = SessionStore()

    security_config = SecurityContextConfig(
        trusted_proxy_cidrs=("127.0.0.0/8",),
        max_travel_speed_kmh=900.0,
    )

    app.add_middleware(
        SecurityContextMiddleware,
        session_store=store,
        config=security_config,
    )

    @app.get("/api/v1/secure-data")
    def protected_endpoint():
        return {"status": "access granted"}

    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    return client, store


def test_natural_travel_velocity_allows_access(test_env):
    """
    Normal physically possible movement preserves ACTIVE state.
    """

    client, store = test_env

    session = store.create(
        session_id="geo-session-1",
        user_id="user-123",
    )

    session.last_location = LocationMetadata(
        ip_address="82.148.97.22",
        country="QA",
        city="Al Wukair",
        latitude=25.1415,
        longitude=51.5832,
        timestamp=(
            datetime.now(timezone.utc)
            - timedelta(hours=2)
        ),
    )

    headers = {
        "Authorization": "geo-session-1",
        "X-Forwarded-For": "82.148.97.22",
        "x-geo-country": "QA",
        "x-geo-city": "Doha",
        "x-geo-lat": "25.3221",
        "x-geo-lon": "51.5284",
    }

    response = client.get(
        "/api/v1/secure-data",
        headers=headers,
    )

    assert response.status_code == 200
    assert session.state == SessionState.ACTIVE


def test_impossible_travel_velocity_triggers_reverification(
    test_env,
):
    """
    An impossible geographic jump through a trusted proxy
    moves the session into REVERIFY.
    """

    client, store = test_env

    session = store.create(
        session_id="geo-session-2",
        user_id="user-456",
    )

    session.last_location = LocationMetadata(
        ip_address="82.148.97.22",
        country="QA",
        city="Al Wukair",
        latitude=25.1415,
        longitude=51.5832,
        timestamp=(
            datetime.now(timezone.utc)
            - timedelta(minutes=5)
        ),
    )

    headers = {
        "Authorization": "geo-session-2",
        "X-Forwarded-For": "82.148.97.22",
        "x-geo-country": "GB",
        "x-geo-city": "London",
        "x-geo-lat": "51.5074",
        "x-geo-lon": "-0.1278",
    }

    response = client.get(
        "/api/v1/secure-data",
        headers=headers,
    )

    assert response.status_code == 200
    assert session.state == SessionState.REVERIFY


def test_missing_session_context_ignored_by_middleware(
    test_env,
):
    """
    Requests without a session continue normally.
    """

    client, _ = test_env

    response = client.get(
        "/api/v1/secure-data"
    )

    assert response.status_code == 200


def test_untrusted_client_cannot_supply_geo_context(
    test_env,
):
    """
    Geographic headers from an untrusted network peer must
    never become session location evidence.
    """

    client, store = test_env

    session = store.create(
        session_id="geo-session-untrusted",
        user_id="user-789",
    )

    headers = {
        "Authorization": "geo-session-untrusted",
        "x-geo-country": "GB",
        "x-geo-city": "London",
        "x-geo-lat": "51.5074",
        "x-geo-lon": "-0.1278",
    }

    response = client.get(
        "/api/v1/secure-data",
        headers=headers,
    )

    assert response.status_code == 200
    assert session.state == SessionState.ACTIVE
    assert getattr(session, "last_location", None) is None


def test_invalid_geo_coordinates_are_not_accepted(
    test_env,
):
    """
    Malformed or out-of-range coordinates must not become
    security context.
    """

    client, store = test_env

    session = store.create(
        session_id="geo-session-invalid",
        user_id="user-invalid",
    )

    headers = {
        "Authorization": "geo-session-invalid",
        "X-Forwarded-For": "82.148.97.22",
        "x-geo-country": "QA",
        "x-geo-city": "Doha",
        "x-geo-lat": "999.0",
        "x-geo-lon": "51.5284",
    }

    response = client.get(
        "/api/v1/secure-data",
        headers=headers,
    )

    assert response.status_code == 200
    assert session.state == SessionState.ACTIVE
    assert getattr(session, "last_location", None) is None


def test_forwarded_for_is_used_only_from_trusted_proxy(
    test_env,
):
    """
    A trusted proxy may provide the original client address
    through X-Forwarded-For.
    """

    client, store = test_env

    session = store.create(
        session_id="geo-session-forwarded",
        user_id="user-forwarded",
    )

    headers = {
        "Authorization": "geo-session-forwarded",
        "X-Forwarded-For": "203.0.113.10",
        "x-geo-country": "QA",
        "x-geo-city": "Doha",
        "x-geo-lat": "25.2854",
        "x-geo-lon": "51.5310",
    }

    response = client.get(
        "/api/v1/secure-data",
        headers=headers,
    )

    assert response.status_code == 200

    location = session.last_location

    assert location is not None
    assert location.ip_address == "203.0.113.10"


def test_malformed_forwarded_for_does_not_become_client_identity(
    test_env,
):
    """
    Invalid forwarded IP values must not be accepted.
    """

    client, store = test_env

    session = store.create(
        session_id="geo-session-bad-forward",
        user_id="user-bad-forward",
    )

    headers = {
        "Authorization": "geo-session-bad-forward",
        "X-Forwarded-For": "not-an-ip",
        "x-geo-country": "QA",
        "x-geo-city": "Doha",
        "x-geo-lat": "25.2854",
        "x-geo-lon": "51.5310",
    }

    response = client.get(
        "/api/v1/secure-data",
        headers=headers,
    )

    assert response.status_code == 200

    location = session.last_location

    assert location is not None
    assert location.ip_address == "127.0.0.1"


def test_missing_geo_metadata_does_not_create_location(
    test_env,
):
    """
    A trusted proxy without complete geo metadata must not
    produce partial location evidence.
    """

    client, store = test_env

    session = store.create(
        session_id="geo-session-partial",
        user_id="user-partial",
    )

    headers = {
        "Authorization": "geo-session-partial",
        "X-Forwarded-For": "82.148.97.22",
        "x-geo-country": "QA",
        "x-geo-city": "Doha",
    }

    response = client.get(
        "/api/v1/secure-data",
        headers=headers,
    )

    assert response.status_code == 200
    assert getattr(session, "last_location", None) is None
