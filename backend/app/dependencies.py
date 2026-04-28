from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request
from jose import JWTError
from sqlalchemy.orm import sessionmaker, Session

from app.config import Settings
from app.db import get_db
from app.services.aircraft_enrichment import AircraftEnrichmentService
from app.services.aircraft_enrichment_queue import AircraftEnrichmentQueue
from app.services.auth_service import decode_access_token
from app.services.image_storage import ImageStorageService
from app.services.live_flight_provider import LiveFlightProvider


def get_data_seeder(request: Request):
    return request.app.state.data_seeder


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_live_flight_provider(request: Request) -> LiveFlightProvider:
    return request.app.state.live_flight_provider


def get_session_maker(request: Request) -> sessionmaker[Session]:
    return request.app.state.session_maker


def get_enrichment_service(request: Request) -> AircraftEnrichmentService:
    return request.app.state.enrichment_service


def get_enrichment_queue(request: Request) -> AircraftEnrichmentQueue:
    return request.app.state.enrichment_queue


def get_image_storage_service(request: Request) -> ImageStorageService:
    return request.app.state.image_storage


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """Require a valid Bearer JWT. Returns the User ORM object or raises 401."""
    from app.models import User  # local import to avoid circular deps

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.removeprefix("Bearer ")
    try:
        user_id = decode_access_token(token, settings)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_admin(
    current_user=Depends(get_current_user),
):
    """Require the authenticated user to be an active admin."""
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def get_optional_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """Return the User if a valid Bearer JWT is present, otherwise None."""
    from app.models import User  # local import to avoid circular deps

    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    try:
        user_id = decode_access_token(token, settings)
    except (JWTError, ValueError):
        return None
    return db.get(User, user_id)
