"""
Per-task DB session factory for Celery workers.

Workers can't use the global get_db() singleton because it's initialized
at API startup. Each task creates its own short-lived connector + executor.
"""
import logging
from contextlib import asynccontextmanager
from typing import Any

from datametronome_podium.core.database import _create_connector
from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.core.query_adapter import QueryAdapter

logger = logging.getLogger(__name__)


async def create_worker_db(database_url: str) -> tuple[Any, QueryExecutor]:
    """Create a fresh connector + executor for a worker task.

    Returns (connector, executor). Caller must close the connector when done.
    """
    connector, dialect = await _create_connector(database_url)
    adapter = QueryAdapter(dialect)
    executor = QueryExecutor(connector, adapter)
    await connector.connect()
    logger.debug("Worker DB session created (dialect=%s)", dialect)
    return connector, executor


async def close_worker_db(connector: Any) -> None:
    """Close a worker's DB connector."""
    if connector:
        await connector.close()
        logger.debug("Worker DB session closed")


@asynccontextmanager
async def worker_db_session(database_url: str):
    """Context manager that creates and cleans up a worker DB session.

    Usage:
        async with worker_db_session(settings.database_url) as (connector, executor):
            rows = await executor.query("SELECT 1")
    """
    connector, executor = await create_worker_db(database_url)
    try:
        yield connector, executor
    finally:
        await close_worker_db(connector)
