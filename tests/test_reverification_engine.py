from app.config import PolicyConfig
from app.engine.policy import PolicyEngine
from app.engine.reverification import (
    ReverificationEngine,
)
from app.models.decision import DecisionAction
from app.models.session import SessionState
from app.storage.session_store import SessionStore


def create_reverify_session():
    store = SessionStore()

    session = store.create(
        session_id="test-session",
        user_id="test-user",
    )

    store.mark_reverify(
        session
    )

    return store, session


def test_successful_reverification_restores_active_session():

    store, session = create_reverify_session()

    engine = ReverificationEngine(
        session_store=store
    )

    result = engine.verify(
        session,
        verified=True,
    )

    assert result.verified is True

    assert (
        result.action
        == DecisionAction.ALLOW
    )

    assert (
        result.session_state
        == SessionState.ACTIVE
    )

    assert result.session_active is True

    assert (
        session.state
        == SessionState.ACTIVE
    )


def test_failed_reverification_keeps_session_in_reverify():

    store, session = create_reverify_session()

    original_count = (
        session.reverify_count
    )

    engine = ReverificationEngine(
        session_store=store
    )

    result = engine.verify(
        session,
        verified=False,
    )

    assert result.verified is False

    assert (
        result.action
        == DecisionAction.REVERIFY
    )

    assert (
        result.session_state
        == SessionState.REVERIFY
    )

    assert (
        result.reverify_count
        == original_count + 1
    )

    assert (
        session.reverify_count
        == original_count + 1
    )


def test_maximum_failed_reverification_locks_session():

    store, session = create_reverify_session()

    policy = PolicyEngine(
        config=PolicyConfig(
            max_reverify_attempts=2,
        )
    )

    engine = ReverificationEngine(
        session_store=store,
        policy_engine=policy,
    )

    first = engine.verify(
        session,
        verified=False,
    )

    assert (
        first.action
        == DecisionAction.REVERIFY
    )

    assert (
        session.state
        == SessionState.REVERIFY
    )

    second = engine.verify(
        session,
        verified=False,
    )

    assert (
        second.action
        == DecisionAction.LOCK
    )

    assert (
        session.state
        == SessionState.LOCKED
    )

    assert session.is_locked is True


def test_locked_session_cannot_be_reverified():

    store = SessionStore()

    session = store.create(
        session_id="locked-session",
        user_id="test-user",
    )

    store.lock(
        session,
        reason="Test lock.",
    )

    engine = ReverificationEngine(
        session_store=store
    )

    result = engine.verify(
        session,
        verified=True,
    )

    assert result.verified is False

    assert (
        result.action
        == DecisionAction.LOCK
    )

    assert (
        session.state
        == SessionState.LOCKED
    )


def test_can_reverify_only_when_session_is_in_reverify_state():

    store, session = create_reverify_session()

    engine = ReverificationEngine(
        session_store=store
    )

    assert (
        engine.can_reverify(session)
        is True
    )

    store.activate(
        session,
        reason="Test activation.",
    )

    assert (
        engine.can_reverify(session)
        is False
    )


def test_attempts_remaining():

    store, session = create_reverify_session()

    policy = PolicyEngine(
        config=PolicyConfig(
            max_reverify_attempts=3,
        )
    )

    engine = ReverificationEngine(
        session_store=store,
        policy_engine=policy,
    )

    assert (
        engine.attempts_remaining(session)
        == 2
    )

    engine.verify(
        session,
        verified=False,
    )

    assert (
        engine.attempts_remaining(session)
        == 1
    )


def test_successful_reverification_does_not_reset_count():

    store, session = create_reverify_session()

    engine = ReverificationEngine(
        session_store=store
    )

    original_count = (
        session.reverify_count
    )

    engine.verify(
        session,
        verified=True,
    )

    assert (
        session.reverify_count
        == original_count
    )