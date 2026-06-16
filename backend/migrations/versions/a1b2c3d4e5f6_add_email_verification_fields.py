"""add email verification fields

Revision ID: a1b2c3d4e5f6
Revises: ed484f0a903b
Create Date: 2026-06-16 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ed484f0a903b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add one-active-code email-verification state to ``app_users``.

    Existing users predate the verification feature, so they are backfilled as
    verified — otherwise their reminders (which now require a verified email)
    would stop. Only new signups must verify.
    """
    op.add_column(
        "app_users",
        sa.Column("verification_code_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "app_users",
        sa.Column(
            "verification_code_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "app_users",
        sa.Column(
            "verification_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # Grandfather existing accounts so their reminders keep working.
    op.execute("UPDATE app_users SET is_verified = true WHERE is_verified = false")


def downgrade() -> None:
    """Drop the verification columns (the is_verified backfill is left as-is)."""
    op.drop_column("app_users", "verification_attempts")
    op.drop_column("app_users", "verification_code_expires_at")
    op.drop_column("app_users", "verification_code_hash")
