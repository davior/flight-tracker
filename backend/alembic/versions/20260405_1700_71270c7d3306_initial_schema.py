"""initial schema

Revision ID: 71270c7d3306
Revises:
Create Date: 2026-04-05 17:00:48.932415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71270c7d3306'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create aircraft_categories table
    op.create_table(
        'aircraft_categories',
        sa.Column('code', sa.String(32), primary_key=True),
        sa.Column('label', sa.String(128), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
    )

    # Create aircraft_types table
    op.create_table(
        'aircraft_types',
        sa.Column('type_code', sa.String(8), primary_key=True),
        sa.Column('manufacturer', sa.String(128), nullable=True),
        sa.Column('model', sa.String(128), nullable=True),
        sa.Column('category', sa.String(16), nullable=True),
    )

    # Create aircraft_registry table
    op.create_table(
        'aircraft_registry',
        sa.Column('icao24', sa.String(6), primary_key=True),
        sa.Column('registration', sa.String(32), nullable=True),
        sa.Column('type_code', sa.String(8), nullable=True),
        sa.Column('manufacturer', sa.String(128), nullable=True),
        sa.Column('model', sa.String(128), nullable=True),
        sa.Column('category', sa.String(16), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_aircraft_registry_type_code', 'aircraft_registry', ['type_code'])

    # Create flight_logs table
    op.create_table(
        'flight_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('flight_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('icao24', sa.String(6), nullable=False),
        sa.Column('callsign', sa.String(16), nullable=True),
        sa.Column('origin_country', sa.String(64), nullable=True),
        sa.Column('departure_airport', sa.String(8), nullable=True),
        sa.Column('arrival_airport', sa.String(8), nullable=True),
        sa.Column('aircraft_latitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('aircraft_longitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('vertical_rate', sa.Float(), nullable=True),
        sa.Column('owner_uuid', sa.String(36), nullable=True),
        sa.Column('logger_name', sa.String(128), nullable=True),
        sa.Column('logger_location', sa.String(255), nullable=True),
        sa.Column('logger_latitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('logger_longitude', sa.Numeric(9, 6), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
    )
    op.create_index('ix_flight_logs_icao24', 'flight_logs', ['icao24'])
    op.create_index('ix_flight_logs_owner_uuid', 'flight_logs', ['owner_uuid'])

    # Create flight_log_photos table
    op.create_table(
        'flight_log_photos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('flight_log_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['flight_log_id'], ['flight_logs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_flight_log_photos_flight_log_id', 'flight_log_photos', ['flight_log_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('flight_log_photos')
    op.drop_table('flight_logs')
    op.drop_table('aircraft_registry')
    op.drop_table('aircraft_types')
    op.drop_table('aircraft_categories')
