"""add trajectory to flight_logs

Revision ID: b3e7f2a1c904
Revises: 71270c7d3306
Create Date: 2026-04-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e7f2a1c904'
down_revision: Union[str, Sequence[str], None] = '71270c7d3306'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trajectory JSON column to flight_logs."""
    op.add_column('flight_logs', sa.Column('trajectory', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove trajectory column from flight_logs."""
    op.drop_column('flight_logs', 'trajectory')
