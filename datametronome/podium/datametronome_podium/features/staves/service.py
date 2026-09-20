"""Stave action service — business logic for connection testing, data preview,
table listing, and sample data generation.

This module is intentionally free of FastAPI imports. All HTTP concerns
(HTTPException, status codes, Request) are handled by the router layer.
Raises plain ValueError / RuntimeError / LookupError instead.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from datametronome_podium.core.connector_factory import create_connector
from datametronome_podium.core.database import get_executor
from datametronome_podium.core.query import quote_identifier
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.services import connection_tester
from datametronome_podium.services.stave_service import deserialize_stave

logger = logging.getLogger(__name__)

# Row cap for the preview endpoint — kept tight for safety.
_PREVIEW_MAX_ROWS = 500


async def load_stave(stave_id: str) -> Stave:
    """Fetch a stave row from DB and deserialize it.

    Raises LookupError when the stave does not exist so the router can map it
    to a 404 without the service knowing about HTTP.
    """
    rows = await get_executor().query("SELECT * FROM staves WHERE id = ?", [stave_id])
    if not rows:
        raise LookupError(f"Stave '{stave_id}' not found")
    return deserialize_stave(rows[0])


async def test_connection(stave_id: str) -> dict[str, Any]:
    """Test connectivity for the named stave. Returns the tester result dict."""
    stave = await load_stave(stave_id)
    result = await connection_tester.test_connection(stave)
    logger.info("Connection test for stave %s: %s", stave_id, result["success"])
    return result


async def list_tables(stave_id: str, *, include_structure: bool = True) -> dict[str, Any]:
    """List tables available in the stave's data source.

    Raises LookupError on missing stave, ValueError when the connector does
    not support list_tables.
    """
    stave = await load_stave(stave_id)
    logger.info("Listing tables for stave %s (%s)", stave_id, stave.data_source_type)

    connector = await connection_tester.get_connector(stave)
    try:
        if not hasattr(connector, "list_tables"):
            raise ValueError(
                f"list_tables not available for {stave.data_source_type} connector"
            )

        table_names = await _call_list_tables(connector, stave)
        tables = await _build_table_list(connector, stave, table_names, include_structure)
    finally:
        try:
            await connector.close()
        except Exception as exc:
            logger.warning("Failed to close connector: %s", exc)

    logger.info("Found %d tables in stave %s", len(tables), stave_id)
    return {
        "success": True,
        "stave_id": stave_id,
        "stave_name": stave.name,
        "data_source_type": stave.data_source_type,
        "count": len(tables),
        "tables": tables,
    }


async def _call_list_tables(connector: Any, stave: Stave) -> list[str]:
    """Dispatch list_tables with the correct arguments per connector type."""
    if stave.data_source_type == "bigquery":
        dataset = stave.connection_config.get("dataset")
        return await connector.list_tables(dataset)
    if stave.data_source_type in ("postgres", "postgresql"):
        schema = stave.connection_config.get("schema", "public")
        return await connector.list_tables(schema)
    if stave.data_source_type == "dbt":
        return await connector.list_tables()
    return await connector.list_tables()


async def _build_table_list(
    connector: Any,
    stave: Stave,
    table_names: list[str],
    include_structure: bool,
) -> list[dict[str, Any]]:
    """Enrich each table name with optional structure metadata."""
    tables: list[dict[str, Any]] = []
    for name in table_names:
        info: dict[str, Any] = {"name": name}
        if include_structure:
            info = await _add_structure(connector, stave, info, name)
        tables.append(info)
    return tables


async def _add_structure(
    connector: Any,
    stave: Stave,
    info: dict[str, Any],
    table_name: str,
) -> dict[str, Any]:
    """Attempt to fetch table schema and merge it into info."""
    if not hasattr(connector, "get_table_info"):
        logger.warning("get_table_info not available for %s", stave.data_source_type)
        info["structure"] = None
        return info
    try:
        info["structure"] = await connector.get_table_info(table_name)
    except Exception as exc:
        logger.warning("Failed to get structure for table %s: %s", table_name, exc)
        info["structure"] = None
        info["structure_error"] = str(exc)
    return info


def _bigquery_table_ref(config: dict[str, Any], table_name: str) -> str:
    """Return a backtick-quoted BigQuery table reference.

    BigQuery Standard SQL uses backticks, not ANSI double-quotes.
    Raises ValueError on invalid or potentially unsafe table names.
    """
    tn = (table_name or "").strip()
    if not tn or "`" in tn:
        raise ValueError("Invalid table name")
    if "." in tn:
        ref = tn
    else:
        ds = config.get("dataset")
        if not ds:
            raise ValueError(
                "For BigQuery use dataset.table or set dataset in the stave config"
            )
        ref = f"{ds}.{tn}"
    return "`" + ref.replace("`", "``") + "`"


async def preview_data(stave_id: str, table_name: str, count: int) -> dict[str, Any]:
    """Fetch up to _PREVIEW_MAX_ROWS rows from a stave table for preview.

    Returns a result dict. Raises LookupError on missing stave, ValueError on
    unsupported connector types.
    """
    stave = await load_stave(stave_id)
    limit = min(count, _PREVIEW_MAX_ROWS)
    logger.info("Previewing data from stave %s, table %s, limit %d", stave_id, table_name, limit)

    try:
        data = await fetch_sample_rows(stave, table_name, limit)
    except Exception as exc:
        if "no such table" in str(exc).lower():
            return {
                "success": False,
                "message": f"Table '{table_name}' does not exist in this database",
                "stave_id": stave_id,
                "table_name": table_name,
                "data": [],
                "suggestion": "Try generating data for this table first",
            }
        raise

    row_count = len(data) if data else 0
    logger.info("Retrieved %d records from %s", row_count, table_name)
    return {
        "success": True,
        "message": f"Successfully retrieved {row_count} records from table '{table_name}'",
        "stave_id": stave_id,
        "stave_name": stave.name,
        "table_name": table_name,
        "limit": limit,
        "row_count": row_count,
        "data": data or [],
        "columns": list(data[0].keys()) if data else [],
    }


async def fetch_sample_rows(stave: Stave, table_name: str, limit: int) -> list[dict[str, Any]]:
    """Read up to `limit` rows from a stave table, dialect-correct and bound.

    Public because agent_tools samples tables too, and previously hand-built
    this SQL for three of the seven source types with the limit interpolated
    into the string.
    """
    dst = stave.data_source_type
    config = stave.connection_config

    if dst == "sqlite":
        connector = await create_connector(dst, config)
        try:
            return await connector.query(
                {"sql": f"SELECT * FROM {quote_identifier(table_name)} LIMIT ?", "params": [limit]}
            )
        finally:
            await connector.close()

    if dst == "bigquery":
        connector = await create_connector(dst, config)
        try:
            bq_tbl = _bigquery_table_ref(config, table_name)
            return await connector.query(
                {"sql": f"SELECT * FROM {bq_tbl} LIMIT @lim", "named_parameters": {"lim": int(limit)}}
            )
        finally:
            await connector.close()

    if dst in ("postgres", "postgresql"):
        connector = await create_connector(dst, config)
        try:
            qtbl = quote_identifier(table_name)
            return await connector.query_with_params(
                f"SELECT * FROM {qtbl} LIMIT $1", [limit]
            )
        finally:
            await connector.close()

    if dst == "dbt":
        connector = await create_connector(dst, config)
        try:
            return await connector.query({"table": table_name, "limit": limit})
        finally:
            await connector.close()

    raise ValueError(f"Preview not implemented for {dst} yet")
