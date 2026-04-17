"""add users table and owner_id to flight_logs

Revision ID: c5d8e3f9a012
Revises: b3e7f2a1c904
Create Date: 2026-04-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d8e3f9a012'
down_revision: Union[str, Sequence[str], None] = 'b3e7f2a1c904'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table and add owner_id FK to flight_logs."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('verification_token_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('google_id', sa.String(length=255), nullable=True),
        sa.Column('tutorial_seen', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('google_id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.add_column(
        'flight_logs',
        sa.Column('owner_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_flight_logs_owner_id',
        'flight_logs', 'users',
        ['owner_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(op.f('ix_flight_logs_owner_id'), 'flight_logs', ['owner_id'], unique=False)


def downgrade() -> None:
    """Remove owner_id FK from flight_logs and drop users table."""
    op.drop_index(op.f('ix_flight_logs_owner_id'), table_name='flight_logs')
    op.drop_constraint('fk_flight_logs_owner_id', 'flight_logs', type_='foreignkey')
    op.drop_column('flight_logs', 'owner_id')

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
