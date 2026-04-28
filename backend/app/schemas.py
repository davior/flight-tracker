from __future__ import annotations

import re
import math
from datetime import datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


ICAO24_PATTERN = re.compile(r"^[0-9a-fA-F]{6}$")


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


def parse_time_window_days(value: float) -> timedelta:
    if not math.isfinite(value):
        raise ValueError("time_window_days must be between 0.5 and 28")
    if value < 0.5 or value > 28:
        raise ValueError("time_window_days must be between 0.5 and 28")
    if not math.isclose(value * 2, round(value * 2), rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("time_window_days must be in 0.5 day increments")
    return timedelta(days=value)


class TrajectoryPoint(BaseModel):
    lat: float
    lng: float
    altitude: float | None = None
    heading: float | None = None
    velocity: float | None = None
    timestamp: int


class TrajectoryResponse(BaseModel):
    icao24: str
    supports_trajectory: bool
    points: list[TrajectoryPoint]


class FlightLogCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    icao24: str
    flight_time: datetime | None = None
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
    operator: str | None = None
    operator_icao: str | None = None
    operator_callsign: str | None = None
    owner: str | None = None
    serial_number: str | None = None
    year_built: str | None = None
    engines: str | None = None
    icao_aircraft_type: str | None = None


class LiveFlightCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    supports_history: bool
    max_history_minutes: int
    history_step_minutes: int
    supports_trajectory: bool = False


class ProviderStatusItem(BaseModel):
    name: str
    is_active: bool
    is_healthy: bool
    requests_in_period: int
    max_requests: int | None
    period_seconds: int | None
    last_request_at: float | None
    last_error_at: float | None
    last_error_code: str | None
    rate_limited_until: float | None
    supports_time_shift: bool
    supports_trajectory: bool


class ProviderStatusResponse(BaseModel):
    active_provider: str
    providers: list[ProviderStatusItem]


class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    url: str
    media_type: str
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
    operator: str | None = None
    operator_icao: str | None = None
    operator_iata: str | None = None
    operator_callsign: str | None = None
    owner: str | None = None
    serial_number: str | None = None
    year_built: str | None = None
    engines: str | None = None
    icao_aircraft_type: str | None = None
    first_seen: datetime
    last_updated: datetime


class FlightLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    flight_time: datetime
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
    owner_id: int | None = None
    owner_username: str | None = None
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
    operator: str | None = None
    operator_icao: str | None = None
    operator_callsign: str | None = None
    owner: str | None = None
    serial_number: str | None = None
    year_built: str | None = None
    engines: str | None = None
    icao_aircraft_type: str | None = None
    photos: list[PhotoResponse]
    aircraft_registry: AircraftRegistryResponse | None = None
    trajectory: list[TrajectoryPoint] | None = None


class LoggedFlightNearbyResponse(BaseModel):
    id: int
    created_at: datetime
    flight_time: datetime
    icao24: str
    callsign: str | None = None
    note: str | None = None
    aircraft_latitude: Decimal | None = None
    aircraft_longitude: Decimal | None = None
    logger_latitude: Decimal | None = None
    logger_longitude: Decimal | None = None
    owner_uuid: str | None = None
    owner_id: int | None = None
    owner_username: str | None = None
    heading: float | None = None
    type_code: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    category: str | None = None
    category_label: str | None = None
    category_description: str | None = None
    display_type: str | None = None
    operator: str | None = None
    operator_icao: str | None = None
    operator_callsign: str | None = None
    owner: str | None = None
    serial_number: str | None = None
    year_built: str | None = None
    engines: str | None = None
    icao_aircraft_type: str | None = None
    photos: list[PhotoResponse]
    distance_km: float
    is_owner: bool
    trajectory: list[TrajectoryPoint] | None = None


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_verified: bool
    tutorial_seen: bool
    is_admin: bool = False
    is_active: bool = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    login: str   # email or username
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    pass


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class AirportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ident: str
    type: str | None = None
    name: str | None = None
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    elevation_ft: int | None = None
    continent: str | None = None
    iso_country: str | None = None
    municipality: str | None = None
    iata_code: str | None = None
    last_updated: datetime


class DataSyncStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    last_synced_at: datetime | None = None
    last_sync_status: str | None = None
    row_count: int | None = None


class PatchLogRequest(BaseModel):
    note: str | None = None


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None


# ---------------------------------------------------------------------------
# Admin schemas
# ---------------------------------------------------------------------------

class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    is_verified: bool
    is_admin: bool
    is_active: bool
    tutorial_seen: bool
    created_at: datetime
    flight_log_count: int = 0


class AdminUserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str
    username: str
    password: str
    is_admin: bool = False


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str | None = None
    username: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    is_verified: bool | None = None


class AdminSetPasswordRequest(BaseModel):
    new_password: str


class RequestLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    method: str
    path: str
    status_code: int
    duration_ms: int
    user_id: int | None
    requested_at: datetime


class IpBlockRequest(BaseModel):
    ip_address: str
    reason: str | None = None
    release_hours: int | None = None


class IpBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ip_address: str
    reason: str | None
    blocked_at: datetime
    release_at: datetime | None
    auto_blocked: bool
    blocked_by_user_id: int | None


class DailyMetricPoint(BaseModel):
    date: str
    value: int


class MetricsOverviewResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_flight_logs: int
    requests_today: int
    unique_visitors_today: int
    requests_last_7_days: int


class AiQueryRequest(BaseModel):
    question: str
    context_hint: str | None = None


class AiQueryResponse(BaseModel):
    answer: str
    chart_type: str | None = None
    chart_data: dict | None = None
    model_used: str | None = None


class DataSyncTriggerResponse(BaseModel):
    source: str
    message: str
