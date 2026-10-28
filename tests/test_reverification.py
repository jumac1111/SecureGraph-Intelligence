from fastapi.testclient import TestClient

from app.main import (
    app,
    session_store,
)


client = TestClient(app)


def login():

    response = client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200

    return response


def test_successful_reverification_restores_active_session():

    isolated_client = TestClient(app)

    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200


    session_id = (
        response.cookies.get(
            "session_id"
        )
    )

    assert session_id is not None


    session = session_store.get(
        session_id
    )

    assert session is not None


    session_store.mark_reverify(
        session
    )


    response = isolated_client.post(
        "/api/session/reverify",
        json={
            "verified": True,
        },
    )


    assert response.status_code == 200


    data = response.json()


    assert data["verified"] is True

    assert (
        data["session_state"]
        == "active"
    )

    assert (
        data["session_active"]
        is True
    )


def test_failed_reverification_keeps_session_in_reverify():

    isolated_client = TestClient(app)

    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200


    session_id = (
        response.cookies.get(
            "session_id"
        )
    )

    session = session_store.get(
        session_id
    )

    assert session is not None


    session_store.mark_reverify(
        session
    )


    original_count = (
        session.reverify_count
    )


    response = isolated_client.post(
        "/api/session/reverify",
        json={
            "verified": False,
        },
    )


    assert response.status_code == 200


    data = response.json()


    assert data["verified"] is False

    assert (
        data["session_state"]
        == "reverify"
    )

    assert (
        data["reverify_count"]
        == original_count + 1
    )


def test_locked_session_cannot_reverify():

    isolated_client = TestClient(app)

    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200


    session_id = (
        response.cookies.get(
            "session_id"
        )
    )

    session = session_store.get(
        session_id
    )

    assert session is not None


    session_store.lock(
        session,
        reason="Test lock.",
    )


    response = isolated_client.post(
        "/api/session/reverify",
        json={
            "verified": True,
        },
    )


    assert response.status_code == 401


def test_reverification_required_for_protected_resource():

    isolated_client = TestClient(app)

    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200


    session_id = (
        response.cookies.get(
            "session_id"
        )
    )

    session = session_store.get(
        session_id
    )

    assert session is not None


    session_store.mark_reverify(
        session
    )


    response = isolated_client.get(
        "/api/protected/resource"
    )


    assert response.status_code == 403

    assert (
        "verification"
        in response.json()["detail"].lower()
    )