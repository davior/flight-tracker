from __future__ import annotations

from dataclasses import dataclass

from app.services.trajectory import build_trajectory


@dataclass
class FakeRecord:
    latitude: float
    longitude: float
    altitude: float | None
    heading: float | None
    velocity: float | None


class FakeTrajectoryProvider:
    def __init__(self, records: dict[int, FakeRecord | None]):
        self.records = records
        self.calls: list[tuple[str, int]] = []

    def get_flight_by_icao24(self, icao24: str, query_time: int):
        self.calls.append((icao24, query_time))
        return self.records.get(query_time)


def test_build_trajectory_returns_points_sorted_by_timestamp() -> None:
    provider = FakeTrajectoryProvider(
        records={
            940: FakeRecord(latitude=-37.81, longitude=144.96, altitude=1000.0, heading=90.0, velocity=150.0),
            880: FakeRecord(latitude=-37.82, longitude=144.97, altitude=1100.0, heading=95.0, velocity=148.0),
            820: FakeRecord(latitude=-37.83, longitude=144.98, altitude=1200.0, heading=100.0, velocity=146.0),
        }
    )

    points = build_trajectory(
        provider=provider,
        icao24="abc123",
        reference_time=1000,
        max_history_minutes=3,
        step_minutes=1,
    )

    assert [point.timestamp for point in points] == [820, 880, 940]


def test_build_trajectory_keeps_timestamp_order_with_gaps() -> None:
    provider = FakeTrajectoryProvider(
        records={
            940: FakeRecord(latitude=-37.81, longitude=144.96, altitude=1000.0, heading=90.0, velocity=150.0),
            880: None,
            820: FakeRecord(latitude=-37.83, longitude=144.98, altitude=1200.0, heading=100.0, velocity=146.0),
        }
    )

    points = build_trajectory(
        provider=provider,
        icao24="abc123",
        reference_time=1000,
        max_history_minutes=3,
        step_minutes=1,
    )

    assert [point.timestamp for point in points] == [820, 940]
