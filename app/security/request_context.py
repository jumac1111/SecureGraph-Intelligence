from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from app.config import SecurityContextConfig
from app.models.location import LocationMetadata


@dataclass(frozen=True)
class RequestNetworkContext:
    """
    Network information derived from an incoming request.

    client_ip is the effective client address used by the
    application.

    forwarded_client_ip is populated only when the immediate
    peer
    belongs to a configured trusted proxy network.

    trusted_proxy indicates whether forwarded request metadata
    was permitted to participate in client identity resolution.
    """

    client_ip: str
    forwarded_client_ip: str | None
    trusted_proxy: bool


class RequestContextProvider:
    """
    Resolve trusted network and geographic request context.

    Security boundary:

        Internet client
            |
            v
        immediate peer
            |
            +---- trusted proxy? ----+
            |                        |
           no                       yes
            |                        |
      ignore forwarded        inspect forwarded
      and geo metadata        and trusted geo metadata

    Client-controlled forwarding and geo headers are never
    accepted from an untrusted network peer.

    HTTP header names are treated case-insensitively in accordance
    with HTTP semantics.
    """

    def __init__(
        self,
        config: SecurityContextConfig,
    ) -> None:
        self._config = config

        self._trusted_networks = tuple(
            ipaddress.ip_network(
                network,
                strict=False,
            )
            for network in config.trusted_proxy_cidrs
        )

    # ==========================================================
    # NETWORK
    # ==========================================================

    def resolve_network_context(
        self,
        *,
        peer_ip: str,
        headers: Mapping[str, str],
    ) -> RequestNetworkContext:
        """
        Resolve the effective network identity of the request.

        X-Forwarded-For is consulted only when the immediate
        network peer belongs to a configured trusted proxy
        network.

        Header-name matching is case-insensitive.
        """

        normalized_peer = self._validate_ip(
            peer_ip,
            field_name="peer_ip",
        )

        trusted_proxy = self._is_trusted_proxy(
            normalized_peer
        )

        if not trusted_proxy:
            return RequestNetworkContext(
                client_ip=normalized_peer,
                forwarded_client_ip=None,
                trusted_proxy=False,
            )

        forwarded_value = self._get_header(
            headers,
            self._config.forwarded_for_header,
        )

        forwarded_client_ip = (
            self._extract_forwarded_client_ip(
                forwarded_value
            )
        )

        return RequestNetworkContext(
            client_ip=(
                forwarded_client_ip
                if forwarded_client_ip is not None
                else normalized_peer
            ),
            forwarded_client_ip=forwarded_client_ip,
            trusted_proxy=True,
        )

    # ==========================================================
    # LOCATION
    # ==========================================================

    def resolve_location(
        self,
        *,
        peer_ip: str,
        headers: Mapping[str, str],
        timestamp: datetime | None = None,
    ) -> LocationMetadata | None:
        """
        Resolve geographic metadata from a trusted request.

        Returns None when:

        - the request did not originate through a trusted proxy;
        - required geo headers are absent;
        - latitude/longitude are malformed;
        - latitude/longitude are outside valid bounds.

        This method intentionally fails closed.
        """

        network = self.resolve_network_context(
            peer_ip=peer_ip,
            headers=headers,
        )

        if not network.trusted_proxy:
            return None

        country = self._get_required_header(
            headers,
            self._config.geo_country_header,
        )

        city = self._get_required_header(
            headers,
            self._config.geo_city_header,
        )

        latitude = self._parse_coordinate(
            self._get_header(
                headers,
                self._config.geo_latitude_header,
            ),
            minimum=-90.0,
            maximum=90.0,
            field_name="latitude",
        )

        longitude = self._parse_coordinate(
            self._get_header(
                headers,
                self._config.geo_longitude_header,
            ),
            minimum=-180.0,
            maximum=180.0,
            field_name="longitude",
        )

        if (
            country is None
            or city is None
            or latitude is None
            or longitude is None
        ):
            return None

        location_timestamp = (
            timestamp
            if timestamp is not None
            else datetime.now(timezone.utc)
        )

        if location_timestamp.tzinfo is None:
            raise ValueError(
                "Location timestamp must be timezone-aware."
            )

        return LocationMetadata(
            ip_address=network.client_ip,
            country=country,
            city=city,
            latitude=latitude,
            longitude=longitude,
            timestamp=location_timestamp,
        )

    # ==========================================================
    # TRUST
    # ==========================================================

    def _is_trusted_proxy(
        self,
        peer_ip: str,
    ) -> bool:
        """
        Determine whether an immediate network peer belongs to
        a configured trusted proxy network.
        """

        address = ipaddress.ip_address(peer_ip)

        return any(
            address in network
            for network in self._trusted_networks
        )

    # ==========================================================
    # FORWARDED IP
    # ==========================================================

    @staticmethod
    def _extract_forwarded_client_ip(
        forwarded_value: str | None,
    ) -> str | None:
        """
        Extract and validate the left-most X-Forwarded-For
        address.

        The left-most address is treated as the original client
        only because this provider operates behind a configured
        trusted proxy boundary.

        Invalid values are ignored rather than trusted.
        """

        if not forwarded_value:
            return None

        first_value = (
            forwarded_value
            .split(",", 1)[0]
            .strip()
        )

        if not first_value:
            return None

        try:
            return str(
                ipaddress.ip_address(first_value)
            )
        except ValueError:
            return None

    # ==========================================================
    # HEADER HELPERS
    # ==========================================================

    @staticmethod
    def _get_header(
        headers: Mapping[str, str],
        header_name: str,
    ) -> str | None:
        """
        Retrieve an HTTP header case-insensitively.

        HTTP header field names are case-insensitive, but generic
        Mapping implementations used by tests, adapters, and
        infrastructure components may not be.

        This helper therefore normalizes both sides explicitly.
        """

        normalized_name = header_name.strip().lower()

        if not normalized_name:
            return None

        for key, value in headers.items():
            if key.strip().lower() == normalized_name:
                return value

        return None

    @classmethod
    def _get_required_header(
        cls,
        headers: Mapping[str, str],
        header_name: str,
    ) -> str | None:
        """
        Return a normalized non-empty header value.
        """

        value = cls._get_header(
            headers,
            header_name,
        )

        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            return None

        return normalized

    @staticmethod
    def _parse_coordinate(
        value: str | None,
        *,
        minimum: float,
        maximum: float,
        field_name: str,
    ) -> float | None:
        """
        Parse and validate a geographic coordinate.
        """

        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            return None

        try:
            coordinate = float(normalized)
        except (TypeError, ValueError):
            return None

        if coordinate < minimum or coordinate > maximum:
            return None

        return coordinate

    # ==========================================================
    # IP VALIDATION
    # ==========================================================

    @staticmethod
    def _validate_ip(
        value: str,
        *,
        field_name: str,
    ) -> str:
        """
        Validate and normalize an IP address.
        """

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty."
            )

        try:
            return str(
                ipaddress.ip_address(normalized)
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must contain a valid IP address."
            ) from exc
