from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import Settings
from app.services.adsbx import ADSBxLiveFlightProvider
from app.services.live_flight_provider import LiveFlightProvider
from app.services.opensky import OpenSkyLiveFlightProvider
from app.services.provider_router import ProviderConfig, ProviderRouter, _ProviderSlot

if TYPE_CHECKING:
    from app.services.provider_usage_tracker import ProviderUsageTracker

logger = logging.getLogger(__name__)

# Directories searched for providers.json when PROVIDERS_CONFIG_PATH is not set
_DEFAULT_SEARCH_PATHS = [
    Path(__file__).resolve().parents[3] / "providers.json",  # project root / backend/
    Path(__file__).resolve().parents[2] / "providers.json",  # backend/app/../
]


def _load_providers_json(settings: Settings) -> dict | None:
    if settings.providers_config_path:
        p = Path(settings.providers_config_path)
        if not p.exists():
            logger.warning("PROVIDERS_CONFIG_PATH=%s not found", p)
            return None
        logger.info("Loading provider config from %s", p)
        return json.loads(p.read_text())

    for candidate in _DEFAULT_SEARCH_PATHS:
        if candidate.exists():
            logger.info("Loading provider config from %s", candidate)
            return json.loads(candidate.read_text())

    return None


def _instantiate_provider(name: str, settings: Settings) -> LiveFlightProvider:
    if name == "opensky":
        return OpenSkyLiveFlightProvider(settings)
    if name == "adsbx":
        if not settings.adsbx_api_key:
            raise ValueError("ADSBX_API_KEY must be set when adsbx provider is enabled")
        return ADSBxLiveFlightProvider(settings)
    raise ValueError(f"Unsupported live-flight provider: {name!r}")


def create_provider_router(
    settings: Settings,
    tracker: "ProviderUsageTracker",
) -> ProviderRouter:
    config_data = _load_providers_json(settings)

    if config_data:
        slots: list[_ProviderSlot] = []
        for entry in config_data.get("providers", []):
            if not entry.get("enabled", True):
                continue
            name = entry["name"]
            caps = entry.get("capabilities", {})
            rate = entry.get("rate_limit", {})
            provider_config = ProviderConfig(
                name=name,
                supports_time_shift=caps.get("supports_time_shift", False),
                supports_trajectory=caps.get("supports_trajectory", False),
                max_history_minutes=caps.get("max_history_minutes", 0),
                history_step_minutes=caps.get("history_step_minutes", 1),
                max_requests=rate.get("max_requests"),
                period_seconds=rate.get("period_seconds"),
            )
            try:
                provider = _instantiate_provider(name, settings)
            except ValueError as exc:
                logger.warning("Skipping provider %r: %s", name, exc)
                continue
            slots.append(_ProviderSlot(provider=provider, config=provider_config))

        if slots:
            logger.info(
                "ProviderRouter configured with %d provider(s): %s",
                len(slots),
                ", ".join(s.config.name for s in slots),
            )
            return ProviderRouter(slots, tracker)

        logger.warning("providers.json contained no usable providers — falling back to env var")

    # Backwards-compatible fallback: single provider from LIVE_FLIGHT_PROVIDER env var
    name = settings.live_flight_provider.strip().lower()
    logger.info("Falling back to single-provider mode: %s", name)
    provider = _instantiate_provider(name, settings)
    # Derive capabilities from the provider's own implementation
    caps = provider.capabilities
    provider_config = ProviderConfig(
        name=name,
        supports_time_shift=caps.supports_history,
        supports_trajectory=caps.supports_trajectory,
        max_history_minutes=caps.max_history_minutes,
        history_step_minutes=caps.history_step_minutes,
        max_requests=None,
        period_seconds=None,
    )
    return ProviderRouter([_ProviderSlot(provider=provider, config=provider_config)], tracker)
