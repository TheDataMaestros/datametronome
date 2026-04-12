"""Centralized Pulse connector factory.

All connector creation goes through this module. No other file should
branch on data_source_type to instantiate connectors.

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
    *,
    read_only: bool = False,
) -> Any:
    """Create and connect the appropriate Pulse connector from config.

    Args:
        data_source_type: One of 'postgres', 'postgresql', 'sqlite', 'bigquery'
        connection_config: Connection parameters dict (keys vary by type)
        read_only: If True, use the read-only connector variant

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
        connector = _build_connector(dst, config, read_only=read_only)
    except KeyError as exc:
        raise RuntimeError(f"Missing required connection field: {exc}") from exc
    except ImportError as exc:
        raise RuntimeError(
            f"Required connector package is not installed: {exc.name}"
        ) from exc

    await connector.connect()
    return connector


def _build_connector(
    dst: str,
    config: dict[str, Any],
    *,
    read_only: bool,
) -> Any:
    """Instantiate (but do not connect) the correct Pulse connector.

    Kept separate from create_connector so that unit tests can patch the
    lazy imports or inject mock classes without having to await anything.
    """
    if dst in ("postgres", "postgresql"):
        return _build_postgres_connector(config, read_only=read_only)
    elif dst == "sqlite":
        return _build_sqlite_connector(config, read_only=read_only)
    elif dst == "bigquery":
        return _build_bigquery_connector(config, read_only=read_only)
    elif dst == "dbt":
        return _build_dbt_connector(config, read_only=read_only)
    else:
        raise ValueError(f"Unsupported data source type: {dst!r}")


def _build_postgres_connector(config: dict[str, Any], *, read_only: bool) -> Any:
    if read_only:
        from metronome_pulse_postgres import PostgresReadOnlyPulse as PulseClass
    else:
        from metronome_pulse_postgres import PostgresPulse as PulseClass  # type: ignore[assignment]

    return PulseClass(
        host=config["host"],
        port=config.get("port", 5432),
        database=config["database"],
        user=config["user"],
        password=config.get("password", ""),
    )


def _build_sqlite_connector(config: dict[str, Any], *, read_only: bool) -> Any:
    # Accepts either 'database_path' or 'path' to locate the SQLite file.
    db_path = config.get("database_path") or config.get("path")
    if not db_path:
        raise RuntimeError(
            "SQLite connection requires 'database_path' or 'path' in connection_config"
        )

    if read_only:
        from metronome_pulse_sqlite import SQLiteReadonlyPulse as PulseClass
    else:
        from metronome_pulse_sqlite import SQLitePulse as PulseClass  # type: ignore[assignment]

    return PulseClass(db_path)


def _build_bigquery_connector(config: dict[str, Any], *, read_only: bool) -> Any:
    if read_only:
        from metronome_pulse_bigquery import BigQueryReadonlyPulse as PulseClass  # type: ignore[import-untyped]
    else:
        from metronome_pulse_bigquery import BigQueryPulse as PulseClass  # type: ignore[import-untyped, assignment]

    return PulseClass(
        project_id=config["project_id"],
        credentials_path=config.get("credentials_path"),
        credentials_json=config.get("credentials_json"),
        dataset=config.get("dataset"),
        location=config.get("location", "US"),
    )


def _build_dbt_connector(config: dict[str, Any], *, read_only: bool) -> Any:
    if not read_only:
        raise ValueError("dbt connector is read-only. Set read_only=True.")

    from metronome_pulse_dbt import DbtReadonlyPulse  # ty: ignore[unresolved-import]

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
