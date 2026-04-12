"""
Connection Tester - Tests connections to various data sources.

This module provides functionality to test connections to different types
of data sources (PostgreSQL, MySQL, SQLite, Redis, MongoDB, etc.) to ensure
that stave configurations are valid and accessible.
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime
from typing import Any, cast

from datametronome_podium.features.staves.model import Stave

logger = logging.getLogger(__name__)


class ConnectionTester:
    """
    Tests connections to various data sources.

    This class provides methods to test connectivity to different types of
    data sources based on stave configurations.
    """

    def __init__(self):
        self.timeout = 10  # seconds

    async def test_connection(self, stave: Stave) -> dict[str, Any]:
        """
        Test connection to a stave's data source.

        Args:
            stave: Stave configuration to test

        Returns:
            Connection test result with success status, message, and metadata
        """
        start_time = time.time()

        try:
            if stave.data_source_type in ["postgres", "postgresql"]:
                result = await self._test_postgres_connection(stave)
            elif stave.data_source_type == "mysql":
                result = await self._test_mysql_connection(stave)
            elif stave.data_source_type == "sqlite":
                result = await self._test_sqlite_connection(stave)
            elif stave.data_source_type == "redis":
                result = await self._test_redis_connection(stave)
            elif stave.data_source_type == "mongodb":
                result = await self._test_mongodb_connection(stave)
            elif stave.data_source_type == "bigquery":
                result = await self._test_bigquery_connection(stave)
            elif stave.data_source_type in ["api", "http"]:
                result = await self._test_api_connection(stave)
            else:
                result = {
                    "success": False,
                    "message": f"Unsupported data source type: {stave.data_source_type}",
                    "metadata": {},
                }

            connection_time = time.time() - start_time
            result["connection_time"] = connection_time  # ty: ignore[assignment]  # ty:ignore[ignore-comment-unknown-rule, invalid-assignment]

            return result

        except Exception as e:
            connection_time = time.time() - start_time
            logger.error("Connection test failed for %s: %s", stave.name, e)
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "connection_time": connection_time,
                "metadata": {},
            }

    async def get_connector(self, stave: Stave, read_only: bool = True):
        """
        Return a connected DataPulse connector for the given stave.

        Callers are responsible for closing the connector when finished.
        """
        from datametronome_podium.core.connector_factory import create_connector

        return await create_connector(
            stave.data_source_type or "",
            stave.connection_config or {},
            read_only=read_only,
        )

    async def _test_postgres_connection(self, stave: Stave) -> dict[str, Any]:
        """Test PostgreSQL connection using DataPulse."""
        try:
            # Import DataPulse PostgreSQL read-only connector
            from metronome_pulse_postgres import PostgresReadOnlyPulse

            config = stave.connection_config

            # Create DataPulse read-only connector
            connector = PostgresReadOnlyPulse(
                host=config["host"],
                port=config.get("port", 5432),
                database=config["database"],
                user=config["user"],
                password=config.get("password", ""),
            )

            # Connect to database
            await connector.connect()

            # Test connection by running a simple query
            version_result = await connector.query("SELECT version();")
            version = version_result[0]["version"] if version_result else "Unknown"

            schema_result = await connector.query(
                "SELECT COUNT(*) as count FROM information_schema.schemata;"
            )
            schema_count = schema_result[0]["count"] if schema_result else 0

            table_result = await connector.query(
                "SELECT COUNT(*) as count FROM information_schema.tables;"
            )
            table_count = table_result[0]["count"] if table_result else 0

            # Close connection
            await connector.close()

            return {
                "success": True,
                "message": "PostgreSQL connection successful",
                "metadata": {
                    "database_version": version,
                    "schema_count": schema_count,
                    "table_count": table_count,
                    "host": config["host"],
                    "port": config.get("port", 5432),
                    "database": config["database"],
                },
            }

        except ImportError:
            return {
                "success": False,
                "message": "metronome_pulse_postgres not installed. Install with: pip install metronome-pulse-postgres",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"PostgreSQL connection failed: {str(e)}",
                "metadata": {},
            }

    async def _test_mysql_connection(self, stave: Stave) -> dict[str, Any]:
        """Test MySQL connection.

        The mysql.connector library is synchronous; run it in the default
        thread-pool executor to avoid blocking the event loop.
        """
        try:
            import mysql.connector  # type: ignore

            config = stave.connection_config

            def _connect_and_query() -> dict[str, Any]:
                conn = mysql.connector.connect(
                    host=config["host"],
                    port=config.get("port", 3306),
                    database=config["database"],
                    user=config["user"],
                    password=config.get("password", ""),
                    connect_timeout=self.timeout,
                )
                cursor = conn.cursor()

                cursor.execute("SELECT VERSION();")
                row = cursor.fetchone()
                version = row[0] if row else None  # ty: ignore[index]  # ty:ignore[ignore-comment-unknown-rule, invalid-argument-type]

                cursor.execute("SELECT COUNT(*) FROM information_schema.schemata;")
                row = cursor.fetchone()
                schema_count = row[0] if row else None  # ty: ignore[index]  # ty:ignore[ignore-comment-unknown-rule, invalid-argument-type]

                cursor.execute("SELECT COUNT(*) FROM information_schema.tables;")
                row = cursor.fetchone()
                table_count = row[0] if row else None  # ty: ignore[index]  # ty:ignore[ignore-comment-unknown-rule, invalid-argument-type]

                cursor.close()
                conn.close()
                return {
                    "database_version": version,
                    "schema_count": schema_count,
                    "table_count": table_count,
                    "host": config["host"],
                    "port": config.get("port", 3306),
                    "database": config["database"],
                }

            loop = asyncio.get_running_loop()
            metadata = await loop.run_in_executor(None, _connect_and_query)
            return {"success": True, "message": "MySQL connection successful", "metadata": metadata}

        except ImportError:
            return {
                "success": False,
                "message": "mysql-connector-python not installed. Install with: pip install mysql-connector-python",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"MySQL connection failed: {str(e)}",
                "metadata": {},
            }

    async def _test_sqlite_connection(self, stave: Stave) -> dict[str, Any]:
        """Test SQLite connection using DataPulse."""
        try:
            # Import DataPulse SQLite read-only connector
            from metronome_pulse_sqlite import SQLiteReadonlyPulse

            config = stave.connection_config
            db_path = config.get("database_path", config.get("path"))

            # Create DataPulse read-only connector
            connector = SQLiteReadonlyPulse(db_path)

            # Connect to database
            await connector.connect()

            # Test connection by running simple queries
            version_result = await connector.query(
                "SELECT sqlite_version() as version;"
            )
            version = version_result[0]["version"] if version_result else "Unknown"

            table_result = await connector.query(
                "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table';"
            )
            table_count = table_result[0]["count"] if table_result else 0

            index_result = await connector.query(
                "SELECT COUNT(*) as count FROM sqlite_master WHERE type='index';"
            )
            index_count = index_result[0]["count"] if index_result else 0

            # Close connection
            await connector.close()

            return {
                "success": True,
                "message": "SQLite connection successful",
                "metadata": {
                    "database_version": version,
                    "table_count": table_count,
                    "index_count": index_count,
                    "path": db_path,
                    "file_size_mb": round(self._get_file_size_mb(db_path), 2),
                },
            }

        except ImportError:
            return {
                "success": False,
                "message": "metronome_pulse_sqlite not installed. Install with: pip install metronome-pulse-sqlite",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"SQLite connection failed: {str(e)}",
                "metadata": {},
            }

    async def _test_redis_connection(self, stave: Stave) -> dict[str, Any]:
        """Test Redis connection.

        The redis-py client is synchronous; run it in the default thread-pool
        executor to avoid blocking the event loop.
        """
        try:
            import redis

            config = stave.connection_config

            def _connect_and_query() -> dict[str, Any]:
                r = redis.Redis(
                    host=config["host"],
                    port=config.get("port", 6379),
                    db=config.get("db", 0),
                    password=config.get("password"),
                    socket_timeout=self.timeout,
                )
                info = cast(dict, r.info())
                return {
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "keyspace": info.get("db0", {}).get("keys", 0),
                    "host": config["host"],
                    "port": config.get("port", 6379),
                    "db": config.get("db", 0),
                }

            loop = asyncio.get_running_loop()
            metadata = await loop.run_in_executor(None, _connect_and_query)
            return {"success": True, "message": "Redis connection successful", "metadata": metadata}

        except ImportError:
            return {
                "success": False,
                "message": "redis not installed. Install with: pip install redis",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Redis connection failed: {str(e)}",
                "metadata": {},
            }

    async def _test_mongodb_connection(self, stave: Stave) -> dict[str, Any]:
        """Test MongoDB connection.

        pymongo is synchronous; run it in the default thread-pool executor to
        avoid blocking the event loop.
        """
        try:
            import pymongo  # type: ignore

            config = stave.connection_config

            def _connect_and_query() -> dict[str, Any]:
                client = pymongo.MongoClient(
                    config["uri"], serverSelectionTimeoutMS=self.timeout * 1000
                )
                server_info = client.server_info()
                db = client[config["database"]]
                collection_count = len(db.list_collection_names())
                client.close()
                return {
                    "mongodb_version": server_info.get("version"),
                    "database": config["database"],
                    "collection_count": collection_count,
                    "uri": config["uri"].replace(config.get("password", ""), "***")
                    if config.get("password")
                    else config["uri"],
                }

            loop = asyncio.get_running_loop()
            metadata = await loop.run_in_executor(None, _connect_and_query)
            return {"success": True, "message": "MongoDB connection successful", "metadata": metadata}

        except ImportError:
            return {
                "success": False,
                "message": "pymongo not installed. Install with: pip install pymongo",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"MongoDB connection failed: {str(e)}",
                "metadata": {},
            }

    async def _test_bigquery_connection(self, stave: Stave) -> dict[str, Any]:
        """Test BigQuery connection using DataPulse."""
        try:
            # Import DataPulse BigQuery read-only connector
            from metronome_pulse_bigquery import BigQueryReadonlyPulse

            config = stave.connection_config

            # Create DataPulse read-only connector
            connector = BigQueryReadonlyPulse(
                project_id=config["project_id"],
                credentials_path=config.get("credentials_path"),
                credentials_json=config.get("credentials_json"),
                dataset=config.get("dataset"),
                location=config.get("location", "US"),
            )

            # Connect to BigQuery
            await connector.connect()

            # Test connection by checking if it's connected
            is_connected = await connector.is_connected()
            if not is_connected:
                await connector.close()
                return {
                    "success": False,
                    "message": "BigQuery connection established but health check failed",
                    "metadata": {},
                }

            # Get project info
            project_id = config["project_id"]
            dataset = config.get("dataset", "default")

            # Try to list datasets or tables if dataset is specified
            metadata = {
                "project_id": project_id,
                "location": config.get("location", "US"),
            }

            if dataset:
                metadata["dataset"] = dataset
                try:
                    # Handle public datasets (e.g., bigquery-public-data.samples)
                    # If dataset contains a dot, it's likely project.dataset format
                    dataset_for_listing = dataset

                    # If dataset is just "bigquery-public-data", it's a project, not a dataset
                    # Try a common public dataset instead
                    if dataset == "bigquery-public-data":
                        dataset_for_listing = "bigquery-public-data.samples"
                        metadata["note"] = (
                            f"Note: 'bigquery-public-data' is a project, not a dataset. "
                            f"Trying common public dataset 'bigquery-public-data.samples'. "
                            f"For other public datasets, use format 'bigquery-public-data.DATASET_NAME'"
                        )

                    # Try to list tables in the dataset
                    tables = await connector.list_tables(dataset_for_listing)
                    metadata["table_count"] = len(tables) if tables else 0

                    # If we used a different dataset for listing, add info
                    if dataset_for_listing != dataset and "table_count" in metadata:
                        if metadata.get("note"):
                            metadata[
                                "note"
                            ] += f" Found {metadata['table_count']} tables."
                        else:
                            metadata[
                                "note"
                            ] = f"Found {metadata['table_count']} tables."

                except Exception as e:
                    error_msg = str(e)
                    logger.warning("Could not list tables for dataset %s: %s", dataset, e)

                    # Provide helpful guidance for common errors
                    if "404" in error_msg or "Not found" in error_msg:
                        if dataset == "bigquery-public-data":
                            metadata["note"] = (
                                f"'bigquery-public-data' is a project, not a dataset. "
                                f"Use format 'bigquery-public-data.DATASET_NAME' (e.g., 'bigquery-public-data.samples'). "
                                f"Connection successful, but cannot list tables without a specific dataset."
                            )
                        elif "." not in dataset:
                            metadata["note"] = (
                                f"Dataset '{dataset}' not found in project '{project_id}'. "
                                f"If this is a public dataset, use format 'PROJECT.DATASET' (e.g., 'bigquery-public-data.samples'). "
                                f"Connection successful, but cannot list tables."
                            )
                        else:
                            metadata["note"] = f"Could not list tables: {error_msg}"
                    else:
                        metadata["note"] = f"Could not list tables: {error_msg}"

            # Close connection
            await connector.close()

            return {
                "success": True,
                "message": "BigQuery connection successful",
                "metadata": metadata,
            }

        except ImportError:
            return {
                "success": False,
                "message": "metronome_pulse_bigquery not installed. Install with: pip install metronome-pulse-bigquery",
                "metadata": {},
            }
        except KeyError as e:
            return {
                "success": False,
                "message": f"Missing required BigQuery configuration: {str(e)}",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"BigQuery connection failed: {str(e)}",
                "metadata": {},
            }

    async def _test_api_connection(self, stave: Stave) -> dict[str, Any]:
        """Test API/HTTP connection.

        The requests library is synchronous; run it in the default thread-pool
        executor to avoid blocking the event loop.
        """
        try:
            import requests  # type: ignore

            config = stave.connection_config
            base_url = config["base_url"]
            headers: dict[str, str] = {}
            if config.get("api_key"):
                headers["Authorization"] = f"Bearer {config['api_key']}"

            def _do_request() -> dict[str, Any]:
                response = requests.get(base_url, headers=headers, timeout=self.timeout)
                return {
                    "status_code": response.status_code,
                    "status_text": str(response.status_code),
                    "base_url": base_url,
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                    "content_type": response.headers.get("content-type", "unknown"),
                }

            loop = asyncio.get_running_loop()
            metadata = await loop.run_in_executor(None, _do_request)
            return {
                "success": True,
                "message": f"API connection successful (HTTP {metadata['status_code']})",
                "metadata": metadata,
            }

        except ImportError:
            return {
                "success": False,
                "message": "requests not installed. Install with: pip install requests",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"API connection failed: {str(e)}",
                "metadata": {},
            }

    def _get_file_size_mb(self, file_path: str) -> float:
        """Get file size in MB."""
        try:
            import os

            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except OSError:
            return 0.0
