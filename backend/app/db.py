from __future__ import annotations

import asyncio

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Base declarative model."""


def create_db_engine(database_url: str):
    engine_kwargs: dict[str, object] = {"future": True}

    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"} or ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(database_url, **engine_kwargs)


def create_session_maker(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def wait_for_database(engine, max_attempts: int, retry_delay_seconds: float) -> None:
    last_error: SQLAlchemyError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except SQLAlchemyError as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            await asyncio.sleep(retry_delay_seconds)

    if last_error is not None:
        raise last_error


def ensure_flight_log_schema(engine) -> None:
    inspector = inspect(engine)
    if "flight_logs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("flight_logs")}
    if "flight_time" in existing_columns:
        return

    dialect_name = engine.dialect.name
    with engine.begin() as connection:
        if dialect_name == "sqlite":
            connection.execute(text("ALTER TABLE flight_logs ADD COLUMN flight_time DATETIME"))
            connection.execute(text("UPDATE flight_logs SET flight_time = created_at WHERE flight_time IS NULL"))
            return

        connection.execute(text("ALTER TABLE flight_logs ADD COLUMN flight_time DATETIME NULL"))
        connection.execute(text("UPDATE flight_logs SET flight_time = created_at WHERE flight_time IS NULL"))
        connection.execute(text("ALTER TABLE flight_logs MODIFY COLUMN flight_time DATETIME NOT NULL"))


def get_db(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_maker()
    try:
        yield session
    finally:
        session.close()
