from fastapi.testclient import TestClient

from app.main import app, session_store
from app.models.audit import AuditEventType


def login(client: TestClient) -> str:
    response = client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200

    session_id = response.cookies.get(
        "session_id"
    )

    assert session_id is not None

    return session_id


def test_logout_successfully_terminates_session():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    session_id = login(client)

    session = session_store.get(
        session_id
    )

    assert session is not None

    response = client.post(
        "/api/logout"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["authenticated"] is False
    assert body["logged_out"] is True

    assert session.is_locked


def test_logout_clears_session_cookie():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    login(client)

    response = client.post(
        "/api/logout"
    )

    assert response.status_code == 200

    set_cookie = response.headers.get(
        "set-cookie",
        ""
    )

    assert "session_id=" in set_cookie


def test_logout_generates_audit_event():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    session_id = login(client)

    response = client.post(
        "/api/logout"
    )

    assert response.status_code == 200

    events = session_store._audit_logger.list_events()

    logout_events = [
        event
        for event in events
        if event.event_type
        == AuditEventType.SESSION_LOGGED_OUT
        and event.session_id == session_id
    ]

    assert len(logout_events) == 1


def test_revoked_session_cannot_access_protected_resource():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    session_id = login(client)

    session = session_store.get(
        session_id
    )

    assert session is not None

    session_store.logout(
        session
    )

    response = client.get(
        "/api/protected/resource"
    )

    assert response.status_code == 401

    assert (
        "logged out"
        in response.json()["detail"].lower()
        or
        "locked"
        in response.json()["detail"].lower()
    )


def test_revoked_session_cannot_submit_behavior():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    session_id = login(client)

    session = session_store.get(
        session_id
    )

    assert session is not None

    session_store.logout(
        session
    )

    response = client.post(
        "/api/behavior/observation",
        json={
            "mouse_speed": 10.0,
            "typing_speed": 5.0,
            "session_duration": 60.0,
        },
    )

    assert response.status_code == 401


def test_logout_is_terminal():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    session_id = login(client)

    session = session_store.get(
        session_id
    )

    assert session is not None

    session_store.logout(
        session
    )

    assert session.is_locked

    session_store.activate(
        session,
        reason="attempted recovery",
    )

    assert session.is_locked


def test_logout_without_authentication_is_rejected():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = client.post(
        "/api/logout"
    )

    assert response.status_code == 401


def test_new_login_creates_new_session_after_logout():
    client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    first_session_id = login(client)

    response = client.post(
        "/api/logout"
    )

    assert response.status_code == 200

    second_session_id = login(client)

    assert (
        second_session_id
        != first_session_id
    )