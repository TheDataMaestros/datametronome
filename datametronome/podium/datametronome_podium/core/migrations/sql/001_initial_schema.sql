-- 001_initial_schema.sql
-- All existing DataMetronome tables, ported from inline DDL in database.py.
-- Written in PostgreSQL dialect. The QueryAdapter translates JSONB→TEXT
-- and DOUBLE PRECISION→REAL for SQLite.

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staves (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    data_source_type TEXT NOT NULL,
    connection_config TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clefs (
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
);

CREATE TABLE IF NOT EXISTS checks (
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
);

CREATE TABLE IF NOT EXISTS scheduler_jobs (
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
);

CREATE TABLE IF NOT EXISTS job_executions (
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
);

CREATE TABLE IF NOT EXISTS anomalies (
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
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls TEXT,
    tool_results TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_traces (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_message_preview TEXT,
    intent TEXT,
    model TEXT,
    tool_calls TEXT,
    duration_ms DOUBLE PRECISION,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_traces_conversation_id ON agent_traces(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_user_id ON agent_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_created_at ON agent_traces(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_traces_intent ON agent_traces(intent);
