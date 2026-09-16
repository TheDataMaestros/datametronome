"""Read-only connector for Parquet, CSV and JSON files on S3.

DuckDB does the querying. That choice is the whole point of this package: S3
has no query engine, and DuckDB's httpfs extension reads objects directly and
gives back real SQL, so every check that already works against Postgres works
here without a second SQL generator.

Each configured table becomes a DuckDB view. The stave declares them:

    {
      "bucket": "analytics-prod",
      "region": "eu-west-1",
      "tables": {
        "users": "users/*.parquet",
        "orders": "orders/dt=*/*.parquet"
      }
    }

A check against table "users" then runs SELECT COUNT(*) FROM "users", which is
the same SQL the Postgres path produces. Nothing in the check layer needs to
know the rows came from object storage.
"""

import asyncio
import re

from metronome_pulse_core import Pulse, Readable

from .paths import quote_literal, scan_expression

# DuckDB StatementType names that only read. DuckDB can write to S3 and to
# local disk via COPY and ATTACH, so a read-only connector has to refuse those
# rather than rely on not exposing a write method.
_READ_ONLY_STATEMENTS = frozenset({"SELECT", "EXPLAIN"})

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class S3ReadonlyPulse(Pulse, Readable):
    """Query files in an S3 bucket as if they were tables."""

    def __init__(
        self,
        bucket: str = "",
        tables: dict | None = None,
        region: str = "us-east-1",
        access_key_id: str = "",
        secret_access_key: str = "",
        session_token: str = "",
        endpoint_url: str = "",
    ):
        self._bucket = bucket
        self._tables = tables or {}
        self._region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._session_token = session_token
        self._endpoint_url = endpoint_url
        self._conn = None
        # ponytail: one DuckDB connection behind a lock, so checks against the
        # same stave serialise. Give each query its own cursor if a stave ever
        # has enough concurrent checks for that to matter.
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if not self._bucket:
            raise ValueError("S3 connection requires 'bucket'")
        if not self._tables:
            raise ValueError(
                "S3 connection requires a 'tables' mapping of name to object path, "
                "e.g. {'users': 'users/*.parquet'}"
            )

        self._conn = await asyncio.to_thread(self._open)

    def _open(self):
        import duckdb

        conn = duckdb.connect(":memory:")
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")
        conn.execute(self._secret_sql())

        for name, path in self._tables.items():
            if not _IDENTIFIER.match(name):
                raise ValueError(
                    f"Invalid table name {name!r}. Table names must be plain "
                    "identifiers; the object path goes in the value."
                )
            conn.execute(
                f'CREATE VIEW "{name}" AS '
                f"SELECT * FROM {scan_expression(self._bucket, path)}"
            )

        return conn

    def _secret_sql(self) -> str:
        """Credentials for httpfs.

        With no explicit keys, DuckDB's credential_chain provider picks up the
        instance role or the standard AWS environment, which is how this should
        run on ECS, EKS or EC2. Explicit keys are for everything else.
        """
        parts = [f"TYPE s3, REGION {quote_literal(self._region)}"]

        if self._access_key_id:
            parts.append(f"KEY_ID {quote_literal(self._access_key_id)}")
            parts.append(f"SECRET {quote_literal(self._secret_access_key)}")
            if self._session_token:
                parts.append(f"SESSION_TOKEN {quote_literal(self._session_token)}")
        else:
            parts.append("PROVIDER credential_chain")

        if self._endpoint_url:
            endpoint = self._endpoint_url.split("://", 1)[-1]
            parts.append(f"ENDPOINT {quote_literal(endpoint)}")
            # DuckDB defaults to virtual-host addressing (bucket.host). MinIO
            # and most other S3-compatible stores only answer path style
            # (host/bucket), and the failure is a DNS error that says nothing
            # about addressing.
            parts.append("URL_STYLE 'path'")
            if self._endpoint_url.startswith("http://"):
                parts.append("USE_SSL false")

        return f"CREATE OR REPLACE SECRET s3_stave ({', '.join(parts)})"

    async def close(self) -> None:
        if self._conn is not None:
            conn, self._conn = self._conn, None
            await asyncio.to_thread(conn.close)

    async def is_connected(self) -> bool:
        return self._conn is not None

    async def query(self, query_config) -> list:
        if self._conn is None:
            raise RuntimeError("Not connected. Call connect() first.")

        if isinstance(query_config, dict):
            sql = query_config.get("sql")
            if not sql:
                raise ValueError("Query config dict must contain 'sql' key")
            params = query_config.get("params") or []
        else:
            sql = query_config
            params = []

        _assert_read_only(sql)

        async with self._lock:
            return await asyncio.to_thread(self._run, sql, params)

    def _run(self, sql: str, params: list) -> list:
        conn = self._conn
        if conn is None:
            raise RuntimeError("Connection closed while the query was queued")
        cur = conn.execute(sql, params) if params else conn.execute(sql)
        if cur.description is None:
            return []
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    async def get_table_info(self, table_name: str) -> list:
        return await self.query(f'DESCRIBE SELECT * FROM "{table_name}"')


def _assert_read_only(sql: str) -> None:
    """Allow exactly one reading statement.

    DuckDB's own parser classifies the statement, so this does not scan for
    keywords. A blocklist would reject "WHERE action = 'delete'", and a check
    on the leading verb would miss "SELECT 1; COPY t TO 's3://...'", which
    execute() would happily run.

    DESCRIBE, SUMMARIZE and WITH all parse as SELECT.
    """
    import duckdb

    statements = duckdb.extract_statements(sql)

    if len(statements) != 1:
        raise ValueError(
            f"Read-only connector expected one statement, got {len(statements)}"
        )

    kind = statements[0].type.name
    if kind not in _READ_ONLY_STATEMENTS:
        raise ValueError(f"Read-only connector rejected a {kind} statement")
