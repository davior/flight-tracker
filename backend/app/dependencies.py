from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import sessionmaker, Session

from app.config import Settings
from app.services.aircraft_enrichment import AircraftEnrichmentService
from app.services.aircraft_enrichment_queue import AircraftEnrichmentQueue
from app.services.image_storage import ImageStorageService
from app.services.live_flight_provider import LiveFlightProvider


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
