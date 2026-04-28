from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.models import IpBlockList, RequestLog

logger = logging.getLogger(__name__)

# Paths we skip logging entirely (high-frequency health/static noise)
_SKIP_PATHS = frozenset(["/health", "/favicon.ico", "/docs", "/openapi.json", "/redoc"])


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _is_blocked(session: Session, ip: str) -> bool:
    now = datetime.now(timezone.utc)
    block = session.get(IpBlockList, ip)
    if block is None:
        return False
    if block.release_at is not None and block.release_at <= now:
        session.delete(block)
        session.commit()
        return False
    return True


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Logs every request and enforces IP blocklist. Reads session_maker from app.state."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        session_maker = getattr(request.app.state, "session_maker", None)
        if session_maker is None:
            # App not fully initialised yet (e.g. during startup)
            return await call_next(request)

        ip = _get_client_ip(request)
        session = session_maker()
        try:
            if _is_blocked(session, ip):
                return Response(
                    content='{"detail":"Your IP address has been blocked"}',
                    status_code=403,
                    media_type="application/json",
                )
        finally:
            session.close()

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        user_id: int | None = getattr(request.state, "user_id", None)

        session = session_maker()
        try:
            entry = RequestLog(
                ip_address=ip,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                requested_at=datetime.now(timezone.utc),
            )
            session.add(entry)
            session.commit()
        except Exception:
            session.rollback()
            logger.debug("Failed to write request log", exc_info=True)
        finally:
            session.close()

        return response
