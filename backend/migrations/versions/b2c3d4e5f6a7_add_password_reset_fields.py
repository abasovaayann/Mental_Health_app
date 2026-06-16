"""add password reset fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-16 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add one-active-code password-reset state to ``app_users``."""
    op.add_column(
        "app_users",
        sa.Column("reset_code_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "app_users",
        sa.Column("reset_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "app_users",
        sa.Column(
            "reset_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("app_users", "reset_attempts")
    op.drop_column("app_users", "reset_code_expires_at")
    op.drop_column("app_users", "reset_code_hash")
