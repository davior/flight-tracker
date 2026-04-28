from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker, Session

from app.config import Settings
from app.models import IpBlockList, RequestLog

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 300  # run every 5 minutes


def _detect_and_block(session: Session, settings: Settings) -> int:
    """Block IPs that exceed the configured request rate. Returns count of new blocks."""
    window_start = datetime.now(timezone.utc) - timedelta(minutes=1)
    threshold = settings.auto_block_requests_per_minute

    rows = (
        session.query(RequestLog.ip_address, func.count().label("cnt"))
        .filter(RequestLog.requested_at >= window_start)
        .group_by(RequestLog.ip_address)
        .having(func.count() > threshold)
        .all()
    )

    blocked_count = 0
    release_at = datetime.now(timezone.utc) + timedelta(hours=settings.auto_block_release_hours)

    for ip_address, _count in rows:
        existing = session.get(IpBlockList, ip_address)
        if existing:
            continue
        block = IpBlockList(
            ip_address=ip_address,
            reason=f"Auto-blocked: exceeded {threshold} requests/minute",
            blocked_at=datetime.now(timezone.utc),
            release_at=release_at,
            auto_blocked=True,
        )
        session.add(block)
        blocked_count += 1
        logger.warning("Auto-blocked IP %s (%d req/min threshold exceeded)", ip_address, threshold)

    if blocked_count:
        session.commit()

    return blocked_count


def _release_expired_blocks(session: Session) -> int:
    """Remove auto-blocks whose release_at has passed. Returns count removed."""
    now = datetime.now(timezone.utc)
    expired = (
        session.query(IpBlockList)
        .filter(IpBlockList.auto_blocked.is_(True), IpBlockList.release_at <= now)
        .all()
    )
    for block in expired:
        session.delete(block)
        logger.info("Released expired auto-block for IP %s", block.ip_address)
    if expired:
        session.commit()
    return len(expired)


class ThreatDetector:
    def __init__(self, session_maker: sessionmaker[Session], settings: Settings) -> None:
        self._session_maker = session_maker
        self._settings = settings
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="threat-detector")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while True:
            try:
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                await asyncio.get_event_loop().run_in_executor(None, self._check)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Threat detector error")

    def _check(self) -> None:
        session = self._session_maker()
        try:
            released = _release_expired_blocks(session)
            blocked = _detect_and_block(session, self._settings)
            if released or blocked:
                logger.info("Threat detector: +%d blocked, +%d released", blocked, released)
        finally:
            session.close()
