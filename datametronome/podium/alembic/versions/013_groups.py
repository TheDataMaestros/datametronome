"""013 — groups and group membership, with staves owned by a group.

Reads stay global: any authenticated user can view any stave. Writes are
restricted to members of the stave's owning group, so one team cannot modify
another team's data sources. Global admins bypass this entirely.

Existing installs must keep working, so every current stave and user is moved
into a single default group, which reproduces today's behaviour exactly.

Revision ID: 013
Revises: 012
Create Date: 2026-09-13
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dialect_ops import DialectAwareOps as dao

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

DEFAULT_GROUP_ID = "default"

# Literal rather than CURRENT_TIMESTAMP: these columns are TEXT holding ISO
# strings everywhere else, and CURRENT_TIMESTAMP yields a timestamp type on
# Postgres and a differently formatted string on SQLite.
_BACKFILL_TS = "2026-09-13T00:00:00Z"


def upgrade() -> None:
    dao.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Membership is a plain join table. Roles stay global (admin/editor/viewer)
    # and say what a user may do; membership says which staves they may do it to.
    dao.execute("""
        CREATE TABLE IF NOT EXISTS user_groups (
            user_id TEXT NOT NULL,
            group_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, group_id)
        )
    """)

    dao.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_groups_user ON user_groups (user_id)"
    )

    dao.execute("ALTER TABLE staves ADD COLUMN group_id TEXT")
    dao.execute("CREATE INDEX IF NOT EXISTS idx_staves_group ON staves (group_id)")

    # Backfill so nothing loses access on upgrade.
    dao.execute(
        "INSERT INTO groups (id, name, description, created_at, updated_at) "
        f"VALUES ('{DEFAULT_GROUP_ID}', 'Default', "
        "'Holds everything that existed before groups were introduced', "
        f"'{_BACKFILL_TS}', '{_BACKFILL_TS}')"
    )
    dao.execute(
        f"UPDATE staves SET group_id = '{DEFAULT_GROUP_ID}' WHERE group_id IS NULL"
    )
    dao.execute(
        "INSERT INTO user_groups (user_id, group_id, created_at) "
        f"SELECT id, '{DEFAULT_GROUP_ID}', '{_BACKFILL_TS}' FROM users"
    )


def downgrade() -> None:
    dao.execute("DROP INDEX IF EXISTS idx_staves_group")
    dao.execute("ALTER TABLE staves DROP COLUMN group_id")
    dao.execute("DROP INDEX IF EXISTS idx_user_groups_user")
    dao.execute("DROP TABLE IF EXISTS user_groups")
    dao.execute("DROP TABLE IF EXISTS groups")
