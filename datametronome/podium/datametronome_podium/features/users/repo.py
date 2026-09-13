"""User data access."""
import sqlite3
from typing import Any

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.users.model import UserRow as User

# Columns safe to return in list/detail views (excludes hashed_password).
_SAFE_COLUMNS = ["id", "username", "email", "is_active", "role", "created_at", "updated_at"]


def _pg_unique_violation(exc: BaseException | None) -> bool:
    """Postgres unique violation (asyncpg or SQLSTATE 23505)."""
    if exc is None:
        return False
    try:
        import asyncpg

        if isinstance(exc, asyncpg.exceptions.UniqueViolationError):
            return True
    except ImportError:
        pass
    if getattr(exc, "sqlstate", None) == "23505":
        return True
    return False


def is_duplicate_user_insert(exc: BaseException) -> bool:
    """True if the insert failed only because of a uniqueness constraint.

    Callers check for an existing username before inserting, which leaves a
    race between the check and the insert. This lets that race surface as a
    409 rather than a 500.
    """
    if _pg_unique_violation(exc):
        return True
    bc = exc.__cause__
    if isinstance(bc, BaseException) and _pg_unique_violation(bc):
        return True
    if isinstance(exc, sqlite3.IntegrityError):
        return "unique" in str(exc).lower()
    if isinstance(bc, sqlite3.IntegrityError):
        return "unique" in str(bc).lower()
    lowered = str(exc).lower()
    return "unique" in lowered or "duplicate" in lowered


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
