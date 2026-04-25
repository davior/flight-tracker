#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import TextIO

from sqlalchemy.exc import DataError as SQLAlchemyDataError

from app.config import Settings, get_settings
from app.db import create_db_engine, create_session_maker
from app.migrations import run_migrations
from app.services.data_seeder import MAX_SYNC_ERROR_LENGTH, SOURCE_OPENSKY_AIRCRAFT, DataSeeder
from app.services.data_sync import DataSyncService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manually run backend data sync tasks.")
    parser.add_argument(
        "source",
        nargs="?",
        default=SOURCE_OPENSKY_AIRCRAFT,
        help="Data source to sync. Defaults to opensky_aircraft.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current sync status instead of running a sync.",
    )
    return parser


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    sync_service: DataSyncService | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    if sync_service is None:
        settings = settings or get_settings()
        settings.ensure_directories()
        engine = create_db_engine(settings.database_url)
        run_migrations(engine)
        session_maker = create_session_maker(engine)
        seeder = DataSeeder(settings, session_maker)
        sync_service = DataSyncService(settings, seeder, session_maker)
        should_close = True
    else:
        seeder = None
        engine = None
        should_close = False

    try:
        if args.status:
            for record in sync_service.list_sync_statuses():
                print(
                    f"{record.source}\t{record.last_sync_status or '-'}\t"
                    f"{record.row_count if record.row_count is not None else '-'}\t"
                    f"{record.last_synced_at.isoformat() if record.last_synced_at else '-'}",
                    file=stdout,
                )
            return 0

        count = sync_service.seed_source(args.source)
        print(f"Synced {args.source}: {count} rows", file=stdout)
        return 0
    except Exception as exc:
        message = _compact_exception_message(exc)
        print(f"Sync failed for {args.source}: {message}", file=stderr)
        return 1
    finally:
        if should_close:
            assert seeder is not None
            assert engine is not None
            seeder.close()
            engine.dispose()


def main() -> None:
    raise SystemExit(run_cli())


def _compact_exception_message(exc: Exception) -> str:
    if isinstance(exc, SQLAlchemyDataError):
        message = str(getattr(exc, "orig", exc))
    else:
        message = str(exc)
    if len(message) > MAX_SYNC_ERROR_LENGTH:
        message = f"{message[:MAX_SYNC_ERROR_LENGTH - 3]}..."
    return message


if __name__ == "__main__":
    main()
