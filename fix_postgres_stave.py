#!/usr/bin/env python3
"""
Quick script to fix the PostgreSQL stave authentication issue.
"""

import os
import sqlite3


def fix_postgres_stave():
    # Find the correct database file
    db_paths = [
        "datametronome.db",
        "data/datametronome.db",
        "datametronome_podium/datametronome.db",
        "datametronome/podium/datametronome.db",
    ]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='staves'"
                )
                if cursor.fetchone():
                    db_path = path
                    conn.close()
                    break
                conn.close()
            except:
                continue

    if not db_path:
        print("❌ Could not find database with staves table")
        return

    print(f"✅ Found database: {db_path}")

    # Connect and delete the problematic stave
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete the problematic stave
    cursor.execute('DELETE FROM staves WHERE id = "stave-legacy-ui-demo"')

    # Also delete any clefs that reference this stave
    cursor.execute('DELETE FROM clefs WHERE stave_id = "stave-legacy-ui-demo"')

    conn.commit()

    # Verify deletion
    cursor.execute('SELECT COUNT(*) FROM staves WHERE id = "stave-legacy-ui-demo"')
    remaining = cursor.fetchone()[0]

    conn.close()

    if remaining == 0:
        print("✅ Successfully deleted problematic legacy UI demo stave")
        print("✅ Also deleted any associated clefs")
    else:
        print("❌ Failed to delete the stave")


if __name__ == "__main__":
    fix_postgres_stave()
