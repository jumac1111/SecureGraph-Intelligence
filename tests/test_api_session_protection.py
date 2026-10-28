from fastapi.testclient import TestClient

from app.main import app


client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)



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


def observation(
    typing_speed=1.2,
    mouse_speed=20.0,
    click_interval=38.0,
):

    return {
        "typing_speed": typing_speed,
        "mouse_speed": mouse_speed,
        "click_interval": click_interval,
    }


def test_login_creates_authenticated_session():

    response = login()

    data = response.json()

    assert data["authenticated"] is True

    assert data["session_status"] == "active"


def test_behavior_observation_requires_session():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.post(
        "/api/behavior/observation",
        json=observation(),
    )

    assert response.status_code == 401


def test_behavior_learning():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200

    for _ in range(5):

        response = isolated_client.post(
            "/api/behavior/observation",
            json=observation(),
        )

        assert response.status_code == 200

        data = response.json()

        assert data["mode"] == "learning"

        assert (
            data["session_state"]
            == "active"
        )

        assert (
            data["session_active"]
            is True
        )


def test_session_status():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200

    response = isolated_client.get(
        "/api/session/status"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["authenticated"] is True

    assert data["active"] is True

    assert data["state"] == "active"

    assert (
        data["reverify_count"]
        == 0
    )

    assert data["lock_reason"] is None


def test_session_status_contains_assurance_fields():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200

    response = isolated_client.get(
        "/api/session/status"
    )

    assert response.status_code == 200

    data = response.json()

    assert "behavior_score" in data

    assert "assurance_score" in data

    assert "risk_score" in data

    assert "state" in data


def test_locked_session_cannot_submit_behavior():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


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

    # Import the application's actual session store.
    from app.main import session_store

    session = session_store.get(
        session_id
    )

    assert session is not None

    session_store.lock(
        session,
        reason="Test lock.",
    )

    response = isolated_client.post(
        "/api/behavior/observation",
        json=observation(),
    )

    assert response.status_code == 401

    assert (
        "locked"
        in response.json()["detail"].lower()
    )


def test_reverify_session_requires_identity_verification():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


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

    from app.main import session_store

    session = session_store.get(
        session_id
    )

    assert session is not None

    session_store.mark_reverify(
        session
    )

    response = isolated_client.post(
        "/api/behavior/observation",
        json=observation(),
    )

    assert response.status_code == 403

    assert (
        "verification"
        in response.json()["detail"].lower()
    )


def test_locked_session_status():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


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

    from app.main import session_store

    session = session_store.get(
        session_id
    )

    assert session is not None

    session_store.lock(
        session,
        reason="Identity verification failed.",
    )

    response = isolated_client.get(
        "/api/session/status"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["state"] == "locked"

    assert data["active"] is False

    assert data["authenticated"] is False

    assert (
        data["lock_reason"]
        == "Identity verification failed."
    )

    def test_active_session_can_access_protected_resource():

       isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.post(
        "/api/login",
        json={
            "username": "researcher",
            "password": "research123",
        },
    )

    assert response.status_code == 200

    response = isolated_client.get(
        "/api/protected/resource"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["authorized"] is True

    assert data["resource"] == "protected"

    assert data["session_state"] == "active"


def test_protected_resource_requires_authentication():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.get(
        "/api/protected/resource"
    )

    assert response.status_code == 401


def test_reverify_session_cannot_access_protected_resource():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.post(
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

    from app.main import session_store

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


def test_locked_session_cannot_access_protected_resource():

    isolated_client = client = TestClient(
    app,
    client=("127.0.0.1", 50000),
)


    response = isolated_client.post(
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

    from app.main import session_store

    session = session_store.get(
        session_id
    )

    assert session is not None

    session_store.lock(
        session,
        reason="Identity verification failed.",
    )

    response = isolated_client.get(
        "/api/protected/resource"
    )

    assert response.status_code == 401

    assert (
        "locked"
        in response.json()["detail"].lower()
    )