from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


ICAO24_PATTERN = re.compile(r"^[0-9a-fA-F]{6}$")
TIME_WINDOW_MAP = {
    "3h": timedelta(hours=3),
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
    "14d": timedelta(days=14),
    "30d": timedelta(days=30),
}


def normalize_icao24(value: str) -> str:
    normalized = value.strip().lower()
    if not ICAO24_PATTERN.fullmatch(normalized):
        raise ValueError("icao24 must be a 6-character hexadecimal string")
    return normalized


def build_display_type(
    type_code: str | None = None,
    manufacturer: str | None = None,
    model: str | None = None,
    category: str | None = None,
    category_label: str | None = None,
) -> str | None:
    if manufacturer and model:
        return f"{manufacturer} {model}"
    if model:
        return model
    if type_code:
        return type_code
    if category_label:
        return category_label
    if category:
        return category
    return None


def parse_time_window(value: str) -> timedelta:
    window = TIME_WINDOW_MAP.get(value)
    if window is None:
        raise ValueError("time_window must be one of 3h, 6h, 12h, 1d, 3d, 7d, 14d, 30d")
    return window


class FlightLogCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    icao24: str
    callsign: str | None = None
    origin_country: str | None = None
    departure_airport: str | None = None
    arrival_airport: str | None = None
    aircraft_latitude: Decimal | None = None
    aircraft_longitude: Decimal | None = None
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    vertical_rate: float | None = None
    owner_uuid: str | None = None
    logger_name: str | None = None
    logger_location: str | None = None
    logger_latitude: Decimal | None = None
    logger_longitude: Decimal | None = None
    note: str | None = None

    @field_validator("icao24")
    @classmethod
    def validate_icao24(cls, value: str) -> str:
        return normalize_icao24(value)


class NearbyFlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    icao24: str
    callsign: str | None = None
    origin_country: str | None = None
    latitude: float
    longitude: float
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    vertical_rate: float | None = None
    last_contact: int | None = None
    distance_km: float
    type_code: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    category: str | None = None
    category_label: str | None = None
    category_description: str | None = None
    display_type: str | None = None


class LiveFlightCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    supports_history: bool
    max_history_minutes: int
    history_step_minutes: int


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    url: str
    created_at: datetime


class AircraftRegistryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    icao24: str
    registration: str | None = None
    type_code: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    category: str | None = None
    category_label: str | None = None
    category_description: str | None = None
    first_seen: datetime
    last_updated: datetime


class FlightLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    icao24: str
    callsign: str | None = None
    origin_country: str | None = None
    departure_airport: str | None = None
    arrival_airport: str | None = None
    aircraft_latitude: Decimal | None = None
    aircraft_longitude: Decimal | None = None
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    vertical_rate: float | None = None
    owner_uuid: str | None = None
    logger_name: str | None = None
    logger_location: str | None = None
    logger_latitude: Decimal | None = None
    logger_longitude: Decimal | None = None
    note: str | None = None
    type_code: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    category: str | None = None
    category_label: str | None = None
    category_description: str | None = None
    display_type: str | None = None
    photos: list[PhotoResponse]
    aircraft_registry: AircraftRegistryResponse | None = None


class LoggedFlightNearbyResponse(BaseModel):
    id: int
    created_at: datetime
    icao24: str
    callsign: str | None = None
    note: str | None = None
    aircraft_latitude: Decimal | None = None
    aircraft_longitude: Decimal | None = None
    logger_latitude: Decimal | None = None
    logger_longitude: Decimal | None = None
    owner_uuid: str | None = None
    type_code: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    category: str | None = None
    category_label: str | None = None
    category_description: str | None = None
    display_type: str | None = None
    photos: list[PhotoResponse]
    distance_km: float
    is_owner: bool
