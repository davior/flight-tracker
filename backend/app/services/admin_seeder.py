from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.services.auth_service import hash_password

logger = logging.getLogger(__name__)


def seed_admin_user(session: Session, settings: Settings) -> None:
    """Create the admin user from env vars if it doesn't already exist."""
    email = settings.admin_email.lower().strip()
    existing = session.query(User).filter_by(email=email).first()
    if existing:
        # Ensure the existing record has admin privileges (idempotent upgrade)
        if not existing.is_admin:
            existing.is_admin = True
            session.commit()
            logger.info("Upgraded existing user %s to admin", email)
        return

    admin = User(
        email=email,
        username="admin",
        password_hash=hash_password(settings.admin_password),
        is_verified=True,
        is_admin=True,
        is_active=True,
        tutorial_seen=True,
    )
    session.add(admin)
    try:
        session.commit()
        logger.info("Seeded admin user: %s", email)
    except Exception:
        session.rollback()
        # Another process may have inserted concurrently — not fatal
        logger.warning("Admin user seed skipped (may already exist): %s", email)
