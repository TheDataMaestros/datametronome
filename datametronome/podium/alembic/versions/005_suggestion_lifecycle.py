"""Suggestion lifecycle fields + notifications table.

Adds read_at, read_by, dismiss_reason, assigned_to, assigned_at to
insight_suggestions, and creates a new notifications table.

Revision ID: 005
Revises: 004
Create Date: 2026-03-15
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- insight_suggestions: add lifecycle columns ---
    dao.execute("ALTER TABLE insight_suggestions ADD COLUMN read_at TEXT")
    dao.execute("ALTER TABLE insight_suggestions ADD COLUMN read_by TEXT")
    dao.execute("ALTER TABLE insight_suggestions ADD COLUMN dismiss_reason TEXT")
    dao.execute("ALTER TABLE insight_suggestions ADD COLUMN assigned_to TEXT")
    dao.execute("ALTER TABLE insight_suggestions ADD COLUMN assigned_at TEXT")

    # --- notifications table ---
    dao.execute("""
    CREATE TABLE notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        reference_type TEXT NOT NULL DEFAULT 'suggestion',
        reference_id TEXT,
        read_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    dao.execute("CREATE INDEX idx_notifications_user_id ON notifications(user_id)")
    dao.execute("CREATE INDEX idx_notifications_read_at ON notifications(read_at)")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS notifications")
    # SQLite does not support DROP COLUMN in older versions; guard with try
    try:
        op.execute("ALTER TABLE insight_suggestions DROP COLUMN IF EXISTS assigned_at")
        op.execute("ALTER TABLE insight_suggestions DROP COLUMN IF EXISTS assigned_to")
        op.execute("ALTER TABLE insight_suggestions DROP COLUMN IF EXISTS dismiss_reason")
        op.execute("ALTER TABLE insight_suggestions DROP COLUMN IF EXISTS read_by")
        op.execute("ALTER TABLE insight_suggestions DROP COLUMN IF EXISTS read_at")
    except Exception:
        pass
