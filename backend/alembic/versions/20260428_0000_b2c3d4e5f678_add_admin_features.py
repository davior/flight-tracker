"""add admin features: is_admin/is_active on users, request_log, ip_block_list

Revision ID: b2c3d4e5f678
Revises: a1b2c3d4e567
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f678'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'request_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('method', sa.String(length=8), nullable=False),
        sa.Column('path', sa.String(length=512), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_request_log_requested_at', 'request_log', ['requested_at'], unique=False)
    op.create_index('ix_request_log_ip_requested_at', 'request_log', ['ip_address', 'requested_at'], unique=False)

    op.create_table(
        'ip_block_list',
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('release_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('blocked_by_user_id', sa.Integer(), nullable=True),
        sa.Column('auto_blocked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['blocked_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('ip_address'),
    )


def downgrade() -> None:
    op.drop_table('ip_block_list')
    op.drop_index('ix_request_log_ip_requested_at', table_name='request_log')
    op.drop_index('ix_request_log_requested_at', table_name='request_log')
    op.drop_table('request_log')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'is_admin')
