#!/usr/bin/env python3
"""
Database backup script for DataMetronome.

Supports both SQLite and PostgreSQL databases with automatic rotation and compression.
"""

import argparse
import os
import sys
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import subprocess


def backup_sqlite(db_path: str, backup_dir: str, compress: bool = True) -> str:
    """
    Backup SQLite database.
    
    Args:
        db_path: Path to SQLite database file
        backup_dir: Directory to store backups
        compress: Whether to gzip compress the backup
        
    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"datametronome_sqlite_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)
    
    print(f"📦 Backing up SQLite database: {db_path}")
    
    # Copy database file
    shutil.copy2(db_path, backup_path)
    
    if compress:
        print(f"🗜️  Compressing backup...")
        compressed_path = f"{backup_path}.gz"
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(backup_path)
        backup_path = compressed_path
    
    file_size = os.path.getsize(backup_path) / (1024 * 1024)  # MB
    print(f"✅ Backup complete: {backup_path} ({file_size:.2f} MB)")
    
    return backup_path


def backup_postgres(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str | None,
    backup_dir: str,
    compress: bool = True
) -> str:
    """
    Backup PostgreSQL database using pg_dump.
    
    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Database user
        password: Database password (optional if using .pgpass)
        backup_dir: Directory to store backups
        compress: Whether to gzip compress the backup
        
    Returns:
        Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"datametronome_postgres_{database}_{timestamp}.sql"
    backup_path = os.path.join(backup_dir, backup_name)
    
    print(f"📦 Backing up PostgreSQL database: {database}@{host}")
    
    # Build pg_dump command
    cmd = [
        "pg_dump",
        f"--host={host}",
        f"--port={port}",
        f"--username={user}",
        f"--dbname={database}",
        "--format=plain",
        "--clean",
        "--if-exists",
        f"--file={backup_path}"
    ]
    
    # Set password if provided
    env = os.environ.copy()
    if password:
        env['PGPASSWORD'] = password
    
    try:
        subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ pg_dump failed: {e.stderr}")
        raise
    except FileNotFoundError:
        print("❌ pg_dump not found. Please install PostgreSQL client tools.")
        sys.exit(1)
    
    if compress:
        print(f"🗜️  Compressing backup...")
        compressed_path = f"{backup_path}.gz"
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(backup_path)
        backup_path = compressed_path
    
    file_size = os.path.getsize(backup_path) / (1024 * 1024)  # MB
    print(f"✅ Backup complete: {backup_path} ({file_size:.2f} MB)")
    
    return backup_path


def rotate_backups(backup_dir: str, keep_days: int = 7, keep_weekly: int = 4, keep_monthly: int = 3):
    """
    Rotate backups with retention policy.
    
    Args:
        backup_dir: Directory containing backups
        keep_days: Number of daily backups to keep
        keep_weekly: Number of weekly backups to keep
        keep_monthly: Number of monthly backups to keep
    """
    print(f"\n🔄 Rotating backups (keep: {keep_days}d, {keep_weekly}w, {keep_monthly}m)")
    
    now = datetime.now()
    backup_files = []
    
    # Find all backup files
    for file in Path(backup_dir).glob("datametronome_*"):
        if file.is_file():
            backup_files.append(file)
    
    # Sort by modification time (newest first)
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    daily_cutoff = now - timedelta(days=keep_days)
    weekly_cutoff = now - timedelta(weeks=keep_weekly)
    monthly_cutoff = now - timedelta(days=keep_monthly * 30)
    
    weekly_backups = []
    monthly_backups = []
    
    for backup_file in backup_files:
        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        age_days = (now - file_time).days
        
        # Keep all backups from last N days
        if file_time > daily_cutoff:
            continue
        
        # Keep one backup per week for N weeks
        if file_time > weekly_cutoff:
            week_key = file_time.strftime("%Y-W%W")
            if week_key not in weekly_backups:
                weekly_backups.append(week_key)
                continue
        
        # Keep one backup per month for N months
        if file_time > monthly_cutoff:
            month_key = file_time.strftime("%Y-%m")
            if month_key not in monthly_backups:
                monthly_backups.append(month_key)
                continue
        
        # Delete old backups
        print(f"🗑️  Deleting old backup: {backup_file.name} ({age_days} days old)")
        backup_file.unlink()
    
    remaining = len(list(Path(backup_dir).glob("datametronome_*")))
    print(f"✅ Rotation complete. {remaining} backups retained.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backup DataMetronome database")
    parser.add_argument(
        "--type",
        choices=["sqlite", "postgres"],
        default="sqlite",
        help="Database type"
    )
    parser.add_argument(
        "--backup-dir",
        default="./backups",
        help="Directory to store backups"
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        default=True,
        help="Compress backup with gzip"
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Rotate old backups after creating new one"
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=7,
        help="Number of daily backups to keep"
    )
    parser.add_argument(
        "--keep-weekly",
        type=int,
        default=4,
        help="Number of weekly backups to keep"
    )
    parser.add_argument(
        "--keep-monthly",
        type=int,
        default=3,
        help="Number of monthly backups to keep"
    )
    
    # SQLite options
    parser.add_argument(
        "--sqlite-path",
        default="./datametronome.db",
        help="Path to SQLite database file"
    )
    
    # PostgreSQL options
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--database", default="datametronome", help="Database name")
    parser.add_argument("--user", default="datametronome", help="Database user")
    parser.add_argument("--password", help="Database password (or use PGPASSWORD env var)")
    
    args = parser.parse_args()
    
    # Create backup directory
    os.makedirs(args.backup_dir, exist_ok=True)
    
    print("🎵 DataMetronome Database Backup")
    print("=" * 60)
    
    # Perform backup
    try:
        if args.type == "sqlite":
            backup_sqlite(args.sqlite_path, args.backup_dir, args.compress)
        else:
            password = args.password or os.getenv("PGPASSWORD")
            backup_postgres(
                args.host,
                args.port,
                args.database,
                args.user,
                password,
                args.backup_dir,
                args.compress
            )
        
        # Rotate backups if requested
        if args.rotate:
            rotate_backups(
                args.backup_dir,
                args.keep_days,
                args.keep_weekly,
                args.keep_monthly
            )
        
        print("\n✅ Backup completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

