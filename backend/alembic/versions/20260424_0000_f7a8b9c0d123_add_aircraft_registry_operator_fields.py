"""add operator and ownership fields to aircraft_registry

Revision ID: f7a8b9c0d123
Revises: e6f7a8b9c012
Create Date: 2026-04-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d123"
down_revision: Union[str, None] = "e6f7a8b9c012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("aircraft_registry", sa.Column("operator", sa.String(128), nullable=True))
    op.add_column("aircraft_registry", sa.Column("operator_icao", sa.String(8), nullable=True))
    op.add_column("aircraft_registry", sa.Column("operator_iata", sa.String(8), nullable=True))
    op.add_column("aircraft_registry", sa.Column("operator_callsign", sa.String(64), nullable=True))
    op.add_column("aircraft_registry", sa.Column("owner", sa.String(128), nullable=True))
    op.add_column("aircraft_registry", sa.Column("serial_number", sa.String(32), nullable=True))
    op.add_column("aircraft_registry", sa.Column("year_built", sa.String(4), nullable=True))
    op.add_column("aircraft_registry", sa.Column("engines", sa.String(128), nullable=True))
    op.add_column("aircraft_registry", sa.Column("icao_aircraft_type", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("aircraft_registry", "icao_aircraft_type")
    op.drop_column("aircraft_registry", "engines")
    op.drop_column("aircraft_registry", "year_built")
    op.drop_column("aircraft_registry", "serial_number")
    op.drop_column("aircraft_registry", "owner")
    op.drop_column("aircraft_registry", "operator_callsign")
    op.drop_column("aircraft_registry", "operator_iata")
    op.drop_column("aircraft_registry", "operator_icao")
    op.drop_column("aircraft_registry", "operator")
