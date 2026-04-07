"""010 — add role column to users.

Revision ID: 010
Revises: 009
Create Date: 2026-04-07

Adds a role column (viewer / editor / admin) as the primary RBAC control.
is_superuser is kept in this migration for rollback safety; Task 17 drops it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role column with 'viewer' as the safe default so existing rows are
    # non-destructively backfilled before the explicit UPDATE passes below.
    dao.execute(
        "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'viewer'"
    )
    # Backfill: superusers become admin, all others stay viewer.
    dao.execute("UPDATE users SET role = 'admin' WHERE is_superuser = 1")
    # SQLite stores TRUE as 1; PostgreSQL stores it as TRUE — cover both.
    dao.execute("UPDATE users SET role = 'admin' WHERE is_superuser = TRUE")


def downgrade() -> None:
    # SQLite does not support DROP COLUMN on older versions, but the
    # DialectAwareOps wrapper handles dialect differences at the DDL level.
    dao.execute("ALTER TABLE users DROP COLUMN role")
