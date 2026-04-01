from __future__ import annotations

import math


EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def center_from_bounds(north: float, south: float, east: float, west: float) -> tuple[float, float]:
    return ((north + south) / 2, (east + west) / 2)


def radius_from_bounds(north: float, south: float, east: float, west: float) -> float:
    center_lat, center_lon = center_from_bounds(north, south, east, west)
    corners = (
        (north, east),
        (north, west),
        (south, east),
        (south, west),
    )
    return max(haversine_distance_km(center_lat, center_lon, corner_lat, corner_lon) for corner_lat, corner_lon in corners)


def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    lat_delta = radius_km / 111.32
    cos_lat = max(abs(math.cos(math.radians(lat))), 0.01)
    lon_delta = radius_km / (111.32 * cos_lat)

    min_lat = max(-90.0, lat - lat_delta)
    max_lat = min(90.0, lat + lat_delta)
    min_lon = max(-180.0, lon - lon_delta)
    max_lon = min(180.0, lon + lon_delta)
    return min_lat, min_lon, max_lat, max_lon
