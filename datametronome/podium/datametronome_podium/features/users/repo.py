"""User data access."""
from typing import Any

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.users.model import UserRow as User

# Columns safe to return in list/detail views (excludes hashed_password).
_SAFE_COLUMNS = ["id", "username", "email", "is_active", "role", "created_at", "updated_at"]


class UserRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def find_by_username(self, username: str) -> User | None:
        rows = await self.db.select("users", where={"username": username})
        return User(**rows[0]) if rows else None

    async def find_by_id(self, user_id: str) -> User | None:
        rows = await self.db.select("users", where={"id": user_id})
        return User(**rows[0]) if rows else None

    async def find_by_email(self, email: str) -> User | None:
        rows = await self.db.select("users", where={"email": email})
        return User(**rows[0]) if rows else None

    async def create(self, user: User) -> int:
        return await self.db.insert("users", user.model_dump())

    async def exists(self, username: str) -> bool:
        rows = await self.db.select("users", columns=["id"], where={"username": username})
        return len(rows) > 0

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        return await self.db.select(
            "users",
            columns=_SAFE_COLUMNS,
            order_by="created_at DESC",
            limit=limit,
            offset=offset,
        )

    async def update(self, user_id: str, data: dict[str, Any]) -> int:
        return await self.db.update("users", data, where={"id": user_id})

    async def delete(self, user_id: str) -> int:
        return await self.db.delete("users", where={"id": user_id})
