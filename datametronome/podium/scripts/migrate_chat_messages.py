#!/usr/bin/env python3
"""
Migration Script: Add chat_messages table
Adds the chat_messages table for AI agent conversations.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from datametronome_podium.core.database import get_db


async def migrate_chat_messages():
    """Add chat_messages table."""
    print("🎵 DataMetronome Chat Messages Migration")
    print("=" * 40)
    print("Adding chat_messages table...")

    try:
        # Get database connection
        db = await get_db()

        # Create the table
        print("🔍 Creating chat_messages table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                tool_calls TEXT,
                tool_results TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        print("✅ Created chat_messages table")

        # Create indexes
        print("🔍 Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at)",
        ]
        for index_sql in indexes:
            try:
                await db.execute(index_sql)
                print(f"✅ Created index: {index_sql.split()[-1]}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"⚠️  Index creation warning: {e}")

        print("\n✅ Migration completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(migrate_chat_messages())
    sys.exit(0 if success else 1)

