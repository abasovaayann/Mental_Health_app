"""backfill legacy chat sessions

Revision ID: ed484f0a903b
Revises: bc9a96964317
Create Date: 2026-06-14 20:11:05.573552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed484f0a903b'
down_revision: Union[str, None] = 'bc9a96964317'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_TITLE = "Legacy conversation"


def upgrade() -> None:
    """Assign every pre-sessions chat message to a per-user legacy session.

    Mirrors the old boot-time ``_migrate_legacy_chat_messages`` helper: each
    user with messages that have no ``session_id`` gets a single
    "Legacy conversation" session, and those messages are linked to it.
    """
    bind = op.get_bind()

    user_ids = [
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT DISTINCT user_id FROM chat_messages "
                "WHERE session_id IS NULL"
            )
        )
    ]

    for user_id in user_ids:
        session_id = bind.execute(
            sa.text(
                "SELECT id FROM chat_sessions "
                "WHERE user_id = :user_id AND title = :title "
                "ORDER BY id ASC LIMIT 1"
            ),
            {"user_id": user_id, "title": LEGACY_TITLE},
        ).scalar()

        if session_id is None:
            bind.execute(
                sa.text(
                    "INSERT INTO chat_sessions (user_id, title) "
                    "VALUES (:user_id, :title)"
                ),
                {"user_id": user_id, "title": LEGACY_TITLE},
            )
            session_id = bind.execute(
                sa.text(
                    "SELECT id FROM chat_sessions "
                    "WHERE user_id = :user_id AND title = :title "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"user_id": user_id, "title": LEGACY_TITLE},
            ).scalar()

        bind.execute(
            sa.text(
                "UPDATE chat_messages SET session_id = :session_id "
                "WHERE user_id = :user_id AND session_id IS NULL"
            ),
            {"session_id": session_id, "user_id": user_id},
        )


def downgrade() -> None:
    """Detach messages from auto-created legacy sessions and drop them.

    Only sessions titled "Legacy conversation" are removed; their messages
    are reset to a NULL ``session_id`` so the data itself is preserved.
    """
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "UPDATE chat_messages SET session_id = NULL "
            "WHERE session_id IN ("
            "  SELECT id FROM chat_sessions WHERE title = :title"
            ")"
        ),
        {"title": LEGACY_TITLE},
    )
    bind.execute(
        sa.text("DELETE FROM chat_sessions WHERE title = :title"),
        {"title": LEGACY_TITLE},
    )
