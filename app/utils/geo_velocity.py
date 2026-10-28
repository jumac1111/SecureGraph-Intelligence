from __future__ import annotations
import math
from app.models.location import LocationMetadata

def calculate_travel_velocity_kmh(prev: LocationMetadata, current: LocationMetadata) -> float:
    """
    Calculates the speed (km/h) needed to travel between two location signatures.
    """
    time_diff_hours = (current.timestamp - prev.timestamp).total_seconds() / 3600.0
    if time_diff_hours <= 0:
        return 0.0

    # Haversine formula for physical distance calculations
    radius_earth_km = 6371.0
    
    lat1, lon1 = math.radians(prev.latitude), math.radians(prev.longitude)
    lat2, lon2 = math.radians(current.latitude), math.radians(current.longitude)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = radius_earth_km * c

    return distance_km / time_diff_hours
