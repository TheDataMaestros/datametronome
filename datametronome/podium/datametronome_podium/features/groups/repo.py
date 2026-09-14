"""Group data access."""

from typing import Any

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.groups.model import GroupRow


class GroupRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    # Named list_all, not list: a method called `list` shadows the builtin for
    # every annotation later in the class body.
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[GroupRow]:
        rows = await self.db.select(
            "groups", order_by="name ASC", limit=limit, offset=offset
        )
        return [GroupRow(**dict(r)) for r in rows]

    async def get(self, group_id: str) -> GroupRow | None:
        rows = await self.db.select("groups", where={"id": group_id})
        return GroupRow(**dict(rows[0])) if rows else None

    async def find_by_name(self, name: str) -> GroupRow | None:
        rows = await self.db.select("groups", where={"name": name})
        return GroupRow(**dict(rows[0])) if rows else None

    async def create(self, group: GroupRow) -> Any:
        return await self.db.insert("groups", group.model_dump())

    async def update(self, group_id: str, data: dict[str, Any]) -> Any:
        return await self.db.update("groups", data, where={"id": group_id})

    async def delete(self, group_id: str) -> Any:
        return await self.db.delete("groups", where={"id": group_id})

    async def stave_count(self, group_id: str) -> int:
        rows = await self.db.query(
            "SELECT COUNT(*) AS cnt FROM staves WHERE group_id = ?", [group_id]
        )
        return int(rows[0]["cnt"]) if rows else 0

    # -- membership ---------------------------------------------------------

    async def members(self, group_id: str) -> list[dict[str, Any]]:
        rows = await self.db.query(
            """
            SELECT u.id AS user_id, u.username, u.email, u.role
            FROM user_groups ug
            JOIN users u ON u.id = ug.user_id
            WHERE ug.group_id = ?
            ORDER BY u.username ASC
            """,
            [group_id],
        )
        return [dict(r) for r in rows]

    async def is_member(self, group_id: str, user_id: str) -> bool:
        rows = await self.db.query(
            "SELECT 1 AS present FROM user_groups WHERE group_id = ? AND user_id = ?",
            [group_id, user_id],
        )
        return bool(rows)

    async def add_member(self, group_id: str, user_id: str, now: str) -> Any:
        return await self.db.insert(
            "user_groups",
            {"user_id": user_id, "group_id": group_id, "created_at": now},
        )

    async def remove_member(self, group_id: str, user_id: str) -> Any:
        return await self.db.delete(
            "user_groups", where={"group_id": group_id, "user_id": user_id}
        )
