"""Agent-generated BI query plans: stave_query_plans + schema_interpretation on data_profiles.

Revision ID: 007
Revises: 006
Create Date: 2026-03-16
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

logger = logging.getLogger(__name__)

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE stave_query_plans (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        schema_fingerprint TEXT NOT NULL,
        kpi_queries TEXT NOT NULL DEFAULT '{}',
        performer_queries TEXT NOT NULL DEFAULT '{}',
        generated_by_model TEXT NOT NULL DEFAULT '',
        generated_at TEXT NOT NULL,
        skipped TEXT NOT NULL DEFAULT '[]',
        invalidated_at TEXT,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)
    dao.execute(
        "CREATE INDEX idx_stave_query_plans_stave_id ON stave_query_plans(stave_id)"
    )
    # Partial unique index: at most one valid (non-invalidated) plan per stave
    # Supported by SQLite >= 3.8.9 and PostgreSQL
    dao.execute(
        "CREATE UNIQUE INDEX idx_stave_query_plans_valid "
        "ON stave_query_plans(stave_id) WHERE invalidated_at IS NULL"
    )
    # Use dao.execute (not op.execute) so DialectAwareOps handles JSONB->TEXT substitution on SQLite.
    # data_profiles was created with TEXT for JSON fields; schema_interpretation follows the same pattern.
    dao.execute(
        "ALTER TABLE data_profiles ADD COLUMN schema_interpretation TEXT NOT NULL DEFAULT '{}'"
    )


def downgrade() -> None:
    # Use dao.execute throughout (not op.execute) for dialect-safe execution
    dao.execute("DROP TABLE IF EXISTS stave_query_plans")
    # DROP COLUMN is best-effort: SQLite < 3.35 cannot do it at all; wrap for safety.
    try:
        dao.execute(
            "ALTER TABLE data_profiles DROP COLUMN schema_interpretation"
        )
    except Exception as exc:
        logger.warning("Could not drop schema_interpretation column (safe to ignore on SQLite): %s", exc)
