from threading import Lock

from app.config import AuditConfig

from app.models.audit import (
    AuditEvent,
)


class AuditLogger:
    """
    Small in-memory audit logger.

    The interface deliberately does not depend on storage.

    A future implementation can persist events to:
    - SQLite
    - PostgreSQL
    - an external SIEM
    - an append-only event store
    """

    def __init__(
        self,
        config: AuditConfig | None = None,
    ) -> None:

        self.config = config or AuditConfig()

        self._events: list[AuditEvent] = []

        self._lock = Lock()

    def record(
        self,
        event: AuditEvent,
    ) -> None:

        if not self.config.enabled:
            return

        with self._lock:

            self._events.append(
                event
            )

            overflow = (
                len(self._events)
                - self.config.max_events
            )

            if overflow > 0:

                del self._events[
                    :overflow
                ]

    def list_events(self) -> list[AuditEvent]:

        with self._lock:

            return list(
                self._events
            )

    def clear(self) -> None:

        with self._lock:

            self._events.clear()

    def count(self) -> int:

        with self._lock:

            return len(
                self._events
            )