#!/usr/bin/env python3
"""
Database migration runner for DataMetronome.

Applies SQL migrations in order and tracks applied migrations.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


class MigrationRunner:
    """Handles database migrations."""

    def __init__(self, db_path: str, migrations_dir: str):
        """
        Initialize migration runner.

        Args:
            db_path: Path to SQLite database
            migrations_dir: Directory containing migration files
        """
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self.conn = None

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        print(f"📊 Connected to database: {self.db_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """
        )
        self.conn.commit()

    def get_applied_migrations(self) -> set[int]:
        """
        Get list of applied migration versions.

        Returns:
            Set of applied migration version numbers
        """
        cursor = self.conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        return {row[0] for row in cursor.fetchall()}

    def get_pending_migrations(self) -> list[tuple[int, str, Path]]:
        """
        Get list of pending migrations.

        Returns:
            List of (version, name, path) tuples for pending migrations
        """
        applied = self.get_applied_migrations()
        pending = []

        # Find all .sql files in migrations directory
        for migration_file in sorted(self.migrations_dir.glob("*.sql")):
            # Parse version from filename (e.g., "001_initial_schema.sql" -> 1)
            try:
                version = int(migration_file.stem.split("_")[0])
                name = "_".join(migration_file.stem.split("_")[1:])

                if version not in applied:
                    pending.append((version, name, migration_file))
            except (ValueError, IndexError):
                print(f"⚠️  Skipping invalid migration filename: {migration_file.name}")
                continue

        return sorted(pending, key=lambda x: x[0])

    def apply_migration(self, version: int, name: str, path: Path) -> bool:
        """
        Apply a single migration.

        Args:
            version: Migration version number
            name: Migration name
            path: Path to migration SQL file

        Returns:
            True if successful, False otherwise
        """
        print(f"\n🔧 Applying migration {version:03d}: {name}")

        try:
            # Read migration SQL
            with open(path, "r") as f:
                sql = f.read()

            # Execute migration
            self.conn.executescript(sql)

            # Record migration
            self.conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (version, name, datetime.utcnow().isoformat()),
            )

            self.conn.commit()
            print(f"✅ Migration {version:03d} applied successfully")
            return True

        except Exception as e:
            print(f"❌ Migration {version:03d} failed: {e}")
            self.conn.rollback()
            return False

    def run_migrations(self, target_version: int | None = None) -> int:
        """
        Run all pending migrations up to target version.

        Args:
            target_version: Stop at this version (None = run all)

        Returns:
            Number of migrations applied
        """
        pending = self.get_pending_migrations()

        if not pending:
            print("✅ No pending migrations")
            return 0

        print(f"\n📋 Found {len(pending)} pending migration(s)")

        applied_count = 0
        for version, name, path in pending:
            if target_version and version > target_version:
                break

            if self.apply_migration(version, name, path):
                applied_count += 1
            else:
                print(f"\n❌ Migration stopped at version {version}")
                break

        return applied_count

    def show_status(self):
        """Show migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        print("\n📊 Migration Status")
        print("=" * 60)

        if applied:
            print(f"\n✅ Applied migrations: {len(applied)}")
            cursor = self.conn.execute(
                "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
            )
            for row in cursor.fetchall():
                print(f"   {row[0]:03d}: {row[1]} (applied: {row[2]})")
        else:
            print("\n   No migrations applied yet")

        if pending:
            print(f"\n📋 Pending migrations: {len(pending)}")
            for version, name, _ in pending:
                print(f"   {version:03d}: {name}")
        else:
            print("\n   No pending migrations")

        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--db-path", default="./datametronome.db", help="Path to SQLite database"
    )
    parser.add_argument(
        "--migrations-dir",
        default="./datametronome/podium/migrations",
        help="Directory containing migration files",
    )
    parser.add_argument(
        "--status", action="store_true", help="Show migration status and exit"
    )
    parser.add_argument(
        "--target", type=int, help="Target migration version (default: latest)"
    )

    args = parser.parse_args()

    print("🎵 DataMetronome Database Migrations")
    print("=" * 60)

    # Validate migrations directory
    if not os.path.exists(args.migrations_dir):
        print(f"❌ Error: Migrations directory not found: {args.migrations_dir}")
        sys.exit(1)

    # Run migrations
    runner = MigrationRunner(args.db_path, args.migrations_dir)

    try:
        runner.connect()
        runner.ensure_migrations_table()

        if args.status:
            runner.show_status()
        else:
            applied = runner.run_migrations(args.target)
            print(f"\n✅ Migration complete: {applied} migration(s) applied")
            runner.show_status()

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

    finally:
        runner.close()


if __name__ == "__main__":
    main()
