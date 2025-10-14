#!/usr/bin/env python3
"""
Migration Script: Add TDD-compliant columns to clefs table
Adds 'warn' and 'fail' columns to support TDD-compliant severity conditions.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from datametronome_podium.core.database import get_db

async def migrate_clefs_table():
    """Add TDD-compliant columns to the clefs table."""
    print("🎵 DataMetronome TDD Migration")
    print("=" * 35)
    print("Adding TDD-compliant columns to clefs table...")
    
    try:
        # Get database connection
        db = await get_db()
        
        # Check if columns already exist
        print("🔍 Checking current table structure...")
        
        # Add warn column if it doesn't exist
        try:
            await db.execute("ALTER TABLE clefs ADD COLUMN warn TEXT")
            print("✅ Added 'warn' column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  'warn' column already exists")
            else:
                raise
        
        # Add fail column if it doesn't exist
        try:
            await db.execute("ALTER TABLE clefs ADD COLUMN fail TEXT")
            print("✅ Added 'fail' column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  'fail' column already exists")
            else:
                raise
        
        # Verify the migration by trying to query the new columns
        print("\n🔍 Verifying migration...")
        try:
            # Try to query with the new columns to verify they exist
            await db.query({"sql": "SELECT warn, fail FROM clefs LIMIT 1"})
            print("✅ Successfully verified 'warn' and 'fail' columns exist")
            print("\n🎉 Migration completed successfully!")
            print("✅ TDD-compliant columns added to clefs table")
            return True
        except Exception as e:
            print(f"❌ Migration verification failed: {e}")
            return False
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

async def main():
    """Main migration function."""
    success = await migrate_clefs_table()
    
    if success:
        print("\n🚀 Next Steps:")
        print("   1. Import demo configurations:")
        print("      python3 scripts/import_staves.py examples/demo-sqlite-only.yaml")
        print("   2. Check your Streamlit UI - you should now see staves and clefs!")
        return 0
    else:
        print("\n💡 Troubleshooting:")
        print("   - Make sure your podium API is running")
        print("   - Check database connection")
        print("   - Verify database permissions")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
