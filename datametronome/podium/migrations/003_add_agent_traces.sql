-- Migration: 003_add_agent_traces
-- Description: Add agent_traces table for chat/agent observability (Phase 0 multi-agent)
-- Date: 2025-03

CREATE TABLE IF NOT EXISTS agent_traces (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_message_preview TEXT,
    intent TEXT,
    model TEXT,
    tool_calls TEXT,
    duration_ms REAL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_traces_conversation_id ON agent_traces(conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_user_id ON agent_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_created_at ON agent_traces(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_traces_intent ON agent_traces(intent);
