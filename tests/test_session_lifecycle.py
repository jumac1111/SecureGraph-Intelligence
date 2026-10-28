from app.models.decision import (
    DecisionAction,
)

from app.models.session import (
    SessionState,
)

from app.storage.session_store import (
    SessionStore,
)


def create_session():

    store = SessionStore()

    session = store.create(
        session_id="session-1",
        user_id="researcher",
    )

    return store, session


def test_new_session_is_active():

    store, session = (
        create_session()
    )

    assert session.state == (
        SessionState.ACTIVE
    )

    assert session.active

    assert not session.requires_reverification

    assert not session.is_locked


def test_reverify_transition():

    store, session = (
        create_session()
    )

    store.mark_reverify(
        session
    )

    assert session.state == (
        SessionState.REVERIFY
    )

    assert not session.active

    assert session.requires_reverification

    assert session.reverify_count == 1


def test_successful_reverification_activates():

    store, session = (
        create_session()
    )

    store.mark_reverify(
        session
    )

    store.activate(
        session
    )

    assert session.state == (
        SessionState.ACTIVE
    )

    assert session.active

    assert not session.requires_reverification

    assert session.reverify_count == 1


def test_failed_reverification_keeps_session_in_reverify():

    store, session = (
        create_session()
    )

    store.mark_reverify(
        session
    )

    original_count = (
        session.reverify_count
    )

    store.mark_reverify(
        session
    )

    assert session.state == (
        SessionState.REVERIFY
    )

    assert session.reverify_count == (
        original_count + 1
    )


def test_lock_transition():

    store, session = (
        create_session()
    )

    store.lock(
        session,
        reason="test lock",
    )

    assert session.state == (
        SessionState.LOCKED
    )

    assert session.is_locked

    assert not session.active

    assert session.lock_reason == (
        "test lock"
    )


def test_locked_session_cannot_be_reactivated():

    store, session = (
        create_session()
    )

    store.lock(
        session,
        reason="test lock",
    )

    store.activate(
        session
    )

    assert session.state == (
        SessionState.LOCKED
    )

    assert session.is_locked


def test_policy_actions_are_applied_by_store():

    store, session = (
        create_session()
    )

    store.apply_action(
        session,
        DecisionAction.REVERIFY,
        "test",
    )

    assert session.state == (
        SessionState.REVERIFY
    )

    store.apply_action(
        session,
        DecisionAction.ALLOW,
        "test",
    )

    assert session.state == (
        SessionState.ACTIVE
    )

    store.apply_action(
        session,
        DecisionAction.LOCK,
        "test",
    )

    assert session.state == (
        SessionState.LOCKED
    )


def test_locked_session_ignores_policy_actions():

    store, session = (
        create_session()
    )

    store.lock(
        session,
        reason="terminal lock",
    )

    store.apply_action(
        session,
        DecisionAction.ALLOW,
        "attempted recovery",
    )

    assert session.state == (
        SessionState.LOCKED
    )

    assert session.is_locked
