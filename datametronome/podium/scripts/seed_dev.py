#!/usr/bin/env python3
"""Seed a development database with a working demo state.

Creates a group, three users with different roles, a stave pointing at the
platform's own Postgres, and a row_count clef against it. That is enough to
exercise the whole loop: sign in, see a data source, run a check, watch the
dashboard fill in.

Idempotent. Re-running skips anything that already exists, so it is safe after
a migration or a container rebuild.

Usage, from the repo root:

    make seed

Or directly inside the podium container:

    python scripts/seed_dev.py

The password comes from DATAMETRONOME_SEED_PASSWORD, defaulting to a value
that is obviously not for production. This script refuses to run when
DATAMETRONOME_DEBUG is false, so it cannot quietly create known-password
accounts on a real deployment.
"""

import asyncio
import json
import os
import sys
import uuid

from datametronome_podium.core.config import settings
from datametronome_podium.core.database import close_db, get_executor, init_db
from datametronome_podium.core.encryption import encrypt_sensitive_fields
from datametronome_podium.core.security import get_password_hash
from datametronome_podium.core.timestamp_utils import now_utc_iso

SEED_PASSWORD = os.environ.get("DATAMETRONOME_SEED_PASSWORD", "devpassword123")

GROUP_NAME = "demo"
USERS = [
    ("demo-admin", "admin", "Sees and edits across every group"),
    ("demo-editor", "editor", "Can edit data sources in the demo group"),
    ("demo-viewer", "viewer", "Read-only, belongs to the demo group"),
]
STAVE_NAME = "podium-postgres"
CLEF_NAME = "users table has rows"


async def _seed() -> None:
    executor = get_executor()
    now = now_utc_iso()

    # Group
    rows = await executor.query("SELECT id FROM groups WHERE name = ?", [GROUP_NAME])
    if rows:
        group_id = rows[0]["id"]
        print(f"group   {GROUP_NAME}: exists")
    else:
        group_id = str(uuid.uuid4())
        await executor.insert("groups", {
            "id": group_id,
            "name": GROUP_NAME,
            "description": "Seeded by scripts/seed_dev.py",
            "created_at": now,
            "updated_at": now,
        })
        print(f"group   {GROUP_NAME}: created")

    # Users, each a member of the group. The admin is a member too, though its
    # role already lets it edit everywhere; membership just keeps the seeded
    # state consistent.
    for username, role, _why in USERS:
        existing = await executor.query(
            "SELECT id FROM users WHERE username = ?", [username]
        )
        if existing:
            print(f"user    {username} ({role}): exists")
        else:
            await executor.insert("users", {
                "id": username,
                "username": username,
                "email": f"{username}@example.com",
                "hashed_password": get_password_hash(SEED_PASSWORD),
                "is_active": True,
                "role": role,
                "created_at": now,
                "updated_at": now,
            })
            print(f"user    {username} ({role}): created")

        member = await executor.query(
            "SELECT 1 AS present FROM user_groups WHERE user_id = ? AND group_id = ?",
            [username, group_id],
        )
        if not member:
            await executor.insert("user_groups", {
                "user_id": username,
                "group_id": group_id,
                "created_at": now,
            })

    # Stave pointing at the database this app already uses, so the check has
    # something real to count without any external setup.
    rows = await executor.query("SELECT id FROM staves WHERE name = ?", [STAVE_NAME])
    if rows:
        stave_id = rows[0]["id"]
        print(f"stave   {STAVE_NAME}: exists")
    else:
        stave_id = str(uuid.uuid4())
        config = encrypt_sensitive_fields(
            {
                "host": os.environ.get("DATAMETRONOME_SEED_DB_HOST", "postgres"),
                "port": 5432,
                "database": "datametronome_test",
                "user": "testuser",
                "password": "testpass",
            },
            "postgres",
        )
        await executor.insert("staves", {
            "id": stave_id,
            "name": STAVE_NAME,
            "description": "The platform's own database, seeded for demos",
            "data_source_type": "postgres",
            "connection_config": json.dumps(config),
            "is_active": True,
            "group_id": group_id,
            "created_at": now,
            "updated_at": now,
        })
        print(f"stave   {STAVE_NAME}: created")

    # Clef. Config keys must match what ClefExecutor reads: table, expected_min,
    # expected_max.
    rows = await executor.query("SELECT id FROM clefs WHERE name = ?", [CLEF_NAME])
    if rows:
        print(f"clef    {CLEF_NAME}: exists")
    else:
        await executor.insert("clefs", {
            "id": str(uuid.uuid4()),
            "stave_id": stave_id,
            "name": CLEF_NAME,
            "description": "Passes while the users table has at least one row",
            "check_type": "row_count",
            "config": json.dumps(
                {"table": "users", "expected_min": 1, "expected_max": 1_000_000}
            ),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        print(f"clef    {CLEF_NAME}: created")


async def main() -> int:
    if not settings.debug:
        print(
            "Refusing to seed: DATAMETRONOME_DEBUG is false.\n"
            "This creates accounts with a known password and is for development only.",
            file=sys.stderr,
        )
        return 1

    await init_db()
    try:
        await _seed()
    finally:
        await close_db()

    print(f"\nSign in with any of: {', '.join(u for u, _, _ in USERS)}")
    print(f"Password: {SEED_PASSWORD}")
    print("Run the check from Quality Checks, or wait for the scheduler.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
