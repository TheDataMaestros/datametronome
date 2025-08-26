#!/usr/bin/env python3
"""
Basic usage example for DataPulse SQLite connector.

This example demonstrates the core functionality of the SQLite connector
including connection management, data operations, and querying.
"""

import asyncio
import tempfile
import os
from pathlib import Path

from metronome_pulse_sqlite import SQLitePulse, SQLiteReadonlyPulse, SQLiteWriteonlyPulse


async def main():
    """Main example function."""
    print("🚀 DataPulse SQLite Connector - Basic Usage Example")
    print("=" * 60)
    
    # Create a temporary database for this example
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        print(f"📁 Using temporary database: {db_path}")
        
        # Example 1: Full-featured connector
        print("\n1️⃣ Full-featured SQLitePulse connector")
        print("-" * 40)
        
        pulse = SQLitePulse(db_path)
        await pulse.connect()
        print("✅ Connected to database")
        
        # Create a sample table
        await pulse.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created users table")
        
        # Insert sample data
        users_data = [
            {"name": "Alice", "email": "alice@example.com", "active": True},
            {"name": "Bob", "email": "bob@example.com", "active": False},
            {"name": "Charlie", "email": "charlie@example.com", "active": True}
        ]
        
        await pulse.write(users_data, "users")
        print(f"✅ Inserted {len(users_data)} users")
        
        # Query data
        all_users = await pulse.query("SELECT * FROM users ORDER BY name")
        print(f"📊 Retrieved {len(all_users)} users:")
        for user in all_users:
            print(f"   - {user['name']} ({user['email']}) - Active: {user['active']}")
        
        # Parameterized query
        active_users = await pulse.query_with_params(
            "SELECT * FROM users WHERE active = ?", [True]
        )
        print(f"🔍 Found {len(active_users)} active users")
        
        # Get table information
        table_info = await pulse.get_table_info("users")
        print(f"📋 Table schema has {len(table_info)} columns")
        
        # List tables
        tables = await pulse.list_tables()
        print(f"📚 Database contains {len(tables)} tables: {tables}")
        
        await pulse.close()
        print("✅ Closed full-featured connector")
        
        # Example 2: Read-only connector
        print("\n2️⃣ Read-only SQLiteReadonlyPulse connector")
        print("-" * 40)
        
        readonly = SQLiteReadonlyPulse(db_path)
        await readonly.connect()
        print("✅ Connected with read-only connector")
        
        # Complex analytical query
        user_stats = await readonly.query_with_params("""
            SELECT 
                active,
                COUNT(*) as user_count,
                GROUP_CONCAT(name) as names
            FROM users 
            GROUP BY active
            ORDER BY active DESC
        """, [])
        
        print("📊 User statistics:")
        for stat in user_stats:
            status = "Active" if stat['active'] else "Inactive"
            print(f"   - {status}: {stat['user_count']} users ({stat['names']})")
        
        await readonly.close()
        print("✅ Closed read-only connector")
        
        # Example 3: Write-only connector
        print("\n3️⃣ Write-only SQLiteWriteonlyPulse connector")
        print("-" * 40)
        
        writeonly = SQLiteWriteonlyPulse(db_path)
        await writeonly.connect()
        print("✅ Connected with write-only connector")
        
        # Add more users
        new_users = [
            {"name": "Diana", "email": "diana@example.com", "active": True},
            {"name": "Eve", "email": "eve@example.com", "active": False}
        ]
        
        await writeonly.write(new_users, {
            "operation": "insert",
            "table": "users"
        })
        print(f"✅ Added {len(new_users)} new users")
        
        # Bulk copy operation
        bulk_users = [
            {"name": f"BulkUser{i}", "email": f"bulk{i}@example.com", "active": True}
            for i in range(5)
        ]
        
        await writeonly.copy_records("users", bulk_users)
        print(f"✅ Bulk copied {len(bulk_users)} users")
        
        await writeonly.close()
        print("✅ Closed write-only connector")
        
        # Example 4: Verify all data
        print("\n4️⃣ Verifying all data")
        print("-" * 40)
        
        final_pulse = SQLitePulse(db_path)
        await final_pulse.connect()
        
        total_users = await final_pulse.query("SELECT COUNT(*) as count FROM users")
        print(f"📊 Total users in database: {total_users[0]['count']}")
        
        # Show all users
        all_users_final = await final_pulse.query("SELECT * FROM users ORDER BY name")
        print("👥 All users:")
        for user in all_users_final:
            status = "🟢" if user['active'] else "🔴"
            print(f"   {status} {user['name']} ({user['email']})")
        
        await final_pulse.close()
        
        print("\n🎉 Example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during example: {e}")
        raise
    finally:
        # Cleanup temporary database
        try:
            os.unlink(db_path)
            print(f"🧹 Cleaned up temporary database: {db_path}")
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
