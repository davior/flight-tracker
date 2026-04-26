from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker, Session

from app.models import ProviderRequestLog

logger = logging.getLogger(__name__)


class ProviderUsageTracker:
    """Tracks per-provider request counts and errors.

    Maintains an in-memory sliding-window deque for fast real-time counts
    and persists every event to the database for long-term visibility.
    """

    _MAX_DEQUE_SIZE = 100_000

    def __init__(self, session_maker: "sessionmaker[Session]") -> None:
        self._session_maker = session_maker
        # deque of Unix timestamps, one per provider
        self._timestamps: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self._MAX_DEQUE_SIZE)
        )
        # (timestamp, error_code) of the most recent failure per provider;
        # None means the last recorded event was a success
        self._last_error: dict[str, tuple[float, str] | None] = {}
        self._last_request_at: dict[str, float] = {}

    def record(self, provider_name: str, success: bool, error_code: str | None) -> None:
        """Record a provider API call. Called by ProviderRouter after every request."""
        now = time.time()
        self._timestamps[provider_name].append(now)
        self._last_request_at[provider_name] = now

        if success:
            self._last_error[provider_name] = None
        else:
            self._last_error[provider_name] = (now, error_code or "unknown")

        logger.info(
            "provider %s: %s%s",
            provider_name,
            "success" if success else f"error ({error_code})",
            f" — total in deque: {len(self._timestamps[provider_name])}",
        )

        session = self._session_maker()
        try:
            session.add(
                ProviderRequestLog(
                    provider_name=provider_name,
                    requested_at=datetime.fromtimestamp(now, tz=timezone.utc),
                    success=success,
                    error_code=error_code,
                )
            )
            session.commit()
        except Exception:
            logger.exception("Failed to persist provider request log for %s", provider_name)
            session.rollback()
        finally:
            session.close()

    def count_in_period(self, provider_name: str, period_seconds: int) -> int:
        """Return the number of requests made to this provider in the last period_seconds."""
        cutoff = time.time() - period_seconds
        return sum(1 for t in self._timestamps[provider_name] if t >= cutoff)

    def last_error(self, provider_name: str) -> tuple[float, str] | None:
        """Return (timestamp, error_code) of the last failure, or None if last was success."""
        return self._last_error.get(provider_name)

    def last_request_at(self, provider_name: str) -> float | None:
        """Return Unix timestamp of the most recent request, or None if never called."""
        return self._last_request_at.get(provider_name)
