"""011 — drop is_superuser column from users.

Revision ID: 011
Revises: 010
Create Date: 2026-04-07

The role column (added in 010) is the sole RBAC control.
is_superuser has been backfilled to role='admin' and all code
references have been removed; this migration finalises the drop.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("ALTER TABLE users DROP COLUMN is_superuser")


def downgrade() -> None:
    # Re-add is_superuser and backfill from role so rollback is data-safe.
    dao.execute(
        "ALTER TABLE users ADD COLUMN is_superuser BOOLEAN NOT NULL DEFAULT FALSE"
    )
    dao.execute("UPDATE users SET is_superuser = TRUE WHERE role = 'admin'")
