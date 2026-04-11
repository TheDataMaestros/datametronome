"""012 — app-level settings (key-value, encrypted sensitive values).

Stores installation-level configuration such as the AI provider,
model name, and API key so they can be managed via the UI instead
of requiring environment variable changes + redeploy.

Revision ID: 012
Revises: 011
Create Date: 2026-04-09
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            is_encrypted INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)


def downgrade() -> None:
    dao.execute("DROP TABLE IF EXISTS app_settings")
