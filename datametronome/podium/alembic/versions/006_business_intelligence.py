"""Business intelligence: business_reports table + check_spec on suggestions.

Revision ID: 006
Revises: 005
Create Date: 2026-03-15
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE business_reports (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        snapshot_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        business_health_score INTEGER NOT NULL DEFAULT 0,
        executive_summary TEXT NOT NULL DEFAULT '',
        kpis TEXT NOT NULL DEFAULT '[]',
        top_performers TEXT NOT NULL DEFAULT '[]',
        bottom_performers TEXT NOT NULL DEFAULT '[]',
        trends TEXT NOT NULL DEFAULT '[]',
        opportunities TEXT NOT NULL DEFAULT '[]',
        risks TEXT NOT NULL DEFAULT '[]',
        generated_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)
    dao.execute(
        "CREATE INDEX idx_business_reports_stave_id ON business_reports(stave_id)"
    )
    dao.execute(
        "CREATE INDEX idx_business_reports_generated_at ON business_reports(generated_at)"
    )
    dao.execute("ALTER TABLE insight_suggestions ADD COLUMN check_spec TEXT")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS business_reports")
    try:
        op.execute(
            "ALTER TABLE insight_suggestions DROP COLUMN IF EXISTS check_spec"
        )
    except Exception:
        pass
