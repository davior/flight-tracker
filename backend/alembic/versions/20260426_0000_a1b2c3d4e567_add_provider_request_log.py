"""add provider_request_log table

Revision ID: a1b2c3d4e567
Revises: f7a8b9c0d123
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e567"
down_revision: Union[str, None] = "f7a8b9c0d123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_request_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider_name", sa.String(64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_request_log_provider_requested_at",
        "provider_request_log",
        ["provider_name", "requested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_request_log_provider_requested_at", table_name="provider_request_log")
    op.drop_table("provider_request_log")
