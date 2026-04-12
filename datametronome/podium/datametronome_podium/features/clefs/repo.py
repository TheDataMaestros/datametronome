"""Clef data access."""
from __future__ import annotations
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.clefs.model import ClefRow as Clef


class ClefRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def list(self, limit: int = 50, offset: int = 0) -> list[Clef]:  # ty: ignore[invalid-type-form]
        rows = await self.db.select(
            "clefs", order_by="created_at DESC", limit=limit, offset=offset
        )
        return [Clef(**row) for row in rows]

    async def get(self, clef_id: str) -> Clef | None:
        rows = await self.db.select("clefs", where={"id": clef_id})
        return Clef(**rows[0]) if rows else None

    async def create(self, clef: Clef) -> int:
        return await self.db.insert("clefs", clef.model_dump())

    async def update(self, clef_id: str, data: dict) -> int:
        return await self.db.update("clefs", data, where={"id": clef_id})

    async def delete(self, clef_id: str) -> int:
        return await self.db.delete("clefs", where={"id": clef_id})

    async def list_by_stave(self, stave_id: str) -> list[Clef]:  # ty: ignore[invalid-type-form]
        rows = await self.db.select("clefs", where={"stave_id": stave_id})
        return [Clef(**row) for row in rows]
