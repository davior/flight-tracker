from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FlightLog(Base):
    __tablename__ = "flight_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    flight_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    icao24: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    callsign: Mapped[str | None] = mapped_column(String(16))
    origin_country: Mapped[str | None] = mapped_column(String(64))
    departure_airport: Mapped[str | None] = mapped_column(String(8))
    arrival_airport: Mapped[str | None] = mapped_column(String(8))
    aircraft_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    aircraft_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    altitude: Mapped[float | None] = mapped_column(Float)
    velocity: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float)
    vertical_rate: Mapped[float | None] = mapped_column(Float)
    owner_uuid: Mapped[str | None] = mapped_column(String(36), index=True)
    logger_name: Mapped[str | None] = mapped_column(String(128))
    logger_location: Mapped[str | None] = mapped_column(String(255))
    logger_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    logger_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    note: Mapped[str | None] = mapped_column(Text)

    photos: Mapped[list["FlightLogPhoto"]] = relationship(
        back_populates="flight_log",
        cascade="all, delete-orphan",
    )


class FlightLogPhoto(Base):
    __tablename__ = "flight_log_photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    flight_log_id: Mapped[int] = mapped_column(
        ForeignKey("flight_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    flight_log: Mapped[FlightLog] = relationship(back_populates="photos")


class AircraftRegistry(Base):
    __tablename__ = "aircraft_registry"

    icao24: Mapped[str] = mapped_column(String(6), primary_key=True)
    registration: Mapped[str | None] = mapped_column(String(32))
    type_code: Mapped[str | None] = mapped_column(String(8), index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(16))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class AircraftType(Base):
    __tablename__ = "aircraft_types"

    type_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(16))


class AircraftCategory(Base):
    __tablename__ = "aircraft_categories"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
