"""Stave data access."""
from __future__ import annotations

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.staves.model import StaveRow as Stave


class StaveRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def list(self, limit: int = 50, offset: int = 0) -> list[Stave]:  # ty: ignore[invalid-type-form]
        rows = await self.db.select(
            "staves", order_by="created_at DESC", limit=limit, offset=offset
        )
        return [Stave(**row) for row in rows]

    async def get(self, stave_id: str) -> Stave | None:
        rows = await self.db.select("staves", where={"id": stave_id})
        return Stave(**rows[0]) if rows else None

    async def create(self, stave: Stave) -> int:
        return await self.db.insert("staves", stave.model_dump())

    async def update(self, stave_id: str, data: dict) -> int:
        return await self.db.update("staves", data, where={"id": stave_id})

    async def delete(self, stave_id: str) -> int:
        return await self.db.delete("staves", where={"id": stave_id})

    async def find_clef_ids(self, stave_id: str) -> list[str]:  # ty: ignore[invalid-type-form]
        rows = await self.db.query(
            "SELECT id FROM clefs WHERE stave_id = ?", [stave_id]
        )
        return [row["id"] for row in rows]
