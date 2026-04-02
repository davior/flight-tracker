from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AircraftCategory


@dataclass(frozen=True, slots=True)
class AircraftCategorySeed:
    code: str
    label: str
    description: str | None = None


AIRCRAFT_CATEGORY_SEEDS: tuple[AircraftCategorySeed, ...] = (
    AircraftCategorySeed("L", "Light", "Small aircraft in the light wake turbulence category."),
    AircraftCategorySeed("M", "Medium", "Aircraft in the medium wake turbulence category."),
    AircraftCategorySeed("H", "Heavy", "Large aircraft in the heavy wake turbulence category."),
    AircraftCategorySeed("J", "Super", "Very large aircraft in the super wake turbulence category."),
    AircraftCategorySeed("GLIDER", "Glider", "Engine-less glider or sailplane."),
    AircraftCategorySeed("HELICOPTER", "Helicopter", "Rotary-wing helicopter aircraft."),
    AircraftCategorySeed("GYROCOPTER", "Gyrocopter", "Autogyro or gyroplane aircraft."),
    AircraftCategorySeed("AIRSHIP", "Airship", "Lighter-than-air airship."),
    AircraftCategorySeed("BALLOON", "Balloon", "Lighter-than-air balloon."),
    AircraftCategorySeed("LANDPLANE", "Landplane", "Fixed-wing aircraft designed for land operation."),
    AircraftCategorySeed("SEAPLANE", "Seaplane", "Fixed-wing aircraft designed for water operation."),
    AircraftCategorySeed("AMPHIBIAN", "Amphibian", "Aircraft capable of operating from land and water."),
    AircraftCategorySeed("TILTROTOR", "Tiltrotor", "Aircraft using tilting rotors for lift and forward flight."),
    AircraftCategorySeed("ULTRALIGHT", "Ultralight", "Very light recreational aircraft."),
    AircraftCategorySeed("UAV", "Uncrewed", "Uncrewed or remotely piloted aircraft."),
)

AIRCRAFT_CATEGORY_ALIASES: dict[str, str] = {
    "LIGHT": "L",
    "MEDIUM": "M",
    "HEAVY": "H",
    "SUPER": "J",
    "GLID": "GLIDER",
    "GLIDER": "GLIDER",
    "SAILPLANE": "GLIDER",
    "HELI": "HELICOPTER",
    "HELICOPTER": "HELICOPTER",
    "ROTORCRAFT": "HELICOPTER",
    "GYROPLANE": "GYROCOPTER",
    "GYROCOPTER": "GYROCOPTER",
    "AUTOGYRO": "GYROCOPTER",
    "AIRSHIP": "AIRSHIP",
    "BLIMP": "AIRSHIP",
    "BALLOON": "BALLOON",
    "LANDPLANE": "LANDPLANE",
    "SEAPLANE": "SEAPLANE",
    "AMPHIBIAN": "AMPHIBIAN",
    "TILTROTOR": "TILTROTOR",
    "TILT_ROTOR": "TILTROTOR",
    "ULM": "ULTRALIGHT",
    "ULTRALIGHT": "ULTRALIGHT",
    "UAV": "UAV",
    "DRONE": "UAV",
}


def normalize_aircraft_category_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().upper().replace("-", " ").replace("_", " ").split())
    if not normalized:
        return None
    return AIRCRAFT_CATEGORY_ALIASES.get(normalized, normalized.replace(" ", "_"))


def seed_aircraft_categories(db_session: Session) -> None:
    existing_codes = set(db_session.execute(select(AircraftCategory.code)).scalars())
    for seed in AIRCRAFT_CATEGORY_SEEDS:
        if seed.code in existing_codes:
            continue
        db_session.add(
            AircraftCategory(
                code=seed.code,
                label=seed.label,
                description=seed.description,
            )
        )


def load_aircraft_category_map(
    db_session: Session,
    raw_categories: Iterable[str | None],
) -> dict[str, AircraftCategory]:
    category_codes = {
        normalize_aircraft_category_code(raw_category)
        for raw_category in raw_categories
        if normalize_aircraft_category_code(raw_category)
    }
    if not category_codes:
        return {}

    rows = db_session.execute(
        select(AircraftCategory).where(AircraftCategory.code.in_(category_codes))
    ).scalars()
    return {row.code: row for row in rows}


def resolve_aircraft_category_details(
    raw_category: str | None,
    category_map: dict[str, AircraftCategory],
) -> tuple[str | None, str | None, str | None]:
    normalized = normalize_aircraft_category_code(raw_category)
    if normalized is None:
        return None, None, None

    category = category_map.get(normalized)
    if category is None:
        fallback_label = raw_category.strip() if raw_category else normalized.replace("_", " ").title()
        return normalized, fallback_label, None

    return category.code, category.label, category.description
