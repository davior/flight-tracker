#!/usr/bin/env python3
"""Database migration management script.

This script provides convenient commands for managing Alembic migrations.

Usage:
    python migrate.py upgrade       # Upgrade to latest migration
    python migrate.py downgrade     # Downgrade one migration
    python migrate.py current       # Show current migration
    python migrate.py history       # Show migration history
    python migrate.py create "message"  # Create new migration

Environment variables:
    DATABASE_URL - Database connection string (required)
                   Defaults to mysql+mysqlconnector://flightuser:flightpass@127.0.0.1:3306/flightlogs
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    alembic_cfg_path = Path(__file__).resolve().parent / "alembic.ini"
    cfg = Config(str(alembic_cfg_path))

    # Ensure DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = "mysql+mysqlconnector://flightuser:flightpass@127.0.0.1:3306/flightlogs"
        print(f"Warning: DATABASE_URL not set, using default: {database_url}")

    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def upgrade(revision: str = "head") -> None:
    """Upgrade database to a later version."""
    cfg = get_alembic_config()
    command.upgrade(cfg, revision)
    print(f"✓ Database upgraded to {revision}")


def downgrade(revision: str = "-1") -> None:
    """Revert database to a previous version."""
    cfg = get_alembic_config()
    command.downgrade(cfg, revision)
    print(f"✓ Database downgraded to {revision}")


def current() -> None:
    """Show current migration revision."""
    cfg = get_alembic_config()
    command.current(cfg)


def history() -> None:
    """Show migration history."""
    cfg = get_alembic_config()
    command.history(cfg)


def create(message: str, autogenerate: bool = True) -> None:
    """Create a new migration."""
    cfg = get_alembic_config()
    if autogenerate:
        command.revision(cfg, message=message, autogenerate=True)
        print(f"✓ Created new migration: {message}")
    else:
        command.revision(cfg, message=message)
        print(f"✓ Created blank migration: {message}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade(revision)
    elif cmd == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        downgrade(revision)
    elif cmd == "current":
        current()
    elif cmd == "history":
        history()
    elif cmd == "create":
        if len(sys.argv) < 3:
            print("Error: Migration message required")
            print('Usage: python migrate.py create "migration message"')
            sys.exit(1)
        message = sys.argv[2]
        autogenerate = "--no-autogenerate" not in sys.argv
        create(message, autogenerate)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
