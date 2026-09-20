"""Centralized Pulse connector factory.

All connector creation goes through this module. No other file should
branch on data_source_type to instantiate connectors.

Every connector built here is read-only. Staves are things we observe, not
things we write to; the app's own database goes through core.database, which
does not use this module.

Imports are kept lazy (inside the function body) to avoid circular imports
with the optional Pulse packages that may not be installed.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def create_connector(
    data_source_type: str,
    connection_config: dict[str, Any],
) -> Any:
    """Create and connect the appropriate read-only Pulse connector from config.

    Args:
        data_source_type: A key of BUILDERS below
        connection_config: Connection parameters dict (keys vary by type)

    Returns:
        A connected Pulse connector instance. Caller is responsible for
        calling ``await connector.close()`` when finished.

    Raises:
        ValueError: If data_source_type is not supported
        RuntimeError: If a required config key is missing or the Pulse
            package is not installed
    """
    dst = (data_source_type or "").lower()
    config = connection_config or {}

    try:
        connector = _build_connector(dst, config)
    except KeyError as exc:
        raise RuntimeError(f"Missing required connection field: {exc}") from exc
    except ImportError as exc:
        raise RuntimeError(
            f"Required connector package is not installed: {exc.name}"
        ) from exc

    await connector.connect()
    return connector


def _build_connector(dst: str, config: dict[str, Any]) -> Any:
    """Instantiate (but do not connect) the correct Pulse connector.

    Kept separate from create_connector so that unit tests can patch the
    lazy imports or inject mock classes without having to await anything.
    """
    builder = BUILDERS.get(dst)
    if builder is None:
        raise ValueError(f"Unsupported data source type: {dst!r}")
    return builder(config)


def _build_postgres_connector(config: dict[str, Any]) -> Any:
    from metronome_pulse_postgres import PostgresReadOnlyPulse

    # RDS and Aurora with rds.force_ssl=1 reject plaintext, so a stave against
    # one needs "ssl": "require". Omitted when unset, since ssl=None would
    # override asyncpg's own negotiation.
    ssl = config.get("ssl")

    return PostgresReadOnlyPulse(
        host=config["host"],
        port=config.get("port", 5432),
        database=config["database"],
        user=config["user"],
        password=config.get("password", ""),
        **({"ssl": ssl} if ssl else {}),
    )


def _build_redshift_connector(config: dict[str, Any]) -> Any:
    """Redshift runs on psycopg3, not asyncpg.

    asyncpg cannot connect to Redshift at all: Redshift forked from PostgreSQL
    8.0 and does not answer the catalog queries asyncpg issues during
    handshake. This is not a preference between drivers.
    """
    from metronome_pulse_postgres_psycopg3 import PostgresPsycopg3ReadOnlyPulse

    return PostgresPsycopg3ReadOnlyPulse(
        host=config["host"],
        port=config.get("port", 5439),
        database=config["database"],
        user=config["user"],
        password=config.get("password", ""),
        # Redshift clusters terminate plaintext connections, and psycopg
        # spells this sslmode rather than asyncpg's ssl.
        sslmode=config.get("sslmode", "require"),
    )


def _build_s3_connector(config: dict[str, Any]) -> Any:
    from metronome_pulse_s3 import S3ReadonlyPulse

    return S3ReadonlyPulse(
        bucket=config["bucket"],
        tables=config.get("tables") or {},
        region=config.get("region", "us-east-1"),
        access_key_id=config.get("access_key_id", ""),
        secret_access_key=config.get("secret_access_key", ""),
        session_token=config.get("session_token", ""),
        endpoint_url=config.get("endpoint_url", ""),
    )


def _build_sqlite_connector(config: dict[str, Any]) -> Any:
    # Accepts either 'database_path' or 'path' to locate the SQLite file.
    db_path = config.get("database_path") or config.get("path")
    if not db_path:
        raise RuntimeError(
            "SQLite connection requires 'database_path' or 'path' in connection_config"
        )

    from metronome_pulse_sqlite import SQLiteReadonlyPulse

    return SQLiteReadonlyPulse(db_path)


def _build_bigquery_connector(config: dict[str, Any]) -> Any:
    from metronome_pulse_bigquery import BigQueryReadonlyPulse  # type: ignore[import-untyped]

    return BigQueryReadonlyPulse(
        project_id=config["project_id"],
        credentials_path=config.get("credentials_path"),
        credentials_json=config.get("credentials_json"),
        dataset=config.get("dataset"),
        location=config.get("location", "US"),
    )


def _build_dbt_connector(config: dict[str, Any]) -> Any:
    from metronome_pulse_dbt import DbtReadonlyPulse

    mode = config.get("mode", "local")
    return DbtReadonlyPulse(
        mode=mode,
        project_path=config.get("project_path", ""),
        target_path=config.get("target_path", "target"),
        api_token=config.get("api_token", ""),
        account_id=config.get("account_id", ""),
        job_id=config.get("job_id", ""),
        base_url=config.get("base_url", "https://cloud.getdbt.com/api/v2"),
    )


# One entry per data source type. Keys must match
# features.staves.model.SUPPORTED_DATA_SOURCES; test_data_source_coverage.py
# asserts that, so a type cannot be accepted by the API with no way to connect.
BUILDERS = {
    "postgres": _build_postgres_connector,
    "postgresql": _build_postgres_connector,
    "redshift": _build_redshift_connector,
    "sqlite": _build_sqlite_connector,
    "bigquery": _build_bigquery_connector,
    "s3": _build_s3_connector,
    "dbt": _build_dbt_connector,
}
