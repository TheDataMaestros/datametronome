"""Default data seeding. Uses QueryExecutor directly (no repo dependency)."""
import logging
from datametronome_podium.core.query import QueryExecutor

logger = logging.getLogger(__name__)


async def create_default_admin(executor: QueryExecutor) -> None:
    """Create default admin user for development."""
    try:
        existing = await executor.query(
            "SELECT * FROM users WHERE username = ?", ["admin"]
        )
        if existing:
            logger.info("Admin user already exists")
            return

        from datametronome_podium.api.v1.endpoints.auth import get_password_hash

        await executor.insert("users", {
            "id": "admin-001",
            "username": "admin",
            "email": "admin@datametronome.dev",
            "hashed_password": get_password_hash("admin"),
            "is_active": True,
            "is_superuser": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        })
        logger.info("Default admin user created (admin/admin)")
    except Exception as e:
        logger.warning("Could not create default admin user: %s", e)
