from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings

logger = logging.getLogger(__name__)

_PROVIDER_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "ollama": "http://localhost:11434/v1",
    "openai": None,  # uses default openai base URL
}

_SYSTEM_PROMPT = """You are an AI analyst for the Chemtrail Tracker admin panel.
You have access to a MySQL database with the following tables:
- users(id, email, username, is_verified, is_admin, is_active, created_at)
- flight_logs(id, created_at, flight_time, icao24, callsign, origin_country, altitude, velocity, owner_id)
- aircraft_registry(icao24, registration, manufacturer, model, operator)
- airports(ident, name, municipality, iso_country)
- provider_request_log(provider_name, requested_at, success, error_code)
- request_log(ip_address, method, path, status_code, duration_ms, requested_at)
- data_sync_log(source, last_synced_at, last_sync_status, row_count)

Answer questions concisely. When showing data that can be charted, include a JSON block like:
CHART_TYPE: bar|line|pie|doughnut
CHART_DATA: {"labels": [...], "datasets": [{"label": "...", "data": [...]}]}

If the question cannot be answered from the available data, say so clearly."""


def _build_context(session: Session, question: str) -> str:
    """Pull lightweight summary stats to give the AI grounding context."""
    from app.models import User, FlightLog, ProviderRequestLog, DataSyncLog, RequestLog
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    user_count = session.query(func.count(User.id)).scalar() or 0
    log_count = session.query(func.count(FlightLog.id)).scalar() or 0
    req_today = (
        session.query(func.count(RequestLog.id))
        .filter(RequestLog.requested_at >= today_start)
        .scalar()
        or 0
    )
    provider_week = (
        session.query(ProviderRequestLog.provider_name, func.count())
        .filter(ProviderRequestLog.requested_at >= week_start)
        .group_by(ProviderRequestLog.provider_name)
        .all()
    )
    sync_statuses = session.query(DataSyncLog).all()

    lines = [
        f"Current stats (as of {now.strftime('%Y-%m-%d %H:%M UTC')}):",
        f"- Total users: {user_count}",
        f"- Total flight logs: {log_count}",
        f"- HTTP requests today: {req_today}",
        f"- Provider API calls last 7 days: {dict(provider_week)}",
        "- Data sync status:",
    ]
    for s in sync_statuses:
        lines.append(f"  {s.source}: {s.last_sync_status}, rows={s.row_count}, last={s.last_synced_at}")

    return "\n".join(lines)


def _parse_chart(text: str) -> tuple[str, str | None, dict | None]:
    """Extract optional CHART_TYPE / CHART_DATA blocks from AI response text."""
    chart_type: str | None = None
    chart_data: dict | None = None
    clean_lines = []

    i = 0
    lines = text.splitlines()
    while i < len(lines):
        line = lines[i]
        if line.startswith("CHART_TYPE:"):
            chart_type = line.split(":", 1)[1].strip()
        elif line.startswith("CHART_DATA:"):
            raw = line.split(":", 1)[1].strip()
            try:
                chart_data = json.loads(raw)
            except json.JSONDecodeError:
                pass
        else:
            clean_lines.append(line)
        i += 1

    return "\n".join(clean_lines).strip(), chart_type, chart_data


async def query_ai(
    question: str,
    session: Session,
    settings: Settings,
    context_hint: str | None = None,
) -> dict[str, Any]:
    if not settings.ai_api_key:
        return {
            "answer": (
                "AI analysis is not configured. "
                "Set AI_API_KEY (and optionally AI_BASE_URL) in your .env to enable this feature."
            ),
            "chart_type": None,
            "chart_data": None,
            "model_used": None,
        }

    try:
        from openai import AsyncOpenAI
    except ImportError:
        return {
            "answer": "The 'openai' Python package is not installed. Run: pip install openai",
            "chart_type": None,
            "chart_data": None,
            "model_used": None,
        }

    base_url = settings.ai_base_url or _PROVIDER_URLS.get(settings.ai_provider)
    client = AsyncOpenAI(api_key=settings.ai_api_key, base_url=base_url)

    db_context = _build_context(session, question)
    user_message = question
    if context_hint:
        user_message = f"{question}\n\nAdditional context: {context_hint}"

    try:
        completion = await client.chat.completions.create(
            model=settings.ai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Database context:\n{db_context}\n\nQuestion: {user_message}"},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        raw_answer = completion.choices[0].message.content or ""
        answer, chart_type, chart_data = _parse_chart(raw_answer)
        return {
            "answer": answer,
            "chart_type": chart_type,
            "chart_data": chart_data,
            "model_used": settings.ai_model,
        }
    except Exception as exc:
        logger.error("AI query failed: %s", exc)
        return {
            "answer": f"AI query failed: {exc}",
            "chart_type": None,
            "chart_data": None,
            "model_used": settings.ai_model,
        }
