from __future__ import annotations

import asyncio

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, text
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


def get_db(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_maker()
    try:
        yield session
    finally:
        session.close()
