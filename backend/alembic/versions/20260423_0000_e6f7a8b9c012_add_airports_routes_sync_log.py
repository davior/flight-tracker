"""add airports, flight_routes, and data_sync_log tables

Revision ID: e6f7a8b9c012
Revises: d4e9f1a2b305
Create Date: 2026-04-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e6f7a8b9c012'
down_revision: Union[str, None] = 'd4e9f1a2b305'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_sync_log',
        sa.Column('source', sa.String(64), primary_key=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(16), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
    )

    op.create_table(
        'airports',
        sa.Column('ident', sa.String(16), primary_key=True),
        sa.Column('type', sa.String(32), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('latitude_deg', sa.Float(), nullable=True),
        sa.Column('longitude_deg', sa.Float(), nullable=True),
        sa.Column('elevation_ft', sa.Integer(), nullable=True),
        sa.Column('continent', sa.String(4), nullable=True),
        sa.Column('iso_country', sa.String(4), nullable=True),
        sa.Column('municipality', sa.String(128), nullable=True),
        sa.Column('iata_code', sa.String(8), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_airports_iso_country', 'airports', ['iso_country'])
    op.create_index('ix_airports_iata_code', 'airports', ['iata_code'])

    op.create_table(
        'flight_routes',
        sa.Column('callsign', sa.String(16), primary_key=True),
        sa.Column('departure_icao', sa.String(8), nullable=True),
        sa.Column('arrival_icao', sa.String(8), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('flight_routes')
    op.drop_index('ix_airports_iata_code', table_name='airports')
    op.drop_index('ix_airports_iso_country', table_name='airports')
    op.drop_table('airports')
    op.drop_table('data_sync_log')
