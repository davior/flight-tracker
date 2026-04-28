from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_admin
from app.models import FlightLog, User
from app.schemas import (
    AdminSetPasswordRequest,
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.services.auth_service import hash_password
from app.services.email_service import send_password_reset_email
from app.config import Settings
from app.dependencies import get_app_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["admin-users"])


def _user_response(user: User, session: Session) -> AdminUserResponse:
    count = session.query(func.count(FlightLog.id)).filter(FlightLog.owner_id == user.id).scalar() or 0
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        is_active=user.is_active,
        tutorial_seen=user.tutorial_seen,
        created_at=user.created_at,
        flight_log_count=count,
    )


@router.get("/", response_model=dict)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(User)
    if search:
        term = f"%{search.lower()}%"
        q = q.filter((func.lower(User.email).like(term)) | (func.lower(User.username).like(term)))
    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [_user_response(u, db) for u in users],
    }


@router.post("/", response_model=AdminUserResponse, status_code=201)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    email = payload.email.lower().strip()
    username = payload.username.lower().strip()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="Email already in use")
    if db.query(User).filter_by(username=username).first():
        raise HTTPException(status_code=409, detail="Username already in use")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    user = User(
        email=email,
        username=username,
        password_hash=hash_password(payload.password),
        is_verified=True,
        is_admin=payload.is_admin,
        is_active=True,
        tutorial_seen=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user, db)


@router.get("/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_response(user, db)


@router.patch("/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.email is not None:
        email = payload.email.lower().strip()
        conflict = db.query(User).filter(User.email == email, User.id != user_id).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = email
    if payload.username is not None:
        username = payload.username.lower().strip()
        conflict = db.query(User).filter(User.username == username, User.id != user_id).first()
        if conflict:
            raise HTTPException(status_code=409, detail="Username already in use")
        user.username = username
    if payload.is_admin is not None:
        if user.id == admin.id and not payload.is_admin:
            raise HTTPException(status_code=400, detail="Cannot remove your own admin privileges")
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        if user.id == admin.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot disable your own account")
        user.is_active = payload.is_active
    if payload.is_verified is not None:
        user.is_verified = payload.is_verified
    db.commit()
    db.refresh(user)
    return _user_response(user, db)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()


@router.post("/{user_id}/set-password", status_code=200)
def set_password(
    user_id: int,
    payload: AdminSetPasswordRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.post("/{user_id}/send-reset", status_code=200)
async def send_password_reset(
    user_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _admin=Depends(get_current_admin),
):
    from app.services.auth_service import generate_reset_token

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token, expires_at = generate_reset_token()
    user.password_reset_token = token
    user.password_reset_expires = expires_at
    db.commit()
    await send_password_reset_email(user.email, token, settings)
    return {"message": f"Password reset email sent to {user.email}"}
