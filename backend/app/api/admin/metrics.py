from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_admin
from app.models import FlightLog, ProviderRequestLog, RequestLog, User
from app.schemas import DailyMetricPoint, MetricsOverviewResponse

router = APIRouter(prefix="/metrics", tags=["admin-metrics"])


@router.get("/overview", response_model=MetricsOverviewResponse)
def overview(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    admin_users = db.query(func.count(User.id)).filter(User.is_admin.is_(True)).scalar() or 0
    total_logs = db.query(func.count(FlightLog.id)).scalar() or 0
    requests_today = (
        db.query(func.count(RequestLog.id))
        .filter(RequestLog.requested_at >= today_start)
        .scalar()
        or 0
    )
    unique_visitors_today = (
        db.query(func.count(distinct(RequestLog.ip_address)))
        .filter(RequestLog.requested_at >= today_start)
        .scalar()
        or 0
    )
    requests_7d = (
        db.query(func.count(RequestLog.id))
        .filter(RequestLog.requested_at >= week_start)
        .scalar()
        or 0
    )
    return MetricsOverviewResponse(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        total_flight_logs=total_logs,
        requests_today=requests_today,
        unique_visitors_today=unique_visitors_today,
        requests_last_7_days=requests_7d,
    )


@router.get("/daily-visitors", response_model=list[DailyMetricPoint])
def daily_visitors(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(
            func.date(RequestLog.requested_at).label("day"),
            func.count(distinct(RequestLog.ip_address)).label("cnt"),
        )
        .filter(RequestLog.requested_at >= since)
        .group_by(func.date(RequestLog.requested_at))
        .order_by(func.date(RequestLog.requested_at))
        .all()
    )
    return [DailyMetricPoint(date=str(r.day), value=r.cnt) for r in rows]


@router.get("/daily-requests", response_model=list[DailyMetricPoint])
def daily_requests(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(
            func.date(RequestLog.requested_at).label("day"),
            func.count(RequestLog.id).label("cnt"),
        )
        .filter(RequestLog.requested_at >= since)
        .group_by(func.date(RequestLog.requested_at))
        .order_by(func.date(RequestLog.requested_at))
        .all()
    )
    return [DailyMetricPoint(date=str(r.day), value=r.cnt) for r in rows]


@router.get("/api-calls")
def api_call_stats(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    from sqlalchemy import case
    rows = (
        db.query(
            ProviderRequestLog.provider_name,
            func.count(ProviderRequestLog.id).label("total"),
            func.sum(case((ProviderRequestLog.success.is_(True), 1), else_=0)).label("successes"),
        )
        .filter(ProviderRequestLog.requested_at >= since)
        .group_by(ProviderRequestLog.provider_name)
        .all()
    )
    return [
        {
            "provider": r.provider_name,
            "total": r.total,
            "successes": int(r.successes or 0),
            "errors": r.total - int(r.successes or 0),
        }
        for r in rows
    ]
