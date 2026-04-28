from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.dependencies import get_app_settings, get_current_admin
from app.models import IpBlockList, RequestLog
from app.schemas import IpBlockRequest, IpBlockResponse, RequestLogResponse

router = APIRouter(prefix="/logs", tags=["admin-logs"])


@router.get("/requests", response_model=dict)
def list_request_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    ip: str | None = Query(None),
    path: str | None = Query(None),
    status: int | None = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(RequestLog)
    if ip:
        q = q.filter(RequestLog.ip_address == ip)
    if path:
        q = q.filter(RequestLog.path.contains(path))
    if status:
        q = q.filter(RequestLog.status_code == status)
    total = q.count()
    items = q.order_by(RequestLog.requested_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [RequestLogResponse.model_validate(r) for r in items],
    }


@router.get("/blocked-ips", response_model=list[IpBlockResponse])
def list_blocked_ips(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return db.query(IpBlockList).order_by(IpBlockList.blocked_at.desc()).all()


@router.post("/blocked-ips", response_model=IpBlockResponse, status_code=201)
def block_ip(
    payload: IpBlockRequest,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    existing = db.get(IpBlockList, payload.ip_address)
    if existing:
        raise HTTPException(status_code=409, detail="IP is already blocked")
    release_at = None
    if payload.release_hours is not None:
        from datetime import timedelta
        release_at = datetime.now(timezone.utc) + timedelta(hours=payload.release_hours)
    block = IpBlockList(
        ip_address=payload.ip_address,
        reason=payload.reason,
        blocked_at=datetime.now(timezone.utc),
        release_at=release_at,
        blocked_by_user_id=admin.id,
        auto_blocked=False,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


@router.delete("/blocked-ips/{ip_address}", status_code=204)
def unblock_ip(
    ip_address: str,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    block = db.get(IpBlockList, ip_address)
    if not block:
        raise HTTPException(status_code=404, detail="IP not found in blocklist")
    db.delete(block)
    db.commit()


@router.post("/analyze-threats")
async def analyze_threats(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _admin=Depends(get_current_admin),
):
    from app.services.ai_service import query_ai

    result = await query_ai(
        question=(
            "Analyze the recent request_log data for suspicious patterns. "
            "Look for: unusually high request rates from single IPs, repeated 401/403 errors, "
            "scanning patterns (many different paths from one IP), and any other threats. "
            "List the top suspicious IPs with their request counts and patterns."
        ),
        session=db,
        settings=settings,
    )
    return result
