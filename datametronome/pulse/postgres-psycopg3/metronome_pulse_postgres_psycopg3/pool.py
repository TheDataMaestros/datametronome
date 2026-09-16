"""Connection pool construction, shared by the read-write and read-only connectors."""

import psycopg
import psycopg.conninfo

try:
    from psycopg_pool import AsyncConnectionPool
except ImportError:  # pragma: no cover - very old psycopg3
    from psycopg import pool  # type: ignore

    AsyncConnectionPool = pool.AsyncConnectionPool


async def open_pool(
    *,
    host,
    port,
    database,
    user,
    password,
    **kwargs,
):
    """Build and open an AsyncConnectionPool.

    AsyncConnectionPool takes a conninfo string, not connection keywords, and
    opening it inside a running loop requires ``open=False`` followed by an
    awaited ``open()``. Constructing it with ``open=True`` from async code
    warns and starts the worker threads before the loop is ready.
    """
    conninfo = psycopg.conninfo.make_conninfo(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
        **kwargs,
    )
    pool_ = AsyncConnectionPool(conninfo, open=False)
    await pool_.open(wait=True)
    return pool_
