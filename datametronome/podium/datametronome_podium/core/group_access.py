"""Group-based write access for staves and everything hanging off them.

The rule is deliberately asymmetric. Reading is global: any authenticated user
can view any stave, its clefs and its check results, so nothing here filters
list queries. Writing is restricted to members of the stave's owning group, so
one team cannot modify another team's data sources.

Global admins bypass the check entirely.

Clefs, checks and insights have no group of their own. They inherit it through
stave_id, which keeps a single source of truth and avoids having to keep a
denormalised group_id in step across five tables.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status

from datametronome_podium.core.query import QueryExecutor

logger = logging.getLogger(__name__)


def _resolve(executor: QueryExecutor | None) -> QueryExecutor:
    """Fetch the global executor only when a check actually needs the DB.

    Callers pass nothing in production. Resolving lazily, after the super-admin
    bypass, keeps admin requests from touching the database at all.
    """
    if executor is not None:
        return executor
    from datametronome_podium.core.database import get_executor

    return get_executor()

# The role that sees and edits across every group.
SUPER_ADMIN_ROLE = "admin"


def is_super_admin(user: dict[str, Any]) -> bool:
    return user.get("role") == SUPER_ADMIN_ROLE


async def user_group_ids(
    user: dict[str, Any], executor: QueryExecutor | None = None
) -> list[str]:
    """Group IDs the user belongs to."""
    user_id = user.get("id")
    if not user_id:
        return []
    rows = await _resolve(executor).query(
        "SELECT group_id FROM user_groups WHERE user_id = ?", [user_id]
    )
    return [row["group_id"] for row in rows]


async def assert_stave_group_access(
    stave_id: str, user: dict[str, Any], executor: QueryExecutor | None = None
) -> None:
    """Raise unless the user belongs to this stave's owning group.

    Guards two things. Modifying a stave or its clefs, and reaching into the
    source database behind it, which listing tables and previewing rows both
    do. Viewing our own metadata about a stave is not guarded.

    Raises 404 when the stave does not exist, and 403 when it exists but
    belongs to another group.
    """
    if is_super_admin(user):
        return

    executor = _resolve(executor)
    rows = await executor.query("SELECT group_id FROM staves WHERE id = ?", [stave_id])
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stave not found: {stave_id}",
        )

    owning_group = rows[0]["group_id"]
    if owning_group is None:
        # Only reachable if a stave was inserted without a group after the
        # backfill migration. Refuse rather than silently allowing the write.
        logger.warning("Stave %s has no owning group; refusing write", stave_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stave has no owning group. An admin must assign one.",
        )

    if owning_group not in await user_group_ids(user, executor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This data source belongs to another group",
        )


async def assert_clef_group_access(
    clef_id: str, user: dict[str, Any], executor: QueryExecutor | None = None
) -> None:
    """Raise unless the user may modify this clef, via its stave's group."""
    if is_super_admin(user):
        return

    executor = _resolve(executor)
    rows = await executor.query("SELECT stave_id FROM clefs WHERE id = ?", [clef_id])
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clef not found: {clef_id}",
        )

    await assert_stave_group_access(rows[0]["stave_id"], user, executor)


async def assert_group_membership(
    group_id: str, user: dict[str, Any], executor: QueryExecutor | None = None
) -> None:
    """Raise unless the user may create things in this group.

    Used when a stave is created, where there is no existing stave to read the
    group from.
    """
    if is_super_admin(user):
        return

    if group_id not in await user_group_ids(user, executor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of that group",
        )
