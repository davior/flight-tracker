from __future__ import annotations

import logging

from app.schemas import TrajectoryPoint
from app.services.live_flight_provider import LiveFlightProvider, LiveFlightProviderError

logger = logging.getLogger(__name__)

DEFAULT_MAX_HISTORY_MINUTES = 60
DEFAULT_STEP_MINUTES = 10


def build_trajectory(
    provider: LiveFlightProvider,
    icao24: str,
    reference_time: int,
    max_history_minutes: int = DEFAULT_MAX_HISTORY_MINUTES,
    step_minutes: int = DEFAULT_STEP_MINUTES,
) -> list[TrajectoryPoint]:
    """Sample historical positions for an aircraft going back from reference_time.

    Queries the provider at intervals of step_minutes going back up to
    max_history_minutes. Silently skips time points where the aircraft is
    not found (radar dropout) and continues searching.

    Returns points ordered oldest → newest.
    """
    points: list[TrajectoryPoint] = []

    for offset_minutes in range(step_minutes, max_history_minutes + 1, step_minutes):
        query_time = reference_time - offset_minutes * 60
        # Round to 5-second boundary for cache-friendliness (matches /flights/nearby behaviour)
        query_time = query_time - (query_time % 5)

        try:
            record = provider.get_flight_by_icao24(icao24, query_time)
        except LiveFlightProviderError as exc:
            logger.debug("Skipping trajectory point at offset %dm: %s", offset_minutes, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error sampling trajectory at offset %dm: %s", offset_minutes, exc)
            continue

        if record is not None:
            points.append(
                TrajectoryPoint(
                    lat=record.latitude,
                    lng=record.longitude,
                    altitude=record.altitude,
                    heading=record.heading,
                    velocity=record.velocity,
                    timestamp=query_time,
                )
            )

    # Always normalize explicitly by timestamp so ordering doesn't depend on loop direction.
    points.sort(key=lambda point: point.timestamp)
    return points
