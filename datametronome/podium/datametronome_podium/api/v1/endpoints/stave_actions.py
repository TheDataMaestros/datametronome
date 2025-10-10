"""
Stave action endpoints - Test connection functionality.

This module provides endpoints for testing stave connections and other
stave-specific actions.
"""

import asyncio
import logging
from typing import Any, Dict
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import deserialize_stave
from datametronome_podium.services.connection_tester import ConnectionTester
from datametronome_podium.services import data_generator

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
        staves = await db.query({
            "sql": "SELECT * FROM staves WHERE id = ?", 
            "params": [stave_id]
        })
        
        if not staves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stave not found"
            )
        
        # Deserialize the stave
        stave = deserialize_stave(staves[0])
        
        # Test the connection
        tester = ConnectionTester()
        result = await tester.test_connection(stave)
        
        # Log the test result
        logger.info(f"Connection test for stave {stave_id}: {result['success']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection test failed for stave {stave_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )


class GenerateDataRequest(BaseModel):
    table_name: str
    count: int = 100

@router.post("/{stave_id}/generate-data")
async def generate_sample_data(
    stave_id: str, 
    request: GenerateDataRequest
) -> Dict[str, Any]:
    """
    Generate sample data for a table in a stave's data source.
    
    This is a developer utility to populate tables with realistic sample data.
    """
    start_time = datetime.utcnow()
    
    try:
        # Get the stave from database
        db = await get_db()
        staves = await db.query({"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]})
        if not staves:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found")
        
        stave = deserialize_stave(staves[0])
        table_name = request.table_name
        count = request.count
        logger.info(f"🔄 Starting data generation for stave {stave_id}, table {table_name}, count {count}")

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
                    existing_products = await connector.query({"sql": "SELECT * FROM products LIMIT 100", "params": []})
                    if existing_products:
                        products = existing_products
                        logger.info(f"Found {len(products)} existing products for order generation")
                    else:
                        # Generate some products first
                        products = data_generator.generate_products_data(10)
                        logger.info(f"No existing products found, generated {len(products)} products for orders")
                except Exception as e:
                    logger.warning(f"Could not fetch existing products: {e}. Generating sample products.")
                    products = data_generator.generate_products_data(10)
                
                data = data_generator.generate_orders_data(products, count)
            except Exception as e:
                logger.warning(f"Could not connect to stave database for products: {e}. Generating orders without product validation.")
                # Generate fake products for order generation
                fake_products = data_generator.generate_products_data(10)
                data = data_generator.generate_orders_data(fake_products, count)
        elif table_name == "clicks":
            data = data_generator.generate_clickstream_data(count)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Unsupported table '{table_name}' for data generation. Supported: users, products, orders, clicks"
            )

        logger.info(f"📊 Generated {len(data)} {table_name} records")

        # Try to insert the data into the stave's database
        inserted_count = 0
        try:
            # Get connector based on stave type
            if stave.data_source_type == "sqlite":
                from metronome_pulse_sqlite import SQLitePulse
                db_path = stave.connection_config.get('database_path', stave.connection_config.get('path'))
                connector = SQLitePulse(db_path)
                await connector.connect()
                
                # Create table if it doesn't exist
                await _ensure_table_exists(connector, table_name)
                
                # Insert the data
                success = await connector.write(data, table_name)
                inserted_count = len(data) if success else 0
                await connector.close()
                logger.info(f"✅ Successfully inserted {inserted_count} records into {table_name}")
            elif stave.data_source_type == "bigquery":
                from metronome_pulse_bigquery import BigQueryPulse
                config = stave.connection_config
                connector = BigQueryPulse(
                    project_id=config['project_id'],
                    credentials_path=config.get('credentials_path'),
                    credentials_json=config.get('credentials_json'),
                    dataset=config.get('dataset'),
                    location=config.get('location', 'US')
                )
                await connector.connect()
                
                # Insert the data
                await connector.write(data, table_name)
                inserted_count = len(data)
                await connector.close()
                logger.info(f"✅ Successfully inserted {inserted_count} records into {table_name}")
            else:
                logger.info(f"⏭️  Skipping data insertion for {stave.data_source_type} (not implemented yet)")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not insert data into stave database: {e}")
            logger.info("📝 Data was generated but not inserted (this is expected for some stave types)")
            # Don't fail the request if we can't insert - the data generation itself is valuable

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"🎉 Data generation completed for {table_name}: {len(data)} generated, {inserted_count} inserted, {execution_time:.2f}s")
        
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
                "insertion_status": "success" if inserted_count > 0 else "generated_only"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"❌ Data generation failed for stave {stave_id}, table {table_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data generation failed: {str(e)}"
        )


@router.post("/{stave_id}/preview-data")
async def preview_stave_data(
    stave_id: str,
    request: GenerateDataRequest  # Reusing the same model, but with table_name and count=limit
) -> Dict[str, Any]:
    """
    Preview data from a table in a stave's data source.
    
    This endpoint fetches a sample of data from the specified table for preview purposes.
    """
    try:
        # Get the stave from database
        db = await get_db()
        staves = await db.query({"sql": "SELECT * FROM staves WHERE id = ?", "params": [stave_id]})
        if not staves:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stave not found")
        
        stave = deserialize_stave(staves[0])
        table_name = request.table_name
        limit = request.count  # Using count as limit for preview
        
        logger.info(f"🔍 Previewing data from stave {stave_id}, table {table_name}, limit {limit}")

        # Try to fetch data from the stave's database
        try:
            # Get connector based on stave type
            if stave.data_source_type == "sqlite":
                from metronome_pulse_sqlite import SQLiteReadonlyPulse
                db_path = stave.connection_config.get('database_path', stave.connection_config.get('path'))
                connector = SQLiteReadonlyPulse(db_path)
                await connector.connect()
                
                # Query for sample data
                data = await connector.query({
                    "sql": f"SELECT * FROM {table_name} LIMIT ?",
                    "params": [limit]
                })
                await connector.close()
            elif stave.data_source_type == "bigquery":
                from metronome_pulse_bigquery import BigQueryReadonlyPulse
                config = stave.connection_config
                connector = BigQueryReadonlyPulse(
                    project_id=config['project_id'],
                    credentials_path=config.get('credentials_path'),
                    credentials_json=config.get('credentials_json'),
                    dataset=config.get('dataset'),
                    location=config.get('location', 'US')
                )
                await connector.connect()
                
                # Query for sample data
                data = await connector.query(f"SELECT * FROM {table_name} LIMIT {limit}")
                await connector.close()
            elif stave.data_source_type in ["postgres", "postgresql"]:
                from metronome_pulse_postgres import PostgresReadOnlyPulse
                config = stave.connection_config
                connector = PostgresReadOnlyPulse(
                    host=config['host'],
                    port=config.get('port', 5432),
                    database=config['database'],
                    user=config['user'],
                    password=config['password']
                )
                await connector.connect()
                
                # Query for sample data
                data = await connector.query(f"SELECT * FROM {table_name} LIMIT {limit}")
                await connector.close()
            else:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail=f"Preview not implemented for {stave.data_source_type} yet"
                )
            
            logger.info(f"📊 Retrieved {len(data) if data else 0} records from {table_name}")
            
            return {
                "success": True,
                "message": f"Successfully retrieved {len(data) if data else 0} records from table '{table_name}'",
                "stave_id": stave_id,
                "stave_name": stave.name,
                "table_name": table_name,
                "limit": limit,
                "row_count": len(data) if data else 0,
                "data": data or [],
                "columns": list(data[0].keys()) if data and len(data) > 0 else []
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch data from table {table_name}: {e}")
            
            # If table doesn't exist or query fails, return helpful message
            if "no such table" in str(e).lower():
                return {
                    "success": False,
                    "message": f"Table '{table_name}' does not exist in this database",
                    "stave_id": stave_id,
                    "table_name": table_name,
                    "data": [],
                    "suggestion": "Try generating data for this table first"
                }
            else:
                raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Data preview failed for stave {stave_id}, table {table_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data preview failed: {str(e)}"
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
            logger.warning(f"No schema defined for table {table_name}")
            return
            
        await connector.execute(create_sql, [])
        logger.info(f"✅ Ensured table {table_name} exists")
        
    except Exception as e:
        logger.warning(f"Could not ensure table {table_name} exists: {e}")
        # Don't raise - this is not critical for data generation


