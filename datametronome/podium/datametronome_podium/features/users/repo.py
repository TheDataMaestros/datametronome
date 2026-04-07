"""User data access."""
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.users.model import UserRow as User


class UserRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def find_by_username(self, username: str) -> User | None:
        rows = await self.db.select("users", where={"username": username})
        return User(**rows[0]) if rows else None

    async def find_by_id(self, user_id: str) -> User | None:
        rows = await self.db.select("users", where={"id": user_id})
        return User(**rows[0]) if rows else None

    async def create(self, user: User) -> int:
        return await self.db.insert("users", user.model_dump())

    async def exists(self, username: str) -> bool:
        rows = await self.db.select("users", columns=["id"], where={"username": username})
        return len(rows) > 0
