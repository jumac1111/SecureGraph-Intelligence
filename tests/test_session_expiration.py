from datetime import datetime, timedelta, timezone

from app.audit.logger import (
    AuditLogger,
)

from app.config import (
    SessionConfig,
)

from app.models.audit import (
    AuditEventType,
)

from app.models.session import (
    SessionState,
)

from app.storage.session_store import (
    SessionStore,
)


def create_store(
    timeout_seconds: int = 60,
):
    audit_logger = AuditLogger()

    store = SessionStore(
        audit_logger=audit_logger,
        config=SessionConfig(
            inactivity_timeout_seconds=(
                timeout_seconds
            )
        ),
    )

    session = store.create(
        session_id="session-1",
        user_id="researcher",
    )

    return store, audit_logger, session


def test_fresh_session_is_not_expired():

    store, audit_logger, session = (
        create_store()
    )

    assert not store.is_expired(
        session
    )

    assert session.state == (
        SessionState.ACTIVE
    )


def test_session_expires_after_inactivity():

    store, audit_logger, session = (
        create_store(
            timeout_seconds=60
        )
    )

    future = (
        session.last_activity_at
        + timedelta(seconds=61)
    )

    assert store.is_expired(
        session,
        now=future,
    )

    store.ensure_valid(
        session
    )

    # ensure_valid uses the real current time, so
    # explicitly expire for the deterministic lifecycle test.
    store.expire(
        session
    )

    assert session.state == (
        SessionState.LOCKED
    )

    assert session.is_locked

    assert session.lock_reason == (
        "Session expired due to inactivity."
    )


def test_expiration_generates_audit_event():

    store, audit_logger, session = (
        create_store(
            timeout_seconds=60
        )
    )

    store.expire(
        session
    )

    events = (
        audit_logger.list_events()
    )

    expiration_events = [
        event
        for event in events
        if event.event_type
        == AuditEventType.SESSION_EXPIRED
    ]

    assert len(
        expiration_events
    ) == 1

    assert (
        expiration_events[0].session_id
        == "session-1"
    )

    assert (
        expiration_events[0].user_id
        == "researcher"
    )


def test_expiration_is_terminal():

    store, audit_logger, session = (
        create_store()
    )

    store.expire(
        session
    )

    store.activate(
        session,
        reason="attempted recovery",
    )

    assert session.state == (
        SessionState.LOCKED
    )

    assert session.is_locked


def test_locked_session_does_not_expire_again():

    store, audit_logger, session = (
        create_store()
    )

    store.expire(
        session
    )

    first_count = (
        audit_logger.count()
    )

    store.ensure_valid(
        session
    )

    second_count = (
        audit_logger.count()
    )

    assert second_count == first_count

    expiration_events = [
        event
        for event in audit_logger.list_events()
        if event.event_type
        == AuditEventType.SESSION_EXPIRED
    ]

    assert len(
        expiration_events
    ) == 1


def test_touch_refreshes_activity():

    store, audit_logger, session = (
        create_store(
            timeout_seconds=60
        )
    )

    original_timestamp = (
        session.last_activity_at
    )

    store.touch(
        session
    )

    assert (
        session.last_activity_at
        >= original_timestamp
    )


def test_zero_timeout_disables_expiration():

    store, audit_logger, session = (
        create_store(
            timeout_seconds=0
        )
    )

    future = (
        session.last_activity_at
        + timedelta(days=365)
    )

    assert not store.is_expired(
        session,
        now=future,
    )


def test_negative_timeout_is_rejected():

    import pytest

    with pytest.raises(
        ValueError
    ):

        SessionConfig(
            inactivity_timeout_seconds=-1
        )