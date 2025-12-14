#!/usr/bin/env python3
"""
Fix clef stave references to use the working SQLite stave.
"""

import json
import sqlite3


def fix_clef_staves():
    """Update all clefs to use the working SQLite stave and existing tables."""

    # Connect to the database
    conn = sqlite3.connect("data/datametronome.db")
    cursor = conn.cursor()

    # Mapping of old stave to new stave
    stave_mapping = {"stave-nuxt-demo": "stave-demo-sqlite"}

    # Mapping of non-existent tables to existing tables
    table_mapping = {
        "user_behavior": "users",
        "daily_metrics": "users",  # We'll use users table for metrics
        "orders": "orders",  # orders table exists
    }

    # Get all clefs
    cursor.execute("SELECT id, config FROM clefs")
    clefs = cursor.fetchall()

    updates_made = 0

    for clef_id, config_json in clefs:
        try:
            config = json.loads(config_json)
            updated = False

            # Update table references
            if "table" in config:
                old_table = config["table"]
                if old_table in table_mapping:
                    config["table"] = table_mapping[old_table]
                    updated = True
                    print(f"Updated {clef_id}: table {old_table} -> {config['table']}")

            # Update the config if it changed
            if updated:
                cursor.execute(
                    "UPDATE clefs SET config = ? WHERE id = ?",
                    (json.dumps(config), clef_id),
                )
                updates_made += 1

        except Exception as e:
            print(f"Error updating clef {clef_id}: {e}")

    # Update stave references
    cursor.execute("SELECT id, stave_id FROM clefs")
    clefs_with_staves = cursor.fetchall()

    for clef_id, stave_id in clefs_with_staves:
        if stave_id in stave_mapping:
            new_stave_id = stave_mapping[stave_id]
            cursor.execute(
                "UPDATE clefs SET stave_id = ? WHERE id = ?", (new_stave_id, clef_id)
            )
            updates_made += 1
            print(f"Updated {clef_id}: stave {stave_id} -> {new_stave_id}")

    conn.commit()
    conn.close()

    print(f"\n✅ Updated {updates_made} clef records")
    print("All clefs now use stave-demo-sqlite and existing tables")


if __name__ == "__main__":
    fix_clef_staves()
