"""Add dashboard_prefs TEXT column (JSON string) to users table.

Revision ID: 008
Revises: 007
Create Date: 2026-03-15
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stored as TEXT (JSON string). Default '{}' backfills all existing rows.
    dao.execute(
        "ALTER TABLE users ADD COLUMN dashboard_prefs TEXT NOT NULL DEFAULT '{}'"
    )


def downgrade() -> None:
    try:
        dao.execute("ALTER TABLE users DROP COLUMN dashboard_prefs")
    except Exception:
        pass  # SQLite < 3.35 doesn't support DROP COLUMN
