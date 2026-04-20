from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from app.db import Base


def run_migrations(engine: Engine | None = None) -> None:
    """Run Alembic migrations to upgrade database to latest version.

    For in-memory or test databases, falls back to create_all instead of migrations.

    Args:
        engine: Optional SQLAlchemy engine. If provided and using SQLite in-memory,
                will use create_all instead of migrations.
    """
    # For SQLite databases (testing), use create_all instead of migrations
    # SQLite doesn't work well with Alembic for testing since we use temp databases
    if engine and engine.url.drivername == "sqlite":
        Base.metadata.create_all(bind=engine)
        return

    # For regular databases, run migrations
    alembic_cfg_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_cfg = Config(str(alembic_cfg_path))

    from app.config import _build_database_url
    alembic_cfg.set_main_option("sqlalchemy.url", _build_database_url().replace("%", "%%"))

    # Pass the existing engine connection so env.py doesn't create a second
    # engine (which can hang with some drivers / MariaDB versions).
    if engine is not None:
        with engine.connect() as connection:
            alembic_cfg.attributes["connection"] = connection
            command.upgrade(alembic_cfg, "head")
    else:
        command.upgrade(alembic_cfg, "head")


def create_migration(message: str, autogenerate: bool = True) -> None:
    """Create a new migration."""
    alembic_cfg_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    alembic_cfg = Config(str(alembic_cfg_path))
    if autogenerate:
        command.revision(alembic_cfg, message=message, autogenerate=True)
    else:
        command.revision(alembic_cfg, message=message)
