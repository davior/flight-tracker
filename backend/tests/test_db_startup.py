from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.exc import OperationalError

from app.db import wait_for_database


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, _statement):
        return None


class _FlakyEngine:
    def __init__(self, failures: int):
        self.failures_remaining = failures
        self.attempts = 0

    def connect(self):
        self.attempts += 1
        if self.failures_remaining > 0:
            self.failures_remaining -= 1
            raise OperationalError("SELECT 1", {}, Exception("db unavailable"))
        return _FakeConnection()


def test_wait_for_database_retries_until_connection_succeeds():
    async def run():
        engine = _FlakyEngine(failures=2)

        await wait_for_database(engine, max_attempts=3, retry_delay_seconds=0)

        assert engine.attempts == 3

    asyncio.run(run())


def test_wait_for_database_raises_after_final_attempt():
    async def run():
        engine = _FlakyEngine(failures=3)

        with pytest.raises(OperationalError):
            await wait_for_database(engine, max_attempts=3, retry_delay_seconds=0)

        assert engine.attempts == 3

    asyncio.run(run())
