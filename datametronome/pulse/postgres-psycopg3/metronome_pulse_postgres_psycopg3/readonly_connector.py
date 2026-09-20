"""Read-only psycopg3 connector.

This is the connector Redshift staves run on. asyncpg cannot talk to Redshift
(it forked from PostgreSQL 8.0 and lacks catalog features asyncpg queries at
connection time), so the psycopg3 path is not an alternative driver here, it
is the only one that works.

Read-only is a type-level guarantee: the class implements Pulse and Readable
and not Writable, so there is no method that writes. It matches how
PostgresReadOnlyPulse in the asyncpg package works.
"""

from metronome_pulse_core import Pulse, Readable

from .pool import open_pool


class PostgresPsycopg3ReadOnlyPulse(Pulse, Readable):
    """Read-only PostgreSQL/Redshift connector using psycopg3."""

    def __init__(
        self,
        host="localhost",
        port=5432,
        database=None,
        user=None,
        password=None,
        **kwargs,
    ):
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._kwargs = kwargs
        self._pool = None

    async def connect(self):
        self._pool = await open_pool(
            host=self._host,
            port=self._port,
            database=self._database,
            user=self._user,
            password=self._password,
            **self._kwargs,
        )

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def is_connected(self):
        return self._pool is not None

    async def query(self, query_config) -> list:
        """Run SQL and return a list of row dicts.

        Accepts a plain SQL string, or a dict with 'sql' and optional 'params'
        for parameterised queries, matching the Readable contract.
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")

        if isinstance(query_config, dict):
            sql = query_config.get("sql")
            if not sql:
                raise ValueError("Query config dict must contain 'sql' key")
            params = query_config.get("params") or None
        else:
            sql = query_config
            params = None

        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                if cur.description is None:
                    return []
                rows = await cur.fetchall()
                columns = [desc.name for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]

    async def list_tables(self, schema: str = "public") -> list[str]:
        """Base tables in a schema, alphabetically.

        Redshift keeps information_schema from its PostgreSQL 8.0 ancestry, so
        the same query serves both. Views are excluded: a check that counts
        rows in a view measures the view's definition, not stored data.
        """
        rows = await self.query(
            {
                "sql": (
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                ),
                "params": [schema],
            }
        )
        return [row["table_name"] for row in rows]

    async def get_table_info(self, table_name: str) -> list[dict]:
        """Columns of a table, in declaration order.

        Returns a bare column list like the S3 and BigQuery connectors do, so
        callers need no per-source unwrapping. Deliberately no size or row
        count: the read-write connector computes those by interpolating the
        table name into SQL, which is an injection waiting to happen, and
        nothing in Podium reads them.
        """
        return await self.query(
            {
                "sql": (
                    "SELECT column_name, data_type, is_nullable, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_name = %s ORDER BY ordinal_position"
                ),
                "params": [table_name],
            }
        )
