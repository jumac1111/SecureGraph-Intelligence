from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from app.config import SecurityContextConfig
from app.security.request_context import RequestContextProvider
from app.storage.session_store import SessionStore
from app.utils.geo_velocity import (
    calculate_travel_velocity_kmh,
)


class SecurityContextMiddleware(BaseHTTPMiddleware):
    """
    Attach request-derived security context to an active
    continuous-assurance session.
    """

    def __init__(
        self,
        app,
        *,
        session_store: SessionStore,
        config: SecurityContextConfig | None = None,
        max_speed_kmh: float | None = None,
    ) -> None:
        super().__init__(app)

        self._session_store = session_store

        # Prefer the complete configuration object.
        #
        # max_speed_kmh is retained as a compatibility option for
        # existing tests/callers that have not yet migrated to config.
        if config is None:
            config = SecurityContextConfig(
                max_travel_speed_kmh=(
                    max_speed_kmh
                    if max_speed_kmh is not None
                    else 900.0
                ),
            )

        self._config = config
        self._context_provider = RequestContextProvider(config)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process request security context before the endpoint.

        Requests without a valid session continue normally.

        Requests whose network/location context cannot be
        established safely also continue normally without
        manufacturing security evidence.
        """

        session_id = self._resolve_session_id(request)

        if session_id is None:
            return await call_next(request)

        session = self._session_store.get(session_id)

        if session is None:
            return await call_next(request)

        self._session_store.ensure_valid(session)

        if not session.active:
            return await call_next(request)

        peer_ip = self._resolve_peer_ip(request)

        current_location = self._context_provider.resolve_location(
            peer_ip=peer_ip,
            headers=request.headers,
            timestamp=datetime.now(timezone.utc),
        )

        if current_location is not None:
            self._process_location(
                session=session,
                current_location=current_location,
            )

        self._session_store.touch(session)

        return await call_next(request)

    def _resolve_session_id(
        self,
        request: Request,
    ) -> str | None:
        """
        Resolve the server-side session identifier.

        Cookie authentication takes precedence over the
        Authorization header.
        """

        session_id = request.cookies.get("session_id")

        if session_id:
            return session_id

        authorization = request.headers.get("authorization")

        if authorization:
            normalized = authorization.strip()

            if normalized:
                return normalized

        return None

    @staticmethod
    def _resolve_peer_ip(
        request: Request,
    ) -> str:
        """
        Return the immediate network peer.

        Forwarded client IP handling is deliberately delegated
        to RequestContextProvider.
        """

        if request.client is None:
            raise RuntimeError(
                "Unable to determine the request network peer."
            )

        return request.client.host

    def _process_location(
        self,
        *,
        session,
        current_location,
    ) -> None:
        """
        Compare trusted location context with the previous
        trusted location and update the session context.
        """

        previous_location = getattr(
            session,
            "last_location",
            None,
        )

        if previous_location is not None:
            velocity = calculate_travel_velocity_kmh(
                previous_location,
                current_location,
            )

            if velocity > self._config.max_travel_speed_kmh:
                self._session_store.mark_reverify(
                    session,
                    reason=(
                        "Impossible travel velocity detected: "
                        f"{velocity:.1f} km/h"
                    ),
                )

        object.__setattr__(
            session,
            "last_location",
            current_location,
        )
