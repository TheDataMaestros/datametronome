"""Intelligence Store tables: data_profiles, baseline_snapshots, insight_reports,
insight_suggestions, insight_created_checks.

Revision ID: 004
Revises: d4fa342314f0
Create Date: 2026-03-15
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "004"
down_revision = "d4fa342314f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE data_profiles (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL UNIQUE,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        domain_type TEXT NOT NULL,
        domain_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
        domain_context TEXT NOT NULL DEFAULT '{}',
        schema_map TEXT NOT NULL DEFAULT '{}',
        entity_roles TEXT NOT NULL DEFAULT '{}',
        learned_patterns TEXT NOT NULL DEFAULT '{}',
        profile_version INTEGER NOT NULL DEFAULT 1,
        previous_classification TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE baseline_snapshots (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        snapshot_type TEXT NOT NULL,
        table_metrics TEXT NOT NULL DEFAULT '{}',
        column_stats TEXT NOT NULL DEFAULT '{}',
        captured_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE insight_reports (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        snapshot_id TEXT,
        report_type TEXT NOT NULL,
        health_score INTEGER NOT NULL DEFAULT 0,
        dimensions TEXT NOT NULL DEFAULT '[]',
        anomalies TEXT NOT NULL DEFAULT '[]',
        suggestions TEXT NOT NULL DEFAULT '[]',
        summary TEXT NOT NULL DEFAULT '',
        key_findings TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE,
        FOREIGN KEY (snapshot_id) REFERENCES baseline_snapshots (id) ON DELETE SET NULL
    )
    """)

    dao.execute("""
    CREATE TABLE insight_suggestions (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        report_id TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'medium',
        category TEXT NOT NULL,
        action TEXT NOT NULL,
        reasoning TEXT NOT NULL,
        based_on TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        resolved_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id) ON DELETE CASCADE,
        FOREIGN KEY (report_id) REFERENCES insight_reports (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE insight_created_checks (
        id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        clef_id TEXT NOT NULL,
        rationale TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (report_id) REFERENCES insight_reports (id) ON DELETE CASCADE,
        FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
    )
    """)

    # Indexes
    dao.execute("CREATE INDEX idx_data_profiles_stave_id ON data_profiles(stave_id)")
    dao.execute("CREATE INDEX idx_data_profiles_tenant_id ON data_profiles(tenant_id)")
    dao.execute("CREATE INDEX idx_baseline_snapshots_stave_id ON baseline_snapshots(stave_id)")
    dao.execute("CREATE INDEX idx_baseline_snapshots_captured_at ON baseline_snapshots(captured_at)")
    dao.execute("CREATE INDEX idx_insight_reports_stave_id ON insight_reports(stave_id)")
    dao.execute("CREATE INDEX idx_insight_reports_created_at ON insight_reports(created_at)")
    dao.execute("CREATE INDEX idx_insight_suggestions_stave_id ON insight_suggestions(stave_id)")
    dao.execute("CREATE INDEX idx_insight_suggestions_status ON insight_suggestions(status)")
    dao.execute("CREATE INDEX idx_insight_created_checks_report_id ON insight_created_checks(report_id)")
    dao.execute("CREATE INDEX idx_insight_created_checks_clef_id ON insight_created_checks(clef_id)")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP TABLE IF EXISTS insight_created_checks")
    op.execute("DROP TABLE IF EXISTS insight_suggestions")
    op.execute("DROP TABLE IF EXISTS insight_reports")
    op.execute("DROP TABLE IF EXISTS baseline_snapshots")
    op.execute("DROP TABLE IF EXISTS data_profiles")
