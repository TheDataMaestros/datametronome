"""Check data access."""
from __future__ import annotations
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.checks.model import Check


class CheckRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def list(self, limit: int = 100, offset: int = 0) -> list[Check]:  # ty: ignore[invalid-type-form]
        rows = await self.db.select(
            "checks", order_by="timestamp DESC", limit=limit, offset=offset
        )
        return [Check(**row) for row in rows]

    async def get(self, check_id: str) -> Check | None:
        rows = await self.db.select("checks", where={"id": check_id})
        return Check(**rows[0]) if rows else None

    async def create(self, check: Check) -> int:
        return await self.db.insert("checks", check.model_dump())

    async def update(self, check_id: str, data: dict) -> int:
        return await self.db.update("checks", data, where={"id": check_id})

    async def delete(self, check_id: str) -> int:
        return await self.db.delete("checks", where={"id": check_id})

    async def list_by_clef(self, clef_id: str, limit: int = 10, offset: int = 0) -> list[Check]:  # ty: ignore[invalid-type-form]
        rows = await self.db.query(
            "SELECT * FROM checks WHERE clef_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            [clef_id, limit, offset]
        )
        return [Check(**row) for row in rows]

    async def list_by_stave(self, stave_id: str, limit: int = 10, offset: int = 0) -> list[Check]:  # ty: ignore[invalid-type-form]
        rows = await self.db.query(
            "SELECT * FROM checks WHERE stave_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            [stave_id, limit, offset]
        )
        return [Check(**row) for row in rows]
