"""
BigQuery read-only DataPulse connector.

This connector provides read-only access to BigQuery for data quality checks.
"""

import asyncio
from typing import Any, Dict, List, Optional

from google.cloud import bigquery  # type: ignore
from google.oauth2 import service_account  # type: ignore
from metronome_pulse_core.interfaces import Pulse, Readable


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
        """Check if connected to BigQuery."""
        return self._client is not None

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
            assert self._client is not None
            query_job = await loop.run_in_executor(
                None,
                lambda: self._client.query(
                    sql, job_config=self._get_job_config(params)
                ),
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
            table_name: Name of the table

        Returns:
            List of column information dictionaries
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        try:
            # Parse table name
            if "." in table_name:
                dataset_id, table_id = table_name.split(".", 1)
            else:
                dataset_id = self._dataset
                table_id = table_name

            # Get table
            loop = asyncio.get_event_loop()
            assert self._client is not None
            table = await loop.run_in_executor(
                None,
                lambda: self._client.get_table(
                    f"{self._project_id}.{dataset_id}.{table_id}"
                ),
            )

            # Return schema information
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
            raise Exception(f"Failed to get table info: {e}")

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
            assert self._client is not None
            tables = await loop.run_in_executor(
                None, lambda: list(self._client.list_tables(dataset_id))
            )
            return [table.table_id for table in tables]

        except Exception as e:
            raise Exception(f"Failed to list tables: {e}")

    def _get_job_config(
        self, params: Optional[List] = None
    ) -> Optional[bigquery.QueryJobConfig]:
        """Get job config for parameterized queries.

        Args:
            params: Query parameters

        Returns:
            QueryJobConfig or None
        """
        if params:
            # BigQuery uses named or positional parameters
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(None, "STRING", str(p))
                    for p in params
                ]
            )
            return job_config
        return None
