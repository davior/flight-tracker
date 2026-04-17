"""add media_type to flight_log_photos

Revision ID: d4e9f1a2b305
Revises: c5d8e3f9a012
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e9f1a2b305'
down_revision: Union[str, Sequence[str], None] = 'c5d8e3f9a012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add media_type column to flight_log_photos, defaulting existing rows to 'image'."""
    op.add_column(
        'flight_log_photos',
        sa.Column('media_type', sa.String(length=16), nullable=False, server_default='image'),
    )


def downgrade() -> None:
    op.drop_column('flight_log_photos', 'media_type')
