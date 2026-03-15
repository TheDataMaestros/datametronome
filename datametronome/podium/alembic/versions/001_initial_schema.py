"""Initial schema — all core tables.

Revision ID: 001
Create Date: 2026-03-13

NOTE: Migrations are written in PostgreSQL dialect. The DialectAwareOps.execute()
wrapper in env.py translates JSONB->TEXT and DOUBLE PRECISION->REAL for SQLite.
Do NOT use IF NOT EXISTS — Alembic tracks versions, so each migration runs once.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        is_superuser BOOLEAN DEFAULT FALSE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    dao.execute("""
    CREATE TABLE staves (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        data_source_type TEXT NOT NULL,
        connection_config TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    dao.execute("""
    CREATE TABLE clefs (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        check_type TEXT NOT NULL,
        config TEXT NOT NULL,
        warn TEXT,
        fail TEXT,
        retry_config TEXT,
        schedule TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (stave_id) REFERENCES staves (id)
    )
    """)

    dao.execute("""
    CREATE TABLE checks (
        id TEXT PRIMARY KEY,
        stave_id TEXT NOT NULL,
        clef_id TEXT NOT NULL,
        check_type TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT,
        details TEXT,
        timestamp TEXT NOT NULL,
        execution_time DOUBLE PRECISION,
        anomalies_count INTEGER DEFAULT 0,
        severity TEXT DEFAULT 'medium',
        FOREIGN KEY (stave_id) REFERENCES staves (id),
        FOREIGN KEY (clef_id) REFERENCES clefs (id)
    )
    """)

    dao.execute("""
    CREATE TABLE scheduler_jobs (
        id TEXT PRIMARY KEY,
        clef_id TEXT NOT NULL,
        schedule TEXT NOT NULL,
        enabled BOOLEAN DEFAULT TRUE,
        last_run_time TEXT,
        next_run_time TEXT,
        execution_count INTEGER DEFAULT 0,
        failure_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE job_executions (
        id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        clef_id TEXT NOT NULL,
        status TEXT NOT NULL,
        execution_time DOUBLE PRECISION,
        error_message TEXT,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY (job_id) REFERENCES scheduler_jobs (id) ON DELETE CASCADE,
        FOREIGN KEY (clef_id) REFERENCES clefs (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE anomalies (
        id TEXT PRIMARY KEY,
        check_id TEXT NOT NULL,
        table_name TEXT,
        column_name TEXT,
        anomaly_type TEXT NOT NULL,
        description TEXT,
        severity TEXT DEFAULT 'medium',
        detected_at TEXT NOT NULL,
        data_sample TEXT,
        resolution_status TEXT DEFAULT 'investigating',
        FOREIGN KEY (check_id) REFERENCES checks (id)
    )
    """)

    dao.execute("""
    CREATE TABLE chat_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        tool_calls TEXT,
        tool_results TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    dao.execute("""
    CREATE TABLE agent_traces (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        user_message_preview TEXT,
        intent TEXT,
        model TEXT,
        tool_calls TEXT,
        duration_ms DOUBLE PRECISION,
        created_at TEXT NOT NULL
    )
    """)

    # Indexes
    dao.execute("CREATE INDEX idx_chat_messages_conversation_id ON chat_messages(conversation_id)")
    dao.execute("CREATE INDEX idx_chat_messages_user_id ON chat_messages(user_id)")
    dao.execute("CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at)")
    dao.execute("CREATE INDEX idx_agent_traces_conversation_id ON agent_traces(conversation_id)")
    dao.execute("CREATE INDEX idx_agent_traces_user_id ON agent_traces(user_id)")
    dao.execute("CREATE INDEX idx_agent_traces_created_at ON agent_traces(created_at)")
    dao.execute("CREATE INDEX idx_agent_traces_intent ON agent_traces(intent)")


def downgrade() -> None:
    from alembic import op
    op.execute("DROP TABLE IF EXISTS agent_traces")
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("DROP TABLE IF EXISTS anomalies")
    op.execute("DROP TABLE IF EXISTS job_executions")
    op.execute("DROP TABLE IF EXISTS scheduler_jobs")
    op.execute("DROP TABLE IF EXISTS checks")
    op.execute("DROP TABLE IF EXISTS clefs")
    op.execute("DROP TABLE IF EXISTS staves")
    op.execute("DROP TABLE IF EXISTS users")
