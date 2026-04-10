from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.dependencies import get_app_settings, get_current_user
from app.models import User
from app.schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import (
    create_access_token,
    generate_reset_token,
    generate_verification_token,
    hash_password,
    verify_password,
)
from app.services.email_service import send_password_reset_email, send_verification_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _is_token_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        return expires_at < datetime.utcnow()
    return expires_at < datetime.now(timezone.utc)


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_verified=user.is_verified,
        tutorial_seen=user.tutorial_seen,
    )


def _token_response(user: User, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, settings),
        token_type="bearer",
        user=_user_response(user),
    )


@router.post("/register", status_code=201)
async def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    email = payload.email.lower().strip()
    username = payload.username.lower().strip()

    if len(username) < 3:
        raise HTTPException(status_code=422, detail="Username must be at least 3 characters")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    existing = db.execute(select(User).where(or_(User.email == email, User.username == username))).scalar_one_or_none()
    if existing:
        if existing.email == email:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        raise HTTPException(status_code=409, detail="This username is already taken")

    token, expires = generate_verification_token()
    user = User(
        email=email,
        username=username,
        password_hash=hash_password(payload.password),
        is_verified=False,
        verification_token=token,
        verification_token_expires=expires,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        conflicting_user = db.execute(
            select(User).where(or_(User.email == email, User.username == username))
        ).scalar_one_or_none()
        if conflicting_user and conflicting_user.email == email:
            raise HTTPException(status_code=409, detail="An account with this email already exists") from None
        if conflicting_user and conflicting_user.username == username:
            raise HTTPException(status_code=409, detail="This username is already taken") from None
        logger.exception("Unexpected integrity error while creating user for %s", email)
        raise HTTPException(status_code=500, detail="Unable to create account at this time") from None
    db.refresh(user)

    await send_verification_email(email, token, settings)

    return {"message": "Registration successful. Please check your email to verify your account."}


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    login_value = payload.login.strip().lower()
    user = db.execute(
        select(User).where(or_(User.email == login_value, User.username == login_value))
    ).scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    return _token_response(user, settings)


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    user = db.execute(
        select(User).where(User.verification_token == payload.token)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    if _is_token_expired(user.verification_token_expires):
        raise HTTPException(status_code=400, detail="Verification token has expired. Please request a new one.")

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    db.refresh(user)

    return _token_response(user, settings)


@router.post("/resend-verification", status_code=200)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    if current_user.is_verified:
        return {"message": "Email is already verified"}

    token, expires = generate_verification_token()
    current_user.verification_token = token
    current_user.verification_token_expires = expires
    db.commit()

    await send_verification_email(current_user.email, token, settings)
    return {"message": "Verification email sent"}


@router.post("/forgot-password", status_code=200)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    # Always return 200 to avoid user enumeration
    email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        token, expires = generate_reset_token()
        user.password_reset_token = token
        user.password_reset_expires = expires
        db.commit()
        await send_password_reset_email(email, token, settings)
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", response_model=TokenResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    user = db.execute(
        select(User).where(User.password_reset_token == payload.token)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if _is_token_expired(user.password_reset_expires):
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    user.password_hash = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()
    db.refresh(user)

    return _token_response(user, settings)


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> TokenResponse:
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google authentication is not configured")

    google_user = await _verify_google_token(payload.id_token, settings.google_client_id)
    google_id = google_user["sub"]
    email = google_user.get("email", "").lower()

    # Find by google_id first, then by email
    user = db.execute(select(User).where(User.google_id == google_id)).scalar_one_or_none()
    if not user and email:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user:
        # Link google_id if not already set
        if not user.google_id:
            user.google_id = google_id
        if not user.is_verified:
            user.is_verified = True
        db.commit()
        db.refresh(user)
    else:
        # Create new Google-authenticated user
        if not email:
            raise HTTPException(status_code=400, detail="Google account must have an email address")
        base_username = email.split("@")[0]
        username = _unique_username(db, base_username)
        user = User(
            email=email,
            username=username,
            password_hash=None,
            is_verified=True,  # Google accounts are pre-verified
            google_id=google_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _token_response(user, settings)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return _user_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    if payload.username is not None:
        username = payload.username.lower().strip()
        if len(username) < 3:
            raise HTTPException(status_code=422, detail="Username must be at least 3 characters")
        if username != current_user.username:
            existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=409, detail="This username is already taken")
            current_user.username = username

    if payload.new_password is not None:
        if len(payload.new_password) < 8:
            raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
        if not payload.current_password:
            raise HTTPException(status_code=422, detail="current_password is required to set a new password")
        if not current_user.password_hash or not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        current_user.password_hash = hash_password(payload.new_password)

    db.commit()
    db.refresh(current_user)
    return _user_response(current_user)


@router.patch("/me/tutorial-seen", response_model=UserResponse)
def mark_tutorial_seen(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    current_user.tutorial_seen = True
    db.commit()
    db.refresh(current_user)
    return _user_response(current_user)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _verify_google_token(id_token: str, client_id: str) -> dict:
    """Validate a Google ID token and return the payload."""
    import httpx
    from jose import jwt as jose_jwt, JWTError

    # Fetch Google's public keys
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("https://www.googleapis.com/oauth2/v3/certs")
            resp.raise_for_status()
            certs = resp.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Failed to fetch Google public keys") from exc

    # Try each key until one validates the token
    for key_data in certs.get("keys", []):
        try:
            from jose.backends import RSAKey
            public_key = RSAKey(key_data, algorithm="RS256")
            payload = jose_jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=client_id,
            )
            return payload
        except JWTError:
            continue

    raise HTTPException(status_code=401, detail="Invalid Google ID token")


def _unique_username(db: Session, base: str) -> str:
    """Return a username derived from base that doesn't already exist."""
    # Sanitize: keep only alphanumeric and underscores, max 60 chars
    sanitized = "".join(c for c in base if c.isalnum() or c == "_")[:60] or "user"
    candidate = sanitized
    suffix = 1
    while db.execute(select(User).where(User.username == candidate)).scalar_one_or_none():
        candidate = f"{sanitized}{suffix}"
        suffix += 1
    return candidate
