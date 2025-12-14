#!/usr/bin/env python3
"""
Database restore script for DataMetronome.

Restores backups created by backup_database.py.
"""

import argparse
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path


def restore_sqlite(backup_path: str, db_path: str, force: bool = False):
    """
    Restore SQLite database from backup.

    Args:
        backup_path: Path to backup file
        db_path: Path where to restore the database
        force: Overwrite existing database without confirmation
    """
    if os.path.exists(db_path) and not force:
        response = input(f"⚠️  Database {db_path} exists. Overwrite? (yes/no): ")
        if response.lower() != "yes":
            print("Restore cancelled.")
            sys.exit(0)

    print(f"📦 Restoring SQLite database to: {db_path}")

    # Handle compressed backups
    if backup_path.endswith(".gz"):
        print("🗜️  Decompressing backup...")
        temp_path = backup_path[:-3]  # Remove .gz extension
        with gzip.open(backup_path, "rb") as f_in:
            with open(temp_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        source_path = temp_path
    else:
        source_path = backup_path

    # Copy database file
    shutil.copy2(source_path, db_path)

    # Clean up temp file if we decompressed
    if source_path != backup_path:
        os.remove(source_path)

    print(f"✅ Database restored successfully!")


def restore_postgres(
    backup_path: str,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str | None,
    force: bool = False,
):
    """
    Restore PostgreSQL database from backup.

    Args:
        backup_path: Path to backup file
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Database user
        password: Database password
        force: Skip confirmation
    """
    if not force:
        response = input(
            f"⚠️  This will restore database '{database}' on {host}. Continue? (yes/no): "
        )
        if response.lower() != "yes":
            print("Restore cancelled.")
            sys.exit(0)

    print(f"📦 Restoring PostgreSQL database: {database}@{host}")

    # Handle compressed backups
    if backup_path.endswith(".gz"):
        print("🗜️  Decompressing backup...")
        temp_path = backup_path[:-3]
        with gzip.open(backup_path, "rb") as f_in:
            with open(temp_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        source_path = temp_path
    else:
        source_path = backup_path

    # Build psql command
    cmd = [
        "psql",
        f"--host={host}",
        f"--port={port}",
        f"--username={user}",
        f"--dbname={database}",
        f"--file={source_path}",
    ]

    # Set password if provided
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ psql failed: {e}")
        raise
    except FileNotFoundError:
        print("❌ psql not found. Please install PostgreSQL client tools.")
        sys.exit(1)
    finally:
        # Clean up temp file if we decompressed
        if source_path != backup_path and os.path.exists(source_path):
            os.remove(source_path)

    print(f"✅ Database restored successfully!")


def list_backups(backup_dir: str):
    """
    List available backups.

    Args:
        backup_dir: Directory containing backups
    """
    print("📋 Available backups:\n")

    backups = list(Path(backup_dir).glob("datametronome_*"))
    backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    if not backups:
        print("No backups found.")
        return

    for i, backup in enumerate(backups, 1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        mtime = backup.stat().st_mtime
        from datetime import datetime

        date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i}. {backup.name}")
        print(f"   Date: {date}")
        print(f"   Size: {size_mb:.2f} MB\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Restore DataMetronome database")
    parser.add_argument(
        "--type", choices=["sqlite", "postgres"], default="sqlite", help="Database type"
    )
    parser.add_argument("--backup-path", help="Path to backup file to restore")
    parser.add_argument(
        "--backup-dir", default="./backups", help="Directory containing backups"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available backups and exit"
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompts"
    )

    # SQLite options
    parser.add_argument(
        "--sqlite-path",
        default="./datametronome.db",
        help="Path where to restore SQLite database",
    )

    # PostgreSQL options
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--database", default="datametronome", help="Database name")
    parser.add_argument("--user", default="datametronome", help="Database user")
    parser.add_argument(
        "--password", help="Database password (or use PGPASSWORD env var)"
    )

    args = parser.parse_args()

    print("🎵 DataMetronome Database Restore")
    print("=" * 60 + "\n")

    # List backups if requested
    if args.list:
        list_backups(args.backup_dir)
        sys.exit(0)

    # Validate backup path
    if not args.backup_path:
        print("❌ Error: --backup-path is required")
        print("\nUse --list to see available backups")
        sys.exit(1)

    if not os.path.exists(args.backup_path):
        print(f"❌ Error: Backup file not found: {args.backup_path}")
        sys.exit(1)

    # Perform restore
    try:
        if args.type == "sqlite":
            restore_sqlite(args.backup_path, args.sqlite_path, args.force)
        else:
            password = args.password or os.getenv("PGPASSWORD")
            restore_postgres(
                args.backup_path,
                args.host,
                args.port,
                args.database,
                args.user,
                password,
                args.force,
            )
    except Exception as e:
        print(f"\n❌ Restore failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
