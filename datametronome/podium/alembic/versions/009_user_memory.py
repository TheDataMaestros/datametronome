"""009 — user memory tables.

Revision ID: 009
Revises: 008
Create Date: 2026-04-05
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dao.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category TEXT NOT NULL CHECK (category IN ('domain_focus', 'expertise', 'investigation')),
            content TEXT NOT NULL,
            source_conversation_id TEXT,
            confidence REAL NOT NULL DEFAULT 1.0,
            active INTEGER NOT NULL DEFAULT 1,
            superseded_by TEXT REFERENCES user_memories(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    dao.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_memories_user_active ON user_memories(user_id, active)"
    )
    dao.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_memories_conversation ON user_memories(source_conversation_id)"
    )

    dao.execute("""
        CREATE TABLE IF NOT EXISTS user_memory_profiles (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            domain_summary TEXT NOT NULL DEFAULT '',
            expertise_summary TEXT NOT NULL DEFAULT '',
            investigation_summary TEXT NOT NULL DEFAULT '',
            memory_count INTEGER NOT NULL DEFAULT 0,
            last_rebuilt_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    dao.execute("""
        CREATE TABLE IF NOT EXISTS conversation_extraction_status (
            conversation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'processing')),
            last_extracted_at TEXT
        )
    """)

    # Composite index to speed up memory extraction queries that fetch messages
    # by conversation ordered by time (avoids full table scan on large chat history)
    dao.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_messages_conv_created
        ON chat_messages(conversation_id, created_at DESC)
    """)


def downgrade() -> None:
    dao.execute("DROP TABLE IF EXISTS conversation_extraction_status")
    dao.execute("DROP TABLE IF EXISTS user_memory_profiles")
    dao.execute("DROP TABLE IF EXISTS user_memories")
    dao.execute("DROP INDEX IF EXISTS idx_chat_messages_conv_created")
