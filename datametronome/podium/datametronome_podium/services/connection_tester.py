"""Connection Tester - checks that a stave's configuration actually connects.

One entry per data source in _TESTERS at the bottom of the class. There used
to be an if/elif chain here instead, and it had drifted out of step with what
the platform accepts: it still dispatched MySQL, Redis, MongoDB and HTTP,
none of which have a connector or pass stave validation, so those arms could
not be reached.
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
            tester = self._TESTERS.get(stave.data_source_type)
            if tester is None:
                result = {
                    "success": False,
                    "message": f"Unsupported data source type: {stave.data_source_type}",
                    "metadata": {},
                }
            else:
                result = await tester(self, stave)

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
        """Test a PostgreSQL or Redshift connection.

        The connector comes from the factory rather than being built here.
        Building it locally meant this path and the check path could drift,
        and they did: the factory learned to pass ssl through and this did
        not, so a stave could pass its connection test and then fail every
        check. It also hardcoded asyncpg, which cannot reach Redshift.
        """
        config = stave.connection_config
        label = "Redshift" if stave.data_source_type == "redshift" else "PostgreSQL"
        default_port = 5439 if stave.data_source_type == "redshift" else 5432

        try:
            connector = await self.get_connector(stave, read_only=True)
        except Exception as e:
            return {
                "success": False,
                "message": f"{label} connection failed: {e}",
                "metadata": {},
            }

        try:
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

            return {
                "success": True,
                "message": f"{label} connection successful",
                "metadata": {
                    "database_version": version,
                    "schema_count": schema_count,
                    "table_count": table_count,
                    "host": config["host"],
                    "port": config.get("port", default_port),
                    "database": config["database"],
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"{label} connection failed: {e}",
                "metadata": {},
            }
        finally:
            await connector.close()

    async def _test_s3_connection(self, stave: Stave) -> dict[str, Any]:
        """Test an S3 stave by counting the rows behind each configured table.

        Listing the bucket would prove credentials and nothing else. Reading
        each table proves the path resolves, the format is what the extension
        claims, and the object is readable, which is what a check needs.
        """
        config = stave.connection_config

        try:
            connector = await self.get_connector(stave, read_only=True)
        except Exception as e:
            return {
                "success": False,
                "message": f"S3 connection failed: {e}",
                "metadata": {},
            }

        try:
            counts = {}
            for name in (config.get("tables") or {}):
                rows = await connector.query(
                    f'SELECT COUNT(*) AS n FROM "{name}"'
                )
                counts[name] = rows[0]["n"] if rows else 0

            return {
                "success": True,
                "message": f"S3 connection successful, {len(counts)} table(s) readable",
                "metadata": {
                    "bucket": config.get("bucket"),
                    "region": config.get("region", "us-east-1"),
                    "row_counts": counts,
                    "credentials": (
                        "explicit keys"
                        if config.get("access_key_id")
                        else "instance role or environment"
                    ),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"S3 connection failed: {e}",
                "metadata": {"bucket": config.get("bucket")},
            }
        finally:
            await connector.close()

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
                        found = f"Found {metadata['table_count']} tables."
                        existing = metadata.get("note")
                        metadata["note"] = f"{existing} {found}" if existing else found

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

    async def _test_dbt_connection(self, stave: Stave) -> dict[str, Any]:
        """Test dbt artifact connection using DbtReadonlyPulse."""
        try:
            from metronome_pulse_dbt import DbtReadonlyPulse

            config = stave.connection_config

            connector = DbtReadonlyPulse(
                mode=config.get("mode", "local"),
                project_path=config.get("project_path", ""),
                target_path=config.get("target_path", "target"),
                api_token=config.get("api_token", ""),
                account_id=config.get("account_id", ""),
                job_id=config.get("job_id", ""),
                base_url=config.get(
                    "base_url", "https://cloud.getdbt.com/api/v2"
                ),
            )

            await connector.connect()

            models = await connector.query("models")
            sources = await connector.query("sources")
            tests = await connector.query("tests")

            await connector.close()

            return {
                "success": True,
                "message": "dbt connection successful",
                "metadata": {
                    "mode": config.get("mode", "local"),
                    "model_count": len(models),
                    "source_count": len(sources),
                    "test_count": len(tests),
                },
            }

        except ImportError:
            return {
                "success": False,
                "message": "metronome_pulse_dbt not installed. Install with: pip install metronome-pulse-dbt",
                "metadata": {},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"dbt connection failed: {str(e)}",
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

    # Keys must match features.staves.model.SUPPORTED_DATA_SOURCES.
    # test_connection_tester.py asserts that, so a new stave type cannot ship
    # with no way to test it.
    _TESTERS = {
        "postgres": _test_postgres_connection,
        "postgresql": _test_postgres_connection,
        "redshift": _test_postgres_connection,
        "sqlite": _test_sqlite_connection,
        "bigquery": _test_bigquery_connection,
        "s3": _test_s3_connection,
        "dbt": _test_dbt_connection,
    }
