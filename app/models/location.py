from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class LocationMetadata:
    ip_address: str
    country: str
    city: str
    latitude: float
    longitude: float
    timestamp: datetime
