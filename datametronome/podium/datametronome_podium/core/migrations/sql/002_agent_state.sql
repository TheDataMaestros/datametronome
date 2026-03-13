-- 002_agent_state.sql
-- LangGraph-style agent workflow state tables.
-- Enables: checkpointing (pause/resume), declarative workflow definitions,
-- and full event audit trail with replay capability.

CREATE TABLE IF NOT EXISTS workflow_checkpoints (
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
);

CREATE INDEX IF NOT EXISTS idx_wf_checkpoints_conversation ON workflow_checkpoints(conversation_id);
CREATE INDEX IF NOT EXISTS idx_wf_checkpoints_status ON workflow_checkpoints(status);

CREATE TABLE IF NOT EXISTS workflow_definitions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    graph_data JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id TEXT PRIMARY KEY,
    checkpoint_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    node_name TEXT,
    event_data JSONB,
    created_at TEXT NOT NULL,
    FOREIGN KEY (checkpoint_id) REFERENCES workflow_checkpoints (id)
);

CREATE INDEX IF NOT EXISTS idx_wf_events_checkpoint_created ON workflow_events(checkpoint_id, created_at);
