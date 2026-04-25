from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Airport
from app.schemas import AirportResponse

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get("/{ident}", response_model=AirportResponse)
def get_airport(
    ident: str,
    db_session: Session = Depends(get_db),
) -> AirportResponse:
    airport = db_session.get(Airport, ident.upper())
    if airport is None:
        raise HTTPException(status_code=404, detail="Airport not found")
    return AirportResponse.model_validate(airport)


@router.get("", response_model=list[AirportResponse])
def search_airports(
    q: str = Query(..., min_length=2, max_length=64),
    limit: int = Query(default=10, ge=1, le=50),
    db_session: Session = Depends(get_db),
) -> list[AirportResponse]:
    pattern = f"{q.upper()}%"
    results = db_session.execute(
        select(Airport)
        .where(
            or_(
                Airport.ident.like(pattern),
                Airport.iata_code.like(pattern),
                Airport.name.ilike(f"{q}%"),
            )
        )
        .order_by(Airport.ident)
        .limit(limit)
    ).scalars().all()
    return [AirportResponse.model_validate(r) for r in results]
