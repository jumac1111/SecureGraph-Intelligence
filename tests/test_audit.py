from app.audit.logger import (
    AuditLogger,
)

from app.models.audit import (
    AuditEvent,
    AuditEventType,
)


def test_audit_event_is_recorded():

    logger = AuditLogger()

    logger.record(
        AuditEvent(
            event_type=(
                AuditEventType.LOGIN_SUCCESS
            ),
            user_id="researcher",
            session_id="session-1",
        )
    )

    events = logger.list_events()

    assert len(events) == 1

    assert (
        events[0].event_type
        == AuditEventType.LOGIN_SUCCESS
    )

    assert (
        events[0].user_id
        == "researcher"
    )


def test_audit_logger_can_be_cleared():

    logger = AuditLogger()

    logger.record(
        AuditEvent(
            event_type=(
                AuditEventType.LOGIN_SUCCESS
            ),
        )
    )

    assert logger.count() == 1

    logger.clear()

    assert logger.count() == 0


def test_audit_logger_respects_max_events():

    from app.config import AuditConfig

    logger = AuditLogger(
        AuditConfig(
            enabled=True,
            max_events=2,
        )
    )

    for index in range(3):

        logger.record(
            AuditEvent(
                event_type=(
                    AuditEventType.LOGIN_SUCCESS
                ),
                metadata={
                    "index": index,
                },
            )
        )

    events = logger.list_events()

    assert len(events) == 2

    assert (
        events[0].metadata["index"]
        == 1
    )

    assert (
        events[1].metadata["index"]
        == 2
    )