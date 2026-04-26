from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.services.live_flight_provider import (
    LiveFlightCapabilities,
    LiveFlightProvider,
    LiveFlightProviderError,
    LiveFlightRecord,
)

if TYPE_CHECKING:
    from app.services.provider_usage_tracker import ProviderUsageTracker

logger = logging.getLogger(__name__)

# Error codes that trigger a provider switch
_SWITCH_CODES = frozenset({"rate_limited", "authentication_failed"})


@dataclass
class ProviderConfig:
    name: str
    supports_time_shift: bool
    supports_trajectory: bool
    max_history_minutes: int
    history_step_minutes: int
    max_requests: int | None
    period_seconds: int | None


@dataclass
class ProviderStats:
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


@dataclass
class _ProviderSlot:
    provider: LiveFlightProvider
    config: ProviderConfig
    rate_limited_until: float | None = field(default=None)


class ProviderRouter:
    """Wraps multiple LiveFlightProvider instances and automatically fails over
    when a provider returns a rate-limit or authentication error.

    Implements the LiveFlightProvider protocol so it can drop in as a replacement.
    """

    def __init__(
        self,
        slots: list[_ProviderSlot],
        tracker: "ProviderUsageTracker",
    ) -> None:
        if not slots:
            raise ValueError("ProviderRouter requires at least one provider")
        self._slots = slots
        self._tracker = tracker
        self._active_index = 0

    # ------------------------------------------------------------------
    # LiveFlightProvider protocol
    # ------------------------------------------------------------------

    @property
    def capabilities(self) -> LiveFlightCapabilities:
        cfg = self._active_slot.config
        return LiveFlightCapabilities(
            provider=cfg.name,
            supports_history=cfg.supports_time_shift,
            max_history_minutes=cfg.max_history_minutes,
            history_step_minutes=cfg.history_step_minutes,
            supports_trajectory=cfg.supports_trajectory,
        )

    def close(self) -> None:
        for slot in self._slots:
            slot.provider.close()

    def get_flights_in_bounds(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        time_seconds: int | None = None,
    ) -> list[LiveFlightRecord]:
        return self._call_with_failover(
            "get_flights_in_bounds",
            north=north,
            south=south,
            east=east,
            west=west,
            time_seconds=time_seconds,
        )

    def get_flight_by_icao24(
        self,
        icao24: str,
        time_seconds: int | None = None,
    ) -> LiveFlightRecord | None:
        return self._call_with_failover(
            "get_flight_by_icao24",
            icao24=icao24,
            time_seconds=time_seconds,
        )

    # ------------------------------------------------------------------
    # Status (for the API endpoint)
    # ------------------------------------------------------------------

    def get_status(self) -> list[ProviderStats]:
        now = time.time()
        stats: list[ProviderStats] = []
        for i, slot in enumerate(self._slots):
            cfg = slot.config
            period = cfg.period_seconds or 86400
            last_err = self._tracker.last_error(cfg.name)
            stats.append(
                ProviderStats(
                    name=cfg.name,
                    is_active=(i == self._active_index),
                    is_healthy=(last_err is None),
                    requests_in_period=self._tracker.count_in_period(cfg.name, period),
                    max_requests=cfg.max_requests,
                    period_seconds=cfg.period_seconds,
                    last_request_at=self._tracker.last_request_at(cfg.name),
                    last_error_at=last_err[0] if last_err else None,
                    last_error_code=last_err[1] if last_err else None,
                    rate_limited_until=slot.rate_limited_until if slot.rate_limited_until and slot.rate_limited_until > now else None,
                    supports_time_shift=cfg.supports_time_shift,
                    supports_trajectory=cfg.supports_trajectory,
                )
            )
        return stats

    @property
    def active_provider_name(self) -> str:
        return self._active_slot.config.name

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _active_slot(self) -> _ProviderSlot:
        return self._slots[self._active_index]

    def _promote_recovered_providers(self) -> None:
        """If a higher-priority provider's cooldown has expired, switch back to it."""
        now = time.time()
        for i in range(self._active_index):
            slot = self._slots[i]
            if slot.rate_limited_until is None or now >= slot.rate_limited_until:
                if i < self._active_index:
                    logger.info(
                        "provider_router: %s cooldown expired — restoring as active provider",
                        slot.config.name,
                    )
                    slot.rate_limited_until = None
                    self._active_index = i
                    return

    def _mark_unavailable(self, slot: _ProviderSlot, error_code: str) -> None:
        """Mark a slot as unavailable and advance to the next slot."""
        period = slot.config.period_seconds or 86400
        slot.rate_limited_until = time.time() + period
        logger.warning(
            "provider_router: %s returned %s — marking unavailable until +%ds",
            slot.config.name,
            error_code,
            period,
        )

    def _next_available_index(self, after: int) -> int | None:
        now = time.time()
        for i in range(after + 1, len(self._slots)):
            s = self._slots[i]
            if s.rate_limited_until is None or now >= s.rate_limited_until:
                return i
        return None

    def _call_with_failover(self, method: str, **kwargs):  # type: ignore[return]
        self._promote_recovered_providers()

        attempts = 0
        max_attempts = len(self._slots)

        while attempts < max_attempts:
            attempts += 1
            slot = self._active_slot
            provider_name = slot.config.name
            try:
                result = getattr(slot.provider, method)(**kwargs)
                self._tracker.record(provider_name, success=True, error_code=None)
                logger.info(
                    "provider_router: %s %s succeeded (%d/%s in last %ss)",
                    provider_name,
                    method,
                    self._tracker.count_in_period(
                        provider_name, slot.config.period_seconds or 86400
                    ),
                    slot.config.max_requests or "∞",
                    slot.config.period_seconds or 86400,
                )
                return result
            except LiveFlightProviderError as exc:
                self._tracker.record(provider_name, success=False, error_code=exc.code)
                if exc.code in _SWITCH_CODES:
                    self._mark_unavailable(slot, exc.code)
                    next_idx = self._next_available_index(self._active_index)
                    if next_idx is None:
                        logger.warning(
                            "provider_router: all providers unavailable — returning error to client"
                        )
                        raise
                    self._active_index = next_idx
                    logger.warning(
                        "provider_router: switched to %s (supports_time_shift=%s, supports_trajectory=%s)",
                        self._active_slot.config.name,
                        self._active_slot.config.supports_time_shift,
                        self._active_slot.config.supports_trajectory,
                    )
                    # continue loop to retry with the new provider
                else:
                    # Transient error — don't switch
                    raise
