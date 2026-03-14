"""Add workflow state tables (checkpoints, definitions, events).

Revision ID: 002
Create Date: 2026-03-13
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE workflow_checkpoints (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        workflow_name TEXT NOT NULL,
        current_node TEXT,
        state_data JSONB,
        status TEXT NOT NULL DEFAULT 'running',
        parent_checkpoint_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (parent_checkpoint_id) REFERENCES workflow_checkpoints (id)
    )
    """)

    dao.execute("CREATE INDEX idx_wf_checkpoints_conversation ON workflow_checkpoints(conversation_id)")
    dao.execute("CREATE INDEX idx_wf_checkpoints_status ON workflow_checkpoints(status)")

    dao.execute("""
    CREATE TABLE workflow_definitions (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        graph_data JSONB,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    dao.execute("""
    CREATE TABLE workflow_events (
        id TEXT PRIMARY KEY,
        checkpoint_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        node_name TEXT,
        event_data JSONB,
        created_at TEXT NOT NULL,
        FOREIGN KEY (checkpoint_id) REFERENCES workflow_checkpoints (id)
    )
    """)

    dao.execute("CREATE INDEX idx_wf_events_checkpoint_created ON workflow_events(checkpoint_id, created_at)")


def downgrade() -> None:
    from alembic import op
    op.execute("DROP TABLE IF EXISTS workflow_events")
    op.execute("DROP TABLE IF EXISTS workflow_definitions")
    op.execute("DROP TABLE IF EXISTS workflow_checkpoints")
