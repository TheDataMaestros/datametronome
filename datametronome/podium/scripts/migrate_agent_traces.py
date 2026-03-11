#!/usr/bin/env python3
"""
Migration Script: Add agent_traces table (multi-agent Phase 0)
Adds the agent_traces table for chat/agent observability.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metronome_pulse_sqlite import SQLitePulse


def _get_db_path() -> str:
    """Resolve SQLite DB path from DATAMETRONOME_DATABASE_URL."""
    from datametronome_podium.core.config import settings

    url = settings.database_url
    path = url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if path.startswith("//"):
        path = path[1:]
    path = path.replace("./", "")
    if not os.path.isabs(path):
        podium_dir = Path(__file__).resolve().parent.parent
        path = str((podium_dir / path).resolve())
    return path


AGENT_TRACES_SQL = """
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
"""

INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_agent_traces_conversation_id ON agent_traces(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_agent_traces_user_id ON agent_traces(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_agent_traces_created_at ON agent_traces(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_agent_traces_intent ON agent_traces(intent)",
]


async def migrate_agent_traces() -> bool:
    """Add agent_traces table and indexes."""
    print("🎵 DataMetronome agent_traces Migration (multi-agent Phase 0)")
    print("=" * 50)

    db_path = _get_db_path()
    print(f"Database: {db_path}")

    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("   Run the app once or use: make setup-db")
        return False

    connector = SQLitePulse(db_path)
    try:
        await connector.connect()

        print("🔍 Creating agent_traces table...")
        await connector.execute(AGENT_TRACES_SQL)
        print("✅ Created agent_traces table")

        print("🔍 Creating indexes...")
        for idx_sql in INDEXES_SQL:
            try:
                await connector.execute(idx_sql)
                name = idx_sql.split()[-1]
                print(f"   ✅ {name}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"   ⚠️  {e}")

        print("\n✅ Migration completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await connector.close()


if __name__ == "__main__":
    success = asyncio.run(migrate_agent_traces())
    sys.exit(0 if success else 1)
