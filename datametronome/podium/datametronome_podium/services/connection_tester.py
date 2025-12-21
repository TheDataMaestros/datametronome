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
from typing import Any, Dict, Optional

from datametronome_podium.models.stave import Stave

logger = logging.getLogger(__name__)


class ConnectionTester:
    """
    Tests connections to various data sources.

    This class provides methods to test connectivity to different types of
    data sources based on stave configurations.
    """

    def __init__(self):
        self.timeout = 10  # seconds

    async def test_connection(self, stave: Stave) -> Dict[str, Any]:
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
            elif stave.data_source_type in ["api", "http"]:
                result = await self._test_api_connection(stave)
            else:
                result = {
                    "success": False,
                    "message": f"Unsupported data source type: {stave.data_source_type}",
                    "metadata": {},
                }

            connection_time = time.time() - start_time
            result["connection_time"] = connection_time

            return result

        except Exception as e:
            connection_time = time.time() - start_time
            logger.error(f"Connection test failed for {stave.name}: {e}")
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
        data_source_type = (stave.data_source_type or "").lower()
        config = stave.connection_config or {}

        try:
            if data_source_type in ["postgres", "postgresql"]:
                if read_only:
                    from metronome_pulse_postgres import (
                        PostgresReadOnlyPulse as PulseClass,
                    )
                else:
                    from metronome_pulse_postgres import PostgresPulse as PulseClass

                connector = PulseClass(
                    host=config["host"],
                    port=config.get("port", 5432),
                    database=config["database"],
                    user=config["user"],
                    password=config.get("password", ""),
                )

            elif data_source_type == "sqlite":
                db_path = config.get("database_path") or config.get("path")
                if not db_path:
                    raise RuntimeError(
                        "SQLite connection requires 'database_path' or 'path' in connection_config"
                    )

                if read_only:
                    from metronome_pulse_sqlite import SQLiteReadonlyPulse as PulseClass
                else:
                    from metronome_pulse_sqlite import SQLitePulse as PulseClass

                connector = PulseClass(db_path)

            elif data_source_type == "bigquery":
                if read_only:
                    from metronome_pulse_bigquery import (
                        BigQueryReadonlyPulse as PulseClass,  # type: ignore
                    )
                else:
                    from metronome_pulse_bigquery import (
                        BigQueryPulse as PulseClass,  # type: ignore
                    )

                connector = PulseClass(
                    project_id=config["project_id"],
                    credentials_path=config.get("credentials_path"),
                    credentials_json=config.get("credentials_json"),
                    dataset=config.get("dataset"),
                    location=config.get("location", "US"),
                )

            else:
                raise RuntimeError(
                    f"Unsupported data source type: {stave.data_source_type}"
                )

        except KeyError as exc:
            raise RuntimeError(f"Missing required connection field: {exc}") from exc
        except ImportError as exc:
            raise RuntimeError(
                f"Required connector package is not installed: {exc.name}"
            ) from exc

        await connector.connect()
        return connector

    async def _test_postgres_connection(self, stave: Stave) -> Dict[str, Any]:
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

    async def _test_mysql_connection(self, stave: Stave) -> Dict[str, Any]:
        """Test MySQL connection."""
        try:
            # Import here to avoid dependency issues if mysql-connector is not installed
            import mysql.connector  # type: ignore

            config = stave.connection_config

            # Test connection
            conn = mysql.connector.connect(
                host=config["host"],
                port=config.get("port", 3306),
                database=config["database"],
                user=config["user"],
                password=config.get("password", ""),
                connect_timeout=self.timeout,
            )

            # Get basic info
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION();")
            version = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM information_schema.schemata;")
            schema_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM information_schema.tables;")
            table_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return {
                "success": True,
                "message": "MySQL connection successful",
                "metadata": {
                    "database_version": version,
                    "schema_count": schema_count,
                    "table_count": table_count,
                    "host": config["host"],
                    "port": config.get("port", 3306),
                    "database": config["database"],
                },
            }

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

    async def _test_sqlite_connection(self, stave: Stave) -> Dict[str, Any]:
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

    async def _test_redis_connection(self, stave: Stave) -> Dict[str, Any]:
        """Test Redis connection."""
        try:
            # Import here to avoid dependency issues if redis is not installed
            import redis

            config = stave.connection_config

            # Create Redis client
            r = redis.Redis(
                host=config["host"],
                port=config.get("port", 6379),
                db=config.get("db", 0),
                password=config.get("password"),
                socket_timeout=self.timeout,
            )

            # Test connection
            info: Any = r.info()

            return {
                "success": True,
                "message": "Redis connection successful",
                "metadata": {
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "keyspace": info.get("db0", {}).get("keys", 0),
                    "host": config["host"],
                    "port": config.get("port", 6379),
                    "db": config.get("db", 0),
                },
            }

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

    async def _test_mongodb_connection(self, stave: Stave) -> Dict[str, Any]:
        """Test MongoDB connection."""
        try:
            # Import here to avoid dependency issues if pymongo is not installed
            import pymongo  # type: ignore

            config = stave.connection_config

            # Create MongoDB client
            client = pymongo.MongoClient(
                config["uri"], serverSelectionTimeoutMS=self.timeout * 1000
            )

            # Test connection
            server_info = client.server_info()
            db = client[config["database"]]
            collection_count = len(db.list_collection_names())

            client.close()

            return {
                "success": True,
                "message": "MongoDB connection successful",
                "metadata": {
                    "mongodb_version": server_info.get("version"),
                    "database": config["database"],
                    "collection_count": collection_count,
                    "uri": config["uri"].replace(config.get("password", ""), "***")
                    if config.get("password")
                    else config["uri"],
                },
            }

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

    async def _test_api_connection(self, stave: Stave) -> Dict[str, Any]:
        """Test API/HTTP connection."""
        try:
            # Import here to avoid dependency issues if requests is not installed
            import requests  # type: ignore

            config = stave.connection_config
            base_url = config["base_url"]

            # Test connection with a simple GET request
            headers = {}
            if config.get("api_key"):
                headers["Authorization"] = f"Bearer {config['api_key']}"

            response = requests.get(base_url, headers=headers, timeout=self.timeout)

            return {
                "success": True,
                "message": f"API connection successful (HTTP {response.status_code})",
                "metadata": {
                    "status_code": response.status_code,
                    "base_url": base_url,
                    "response_time_ms": round(
                        response.elapsed.total_seconds() * 1000, 2
                    ),
                    "content_type": response.headers.get("content-type", "unknown"),
                },
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
        except:
            return 0.0
