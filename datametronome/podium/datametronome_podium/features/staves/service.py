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
from datametronome_podium.services import data_generator
from datametronome_podium.services.connection_tester import ConnectionTester
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
    tester = ConnectionTester()
    result = await tester.test_connection(stave)
    logger.info("Connection test for stave %s: %s", stave_id, result["success"])
    return result


async def list_tables(stave_id: str, *, include_structure: bool = True) -> dict[str, Any]:
    """List tables available in the stave's data source.

    Raises LookupError on missing stave, ValueError when the connector does
    not support list_tables.
    """
    stave = await load_stave(stave_id)
    logger.info("Listing tables for stave %s (%s)", stave_id, stave.data_source_type)

    tester = ConnectionTester()
    connector = await tester.get_connector(stave, read_only=True)
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
        data = await _fetch_preview_data(stave, table_name, limit)
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


async def _fetch_preview_data(stave: Stave, table_name: str, limit: int) -> list[dict[str, Any]]:
    """Dispatch preview query to the correct connector type."""
    dst = stave.data_source_type
    config = stave.connection_config

    if dst == "sqlite":
        connector = await create_connector(dst, config, read_only=True)
        try:
            return await connector.query(
                {"sql": f"SELECT * FROM {quote_identifier(table_name)} LIMIT ?", "params": [limit]}
            )
        finally:
            await connector.close()

    if dst == "bigquery":
        connector = await create_connector(dst, config, read_only=True)
        try:
            bq_tbl = _bigquery_table_ref(config, table_name)
            return await connector.query(
                {"sql": f"SELECT * FROM {bq_tbl} LIMIT @lim", "named_parameters": {"lim": int(limit)}}
            )
        finally:
            await connector.close()

    if dst in ("postgres", "postgresql"):
        connector = await create_connector(dst, config, read_only=True)
        try:
            qtbl = quote_identifier(table_name)
            return await connector.query_with_params(
                f"SELECT * FROM {qtbl} LIMIT $1", [limit]
            )
        finally:
            await connector.close()

    if dst == "dbt":
        connector = await create_connector(dst, config, read_only=True)
        try:
            return await connector.query({"table": table_name, "limit": limit})
        finally:
            await connector.close()

    raise ValueError(f"Preview not implemented for {dst} yet")


async def generate_data(stave_id: str, table_name: str, count: int) -> dict[str, Any]:
    """Generate sample data and attempt to insert it into the stave's database.

    Returns a result dict. Raises LookupError on missing stave, ValueError for
    unsupported table names.
    """
    start_time = datetime.now(timezone.utc)
    stave = await load_stave(stave_id)

    logger.info(
        "Starting data generation for stave %s, table %s, count %d",
        stave_id, table_name, count,
    )

    data = await _generate_table_data(stave, table_name, count)
    logger.info("Generated %d %s records", len(data), table_name)

    inserted_count = await _insert_generated_data(stave, table_name, data)

    execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        "Data generation completed for %s: %d generated, %d inserted, %.2fs",
        table_name, len(data), inserted_count, execution_time,
    )

    return {
        "success": True,
        "message": f"Successfully generated {len(data)} {table_name} records",
        "stave_id": stave_id,
        "stave_name": stave.name,
        "table_name": table_name,
        "requested_count": count,
        "generated_count": len(data),
        "inserted_count": inserted_count,
        "execution_time": execution_time,
        "tables_affected": [table_name],
        "metadata": {
            "generation_method": "faker_based",
            "data_quality": "realistic_sample_data",
            "insertion_status": "success" if inserted_count > 0 else "generated_only",
        },
    }


async def _generate_table_data(stave: Stave, table_name: str, count: int) -> list[dict[str, Any]]:
    """Generate in-memory sample rows for the given table name."""
    if table_name == "users":
        return data_generator.generate_users_data(count)
    if table_name == "products":
        return data_generator.generate_products_data(count)
    if table_name == "clicks":
        return data_generator.generate_clickstream_data(count)
    if table_name == "orders":
        return await _generate_orders(stave, count)
    raise ValueError(
        f"Unsupported table '{table_name}' for data generation. "
        "Supported: users, products, orders, clicks"
    )


async def _generate_orders(stave: Stave, count: int) -> list[dict[str, Any]]:
    """Generate orders, trying to source real products from the stave first."""
    try:
        tester = ConnectionTester()
        connector = await tester.get_connector(stave)
        try:
            existing = await connector.query({"sql": "SELECT * FROM products LIMIT 100", "params": []})
            if existing:
                logger.info("Found %d existing products for order generation", len(existing))
                products = existing
            else:
                products = data_generator.generate_products_data(10)
                logger.info("No existing products found, generated %d for orders", len(products))
        finally:
            # Close regardless of query success to avoid connection leaks.
            try:
                await connector.close()
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Could not connect for products: %s. Generating sample products.", exc)
        products = data_generator.generate_products_data(10)

    return data_generator.generate_orders_data(products, count)


async def _insert_generated_data(
    stave: Stave, table_name: str, data: list[dict[str, Any]]
) -> int:
    """Insert generated data into the stave's database. Returns inserted row count.

    Failures are logged but do not raise — data generation is still useful
    even when the write step fails (e.g., for read-only or unsupported connectors).
    """
    dst = stave.data_source_type
    try:
        if dst == "sqlite":
            return await _sqlite_insert(stave, table_name, data)
        if dst == "bigquery":
            return await _bigquery_insert(stave, table_name, data)
        logger.info("Skipping data insertion for %s (not implemented yet)", dst)
        return 0
    except Exception as exc:
        logger.warning("Could not insert data into stave database: %s", exc)
        logger.info("Data was generated but not inserted (expected for some stave types)")
        return 0


async def _sqlite_insert(stave: Stave, table_name: str, data: list[dict[str, Any]]) -> int:
    connector = await create_connector("sqlite", stave.connection_config, read_only=False)
    try:
        await _ensure_sqlite_table_exists(connector, table_name)
        success = await connector.write(data, table_name)
        inserted = len(data) if success else 0
    finally:
        await connector.close()
    logger.info("Successfully inserted %d records into %s", inserted, table_name)
    return inserted


async def _bigquery_insert(stave: Stave, table_name: str, data: list[dict[str, Any]]) -> int:
    connector = await create_connector("bigquery", stave.connection_config, read_only=False)
    try:
        await connector.write(data, table_name)
        inserted = len(data)
    finally:
        await connector.close()
    logger.info("Successfully inserted %d records into %s", inserted, table_name)
    return inserted


async def _ensure_sqlite_table_exists(connector: Any, table_name: str) -> None:
    """Create a known table if it does not exist yet (SQLite only).

    This is a best-effort helper; failures are swallowed because the table
    may already exist or the schema may differ from the template below.
    """
    _SCHEMAS: dict[str, str] = {
        "users": """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, name TEXT, email TEXT,
                age INTEGER, created_at TEXT, updated_at TEXT
            )""",
        "products": """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY, name TEXT, description TEXT,
                price REAL, category TEXT, in_stock BOOLEAN, created_at TEXT
            )""",
        "orders": """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, user_id TEXT, product_id TEXT,
                quantity INTEGER, total_amount REAL, order_date TEXT, status TEXT
            )""",
        "clicks": """
            CREATE TABLE IF NOT EXISTS clicks (
                id TEXT PRIMARY KEY, user_id TEXT, page_url TEXT,
                click_timestamp TEXT, session_id TEXT, user_agent TEXT
            )""",
    }
    sql = _SCHEMAS.get(table_name)
    if not sql:
        logger.warning("No schema defined for table %s", table_name)
        return
    try:
        await connector.execute(sql, [])
        logger.info("Ensured table %s exists", table_name)
    except Exception as exc:
        logger.warning("Could not ensure table %s exists: %s", table_name, exc)
