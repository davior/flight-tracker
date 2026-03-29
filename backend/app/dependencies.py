from __future__ import annotations

from fastapi import Request

from app.config import Settings
from app.services.aircraft_enrichment import AircraftEnrichmentService
from app.services.image_storage import ImageStorageService
from app.services.opensky import OpenSkyClient


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_opensky_client(request: Request) -> OpenSkyClient:
    return request.app.state.opensky_client


def get_enrichment_service(request: Request) -> AircraftEnrichmentService:
    return request.app.state.enrichment_service


def get_image_storage_service(request: Request) -> ImageStorageService:
    return request.app.state.image_storage
