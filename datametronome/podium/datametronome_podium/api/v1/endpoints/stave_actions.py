"""
Stave action endpoints - Test connection functionality.

This module provides endpoints for testing stave connections and other
stave-specific actions.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from datametronome_podium.core.database import get_db
from datametronome_podium.core.query import quote_identifier
from datametronome_podium.services import data_generator
from datametronome_podium.services.connection_tester import ConnectionTester
from datametronome_podium.services.stave_service import deserialize_stave
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{stave_id}/test-connection")
async def test_stave_connection(stave_id: str) -> Dict[str, Any]:
    """
    Test connection to a stave's data source.

    This endpoint attempts to establish a connection to the data source
    specified in the stave configuration and returns the connection status.

    Args:
        stave_id: ID of the stave to test

    Returns:
        Connection test result with status, message, and metadata

    Example Response:
        {
            "success": true,
            "message": "Connection successful",
            "connection_time": 0.123,
            "metadata": {
                "database_version": "PostgreSQL 14.5",
                "schema_count": 5
            }
        }
    """
    try:
        # Get the stave from database
        db = await get_db()
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )

        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        # Deserialize the stave
        stave = deserialize_stave(staves[0])

        # Test the connection
        tester = ConnectionTester()
        result = await tester.test_connection(stave)

        # Log the test result
        logger.info("Connection test for stave %s: %s", stave_id, result["success"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Connection test failed for stave %s: %s", stave_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection test failed",
        )


class GenerateDataRequest(BaseModel):
    table_name: str
    count: int = 100


@router.post("/{stave_id}/generate-data")
async def generate_sample_data(
    stave_id: str, request: GenerateDataRequest
) -> Dict[str, Any]:
    """
    Generate sample data for a table in a stave's data source.

    This is a developer utility to populate tables with realistic sample data.
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Get the stave from database
        db = await get_db()
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )
        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        stave = deserialize_stave(staves[0])
        table_name = request.table_name
        count = request.count
        logger.info(
            "🔄 Starting data generation for stave %s, table %s, count %d",
            stave_id, table_name, count,
        )

        # Generate the data
        if table_name == "users":
            data = data_generator.generate_users_data(count)
        elif table_name == "products":
            data = data_generator.generate_products_data(count)
        elif table_name == "orders":
            # For orders, we need products. Try to get them from the stave's database
            try:
                tester = ConnectionTester()
                connector = await tester.get_connector(stave)

                # Try to get existing products, or generate some if none exist
                try:
                    existing_products = await connector.query(
                        {"sql": "SELECT * FROM products LIMIT 100", "params": []}
                    )
                    if existing_products:
                        products = existing_products
                        logger.info("Found %d existing products for order generation", len(products))
                    else:
                        # Generate some products first
                        products = data_generator.generate_products_data(10)
                        logger.info(
                            "No existing products found, generated %d products for orders",
                            len(products),
                        )
                except Exception as e:
                    logger.warning("Could not fetch existing products: %s. Generating sample products.", e)
                    products = data_generator.generate_products_data(10)

                data = data_generator.generate_orders_data(products, count)
            except Exception as e:
                logger.warning(
                    "Could not connect to stave database for products: %s. Generating orders without product validation.",
                    e,
                )
                # Generate fake products for order generation
                fake_products = data_generator.generate_products_data(10)
                data = data_generator.generate_orders_data(fake_products, count)
        elif table_name == "clicks":
            data = data_generator.generate_clickstream_data(count)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported table '{table_name}' for data generation. Supported: users, products, orders, clicks",
            )

        logger.info("📊 Generated %d %s records", len(data), table_name)

        # Try to insert the data into the stave's database
        inserted_count = 0
        try:
            # Get connector based on stave type
            if stave.data_source_type == "sqlite":
                from metronome_pulse_sqlite import SQLitePulse  # type: ignore

                db_path = stave.connection_config.get(
                    "database_path", stave.connection_config.get("path")
                )
                connector = SQLitePulse(db_path)
                await connector.connect()

                # Create table if it doesn't exist
                await _ensure_table_exists(connector, table_name)

                # Insert the data
                success = await connector.write(data, table_name)
                inserted_count = len(data) if success else 0
                await connector.close()
                logger.info("✅ Successfully inserted %d records into %s", inserted_count, table_name)
            elif stave.data_source_type == "bigquery":
                from metronome_pulse_bigquery import BigQueryPulse  # type: ignore

                config = stave.connection_config
                connector = BigQueryPulse(
                    project_id=config["project_id"],
                    credentials_path=config.get("credentials_path"),
                    credentials_json=config.get("credentials_json"),
                    dataset=config.get("dataset"),
                    location=config.get("location", "US"),
                )
                await connector.connect()

                # Insert the data
                await connector.write(data, table_name)
                inserted_count = len(data)
                await connector.close()
                logger.info("✅ Successfully inserted %d records into %s", inserted_count, table_name)
            else:
                logger.info(
                    "⏭️  Skipping data insertion for %s (not implemented yet)",
                    stave.data_source_type,
                )

        except Exception as e:
            logger.warning("⚠️ Could not insert data into stave database: %s", e)
            logger.info(
                "📝 Data was generated but not inserted (this is expected for some stave types)"
            )
            # Don't fail the request if we can't insert - the data generation itself is valuable

        # Calculate execution time
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            "🎉 Data generation completed for %s: %d generated, %d inserted, %.2fs",
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
                "insertion_status": "success"
                if inserted_count > 0
                else "generated_only",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error(
            "❌ Data generation failed for stave %s, table %s: %s",
            stave_id, table_name, e, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data generation failed",
        )


@router.post("/{stave_id}/preview-data")
async def preview_stave_data(
    stave_id: str,
    request: GenerateDataRequest,  # Reusing the same model, but with table_name and count=limit
) -> Dict[str, Any]:
    """
    Preview data from a table in a stave's data source.

    This endpoint fetches a sample of data from the specified table for preview purposes.
    """
    try:
        # Get the stave from database
        db = await get_db()
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )
        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        stave = deserialize_stave(staves[0])
        table_name = request.table_name
        limit = request.count  # Using count as limit for preview

        logger.info("🔍 Previewing data from stave %s, table %s, limit %d", stave_id, table_name, limit)

        # Try to fetch data from the stave's database
        try:
            # Get connector based on stave type
            if stave.data_source_type == "sqlite":
                from metronome_pulse_sqlite import SQLiteReadonlyPulse

                db_path = stave.connection_config.get(
                    "database_path", stave.connection_config.get("path")
                )
                connector = SQLiteReadonlyPulse(db_path)
                await connector.connect()

                # Query for sample data
                data = await connector.query(
                    {"sql": f"SELECT * FROM {quote_identifier(table_name)} LIMIT ?", "params": [limit]}
                )
                await connector.close()
            elif stave.data_source_type == "bigquery":
                from metronome_pulse_bigquery import (
                    BigQueryReadonlyPulse,  # type: ignore
                )

                config = stave.connection_config
                connector = BigQueryReadonlyPulse(
                    project_id=config["project_id"],
                    credentials_path=config.get("credentials_path"),
                    credentials_json=config.get("credentials_json"),
                    dataset=config.get("dataset"),
                    location=config.get("location", "US"),
                )
                await connector.connect()

                # Query for sample data
                data = await connector.query(
                    f"SELECT * FROM {quote_identifier(table_name)} LIMIT {limit}"
                )
                await connector.close()
            elif stave.data_source_type in ["postgres", "postgresql"]:
                from metronome_pulse_postgres import PostgresReadOnlyPulse

                config = stave.connection_config
                connector = PostgresReadOnlyPulse(
                    host=config["host"],
                    port=config.get("port", 5432),
                    database=config["database"],
                    user=config["user"],
                    password=config["password"],
                )
                await connector.connect()

                # Query for sample data
                data = await connector.query(
                    f"SELECT * FROM {quote_identifier(table_name)} LIMIT {limit}"
                )
                await connector.close()
            else:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail=f"Preview not implemented for {stave.data_source_type} yet",
                )

            logger.info("📊 Retrieved %d records from %s", len(data) if data else 0, table_name)

            return {
                "success": True,
                "message": f"Successfully retrieved {len(data) if data else 0} records from table '{table_name}'",
                "stave_id": stave_id,
                "stave_name": stave.name,
                "table_name": table_name,
                "limit": limit,
                "row_count": len(data) if data else 0,
                "data": data or [],
                "columns": list(data[0].keys()) if data and len(data) > 0 else [],
            }

        except Exception as e:
            logger.warning("⚠️ Could not fetch data from table %s: %s", table_name, e)

            # If table doesn't exist or query fails, return helpful message
            if "no such table" in str(e).lower():
                return {
                    "success": False,
                    "message": f"Table '{table_name}' does not exist in this database",
                    "stave_id": stave_id,
                    "table_name": table_name,
                    "data": [],
                    "suggestion": "Try generating data for this table first",
                }
            else:
                raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ Data preview failed for stave %s, table %s: %s",
            stave_id, table_name, e, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data preview failed",
        )


async def _ensure_table_exists(connector, table_name: str):
    """Ensure a table exists with a basic schema for data generation."""
    try:
        if table_name == "users":
            create_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                age INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
            """
        elif table_name == "products":
            create_sql = """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                price REAL,
                category TEXT,
                in_stock BOOLEAN,
                created_at TEXT
            )
            """
        elif table_name == "orders":
            create_sql = """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                product_id TEXT,
                quantity INTEGER,
                total_amount REAL,
                order_date TEXT,
                status TEXT
            )
            """
        elif table_name == "clicks":
            create_sql = """
            CREATE TABLE IF NOT EXISTS clicks (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                page_url TEXT,
                click_timestamp TEXT,
                session_id TEXT,
                user_agent TEXT
            )
            """
        else:
            logger.warning("No schema defined for table %s", table_name)
            return

        await connector.execute(create_sql, [])
        logger.info("✅ Ensured table %s exists", table_name)

    except Exception as e:
        logger.warning("Could not ensure table %s exists: %s", table_name, e)
        # Don't raise - this is not critical for data generation


@router.get("/{stave_id}/tables")
async def list_stave_tables(
    stave_id: str,
    include_structure: bool = Query(True, description="Include table structure/schema"),
) -> Dict[str, Any]:
    """
    List all tables available in a stave's data source.

    This endpoint connects to the data source specified in the stave configuration
    and returns a list of all available tables, optionally including their structure.

    Args:
        stave_id: ID of the stave to query
        include_structure: Whether to include table structure/schema information

    Returns:
        Dictionary containing:
        - tables: List of table objects with name and optional structure
        - count: Number of tables found
        - stave_id: The stave ID queried
        - data_source_type: Type of data source

    Example Response:
        {
            "success": true,
            "stave_id": "stave-123",
            "stave_name": "Production Database",
            "data_source_type": "postgres",
            "count": 3,
            "tables": [
                {
                    "name": "users",
                    "structure": {
                        "columns": [
                            {"column_name": "id", "data_type": "integer", ...},
                            ...
                        ]
                    }
                },
                ...
            ]
        }
    """
    connector = None
    try:
        # Get the stave from database
        db = await get_db()
        staves = await db.query(
            {"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]}
        )

        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found"
            )

        stave = deserialize_stave(staves[0])

        logger.info("🔍 Listing tables for stave %s (%s)", stave_id, stave.data_source_type)

        # Get connector based on stave type
        tester = ConnectionTester()
        connector = await tester.get_connector(stave, read_only=True)

        # List tables using the connector's list_tables method
        tables = []
        if not hasattr(connector, "list_tables"):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"list_tables not available for {stave.data_source_type} connector",
            )

        # Call list_tables with appropriate parameters based on data source type
        if stave.data_source_type == "bigquery":
            # BigQuery requires dataset parameter
            config = stave.connection_config
            dataset = config.get("dataset")
            table_names = await connector.list_tables(dataset)
        elif stave.data_source_type in ["postgres", "postgresql"]:
            # Postgres can optionally take schema parameter (defaults to 'public')
            schema = stave.connection_config.get("schema", "public")
            table_names = await connector.list_tables(schema)
        else:
            # SQLite and others use default list_tables()
            table_names = await connector.list_tables()

        # Get structure for each table if requested
        for table_name in table_names:
            table_info = {"name": table_name}

            if include_structure:
                try:
                    if hasattr(connector, "get_table_info"):
                        structure = await connector.get_table_info(table_name)
                        table_info["structure"] = structure
                    else:
                        logger.warning(
                            "get_table_info not available for %s", stave.data_source_type
                        )
                        table_info["structure"] = None
                except Exception as e:
                    logger.warning("Failed to get structure for table %s: %s", table_name, e)
                    table_info["structure"] = None
                    table_info["structure_error"] = str(e)

            tables.append(table_info)

        logger.info("📊 Found %d tables in stave %s", len(tables), stave_id)

        return {
            "success": True,
            "stave_id": stave_id,
            "stave_name": stave.name,
            "data_source_type": stave.data_source_type,
            "count": len(tables),
            "tables": tables,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to list tables for stave %s: %s", stave_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tables",
        )
    finally:
        # Always close the connector
        if connector:
            try:
                await connector.close()
            except Exception as e:
                logger.warning("Failed to close connector: %s", e)
