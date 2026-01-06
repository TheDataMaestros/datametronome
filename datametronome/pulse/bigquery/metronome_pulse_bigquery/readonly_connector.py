"""
BigQuery read-only DataPulse connector.

This connector provides read-only access to BigQuery for data quality checks.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from google.cloud import bigquery  # type: ignore
from google.oauth2 import service_account  # type: ignore
from metronome_pulse_core.interfaces import Pulse, Readable

logger = logging.getLogger(__name__)


class BigQueryReadonlyPulse(Pulse, Readable):
    """Read-only BigQuery DataPulse connector.

    Implements Pulse and Readable interfaces for safe read-only operations.
    """

    def __init__(
        self,
        project_id: str,
        credentials_path: Optional[str] = None,
        credentials_json: Optional[Dict] = None,
        dataset: Optional[str] = None,
        location: str = "US",
        **kwargs,
    ):
        """Initialize the BigQuery read-only connector.

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON file
            credentials_json: Service account credentials as dict
            dataset: Default dataset name
            location: BigQuery location (e.g., 'US', 'EU')
            **kwargs: Additional connection parameters
        """
        self._project_id = project_id
        self._credentials_path = credentials_path
        self._credentials_json = credentials_json
        self._dataset = dataset
        self._location = location
        self._kwargs = kwargs
        self._client = None

    async def connect(self) -> None:
        """Establish connection to BigQuery."""
        try:
            # Get credentials
            credentials = None
            if self._credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self._credentials_path
                )
            elif self._credentials_json:
                credentials = service_account.Credentials.from_service_account_info(
                    self._credentials_json
                )

            # Create BigQuery client
            self._client = bigquery.Client(
                project=self._project_id,
                credentials=credentials,
                location=self._location,
                **self._kwargs,
            )

        except Exception as e:
            raise ConnectionError(f"Failed to connect to BigQuery: {e}")

    async def close(self) -> None:
        """Close BigQuery connection."""
        if self._client:
            self._client.close()
            self._client = None

    async def is_connected(self) -> bool:
        """Check if connected to BigQuery and connection is healthy.

        Returns:
            True if connected and connection is valid, False otherwise
        """
        if self._client is None:
            return False

        try:
            # Verify connection is actually working by running a simple query
            loop = asyncio.get_event_loop()
            client = self._client
            assert client is not None
            # Use a simple query that should work in any BigQuery project
            query_job = await loop.run_in_executor(
                None,
                lambda: client.query(
                    "SELECT 1 as health_check",
                    job_config=bigquery.QueryJobConfig(dry_run=True),
                ),
            )
            # Dry run will succeed if connection is valid without actually running the query
            return True
        except Exception:
            # Connection exists but is invalid
            self._client = None
            return False

    async def query(self, query_config) -> List[Dict[str, Any]]:
        """Execute a read-only query and return results.

        Args:
            query_config: Can be:
                - str: Direct SQL query
                - dict: Query configuration with 'sql' and optional 'params'

        Returns:
            List of dictionaries representing the query results
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        try:
            # Parse query config
            if isinstance(query_config, str):
                sql = query_config
                params = None
            elif isinstance(query_config, dict):
                sql = query_config.get("sql", query_config.get("query", ""))
                params = query_config.get("params", query_config.get("parameters"))
            else:
                raise ValueError(f"Invalid query_config type: {type(query_config)}")

            # Run query in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            client = self._client
            assert client is not None
            query_job = await loop.run_in_executor(
                None,
                lambda: client.query(sql, job_config=self._get_job_config(params)),
            )

            # Get results
            results = await loop.run_in_executor(None, lambda: list(query_job.result()))

            # Convert to list of dicts
            return [dict(row) for row in results]

        except Exception as e:
            raise Exception(f"Query execution failed: {e}")

    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information.

        Args:
            table_name: Name of the table. Can be:
                - "table" (uses default dataset from connector)
                - "dataset.table" (uses project from connector)
                - "project.dataset.table" (fully qualified)

        Returns:
            List of column information dictionaries
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        try:
            # Parse table name - handle different formats
            parts = table_name.split(".")

            if len(parts) == 3:
                # Fully qualified: project.dataset.table
                project_id, dataset_id, table_id = parts
                table_ref = f"{project_id}.{dataset_id}.{table_id}"
            elif len(parts) == 2:
                # Dataset.table format - use project from connector
                dataset_id, table_id = parts
                table_ref = f"{self._project_id}.{dataset_id}.{table_id}"
            elif len(parts) == 1:
                # Just table name - use dataset and project from connector
                if not self._dataset:
                    raise ValueError(
                        f"Dataset not specified. Either provide dataset in table_name "
                        f"(format: 'dataset.table' or 'project.dataset.table') or set "
                        f"dataset in connector initialization."
                    )
                dataset_id = self._dataset
                table_id = table_name
                # Handle case where dataset might be project.dataset format
                if "." in dataset_id:
                    # Dataset already contains project, use as-is
                    table_ref = f"{dataset_id}.{table_id}"
                else:
                    table_ref = f"{self._project_id}.{dataset_id}.{table_id}"
            else:
                raise ValueError(f"Invalid table name format: {table_name}")

            # Get table
            loop = asyncio.get_event_loop()
            client = self._client
            assert client is not None
            table = await loop.run_in_executor(
                None,
                lambda: client.get_table(table_ref),
            )

            # Return schema information
            if not table.schema:
                logger.warning(
                    f"Table '{table_name}' exists but has no schema. "
                    f"This is unusual and might indicate a problem with the query or permissions."
                )
                return []

            return [
                {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or "",
                }
                for field in table.schema
            ]

        except Exception as e:
            raise Exception(f"Failed to get table info for '{table_name}': {e}")

    async def list_tables(self, dataset: Optional[str] = None) -> List[str]:
        """List all tables in a dataset.

        Args:
            dataset: Dataset name (uses default if not specified)

        Returns:
            List of table names
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        dataset_id = dataset or self._dataset
        if not dataset_id:
            raise ValueError("Dataset must be specified")

        try:
            loop = asyncio.get_event_loop()
            client = self._client
            assert client is not None
            tables = await loop.run_in_executor(None, lambda: list(client.list_tables(dataset_id)))
            return [table.table_id for table in tables]

        except Exception as e:
            raise Exception(f"Failed to list tables: {e}")

    def _get_job_config(self, params: Optional[List] = None) -> Optional[bigquery.QueryJobConfig]:
        """Get job config for parameterized queries.

        Args:
            params: Query parameters

        Returns:
            QueryJobConfig or None
        """
        if not params:
            return None

        # Convert parameters to appropriate BigQuery types
        query_parameters = []
        for param in params:
            if isinstance(param, bool):
                query_parameters.append(bigquery.ScalarQueryParameter(None, "BOOL", param))
            elif isinstance(param, int):
                query_parameters.append(bigquery.ScalarQueryParameter(None, "INT64", param))
            elif isinstance(param, float):
                query_parameters.append(bigquery.ScalarQueryParameter(None, "FLOAT64", param))
            elif isinstance(param, str):
                query_parameters.append(bigquery.ScalarQueryParameter(None, "STRING", param))
            elif param is None:
                query_parameters.append(bigquery.ScalarQueryParameter(None, "STRING", None))
            else:
                # Fallback to string for other types
                query_parameters.append(bigquery.ScalarQueryParameter(None, "STRING", str(param)))

        return bigquery.QueryJobConfig(query_parameters=query_parameters)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
