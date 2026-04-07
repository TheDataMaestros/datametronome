"""Default data seeding. Uses QueryExecutor directly (no repo dependency)."""
import logging
from datametronome_podium.core.config import settings
from datametronome_podium.core.query import QueryExecutor

logger = logging.getLogger(__name__)


async def create_default_admin(executor: QueryExecutor) -> None:
    """Create default admin user — only in debug/development mode.

    Why: shipping a known admin/admin account to production is a critical
    credential exposure. The debug guard ensures this seed never runs unless
    the operator explicitly enables debug mode.
    """
    if not settings.debug:
        logger.debug("Skipping default admin seed (debug mode is off)")
        return

    try:
        existing = await executor.query(
            "SELECT * FROM users WHERE username = ?", ["admin"]
        )
        if existing:
            logger.info("Admin user already exists")
            return

        from datametronome_podium.core.security import get_password_hash

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
