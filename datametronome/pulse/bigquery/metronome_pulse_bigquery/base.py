"""
Shared BigQuery connector implementation.

Both BigQueryPulse (read-write) and BigQueryReadonlyPulse (read-only) inherit
from this base to avoid duplicating the connection lifecycle and query logic.
"""

import asyncio
import logging
from typing import Any

from google.cloud import bigquery  # type: ignore
from google.oauth2 import service_account  # type: ignore
from metronome_pulse_bigquery.job_config import build_query_job_config
from metronome_pulse_core.interfaces import Pulse, Readable

logger = logging.getLogger(__name__)


class _BigQueryBase(Pulse, Readable):
    """Internal base class for BigQuery connectors.

    Not part of the public API — use BigQueryPulse or BigQueryReadonlyPulse.
    """

    def __init__(
        self,
        project_id: str,
        credentials_path: str | None = None,
        credentials_json: dict | None = None,
        dataset: str | None = None,
        location: str = "US",
        **kwargs,
    ):
        """Initialise the BigQuery connector.

        Args:
            project_id: GCP project ID.
            credentials_path: Path to service account JSON file.
            credentials_json: Service account credentials as dict.
            dataset: Default dataset name.
            location: BigQuery location (e.g. 'US', 'EU').
            **kwargs: Additional parameters forwarded to bigquery.Client.
        """
        self._project_id = project_id
        self._credentials_path = credentials_path
        self._credentials_json = credentials_json
        self._dataset = dataset
        self._location = location
        self._kwargs = kwargs
        self._client: bigquery.Client | None = None

    # ------------------------------------------------------------------
    # Pulse interface
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish connection to BigQuery."""
        try:
            credentials = None
            if self._credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self._credentials_path
                )
            elif self._credentials_json:
                credentials = service_account.Credentials.from_service_account_info(
                    self._credentials_json
                )

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
        """Check whether the connection is alive.

        Uses a dry-run query so no slot quota is consumed.

        Returns:
            True if connected and healthy, False otherwise.
        """
        if self._client is None:
            return False

        try:
            loop = asyncio.get_running_loop()
            client = self._client
            # Dry run validates credentials and reachability without billing.
            await loop.run_in_executor(
                None,
                lambda: client.query(
                    "SELECT 1 as health_check",
                    job_config=bigquery.QueryJobConfig(dry_run=True),
                ),
            )
            return True
        except Exception:
            # Mark as disconnected so the next call triggers a reconnect attempt.
            self._client = None
            return False

    # ------------------------------------------------------------------
    # Readable interface
    # ------------------------------------------------------------------

    async def query(self, query_config) -> list[dict[str, Any]]:
        """Execute a query and return results.

        Args:
            query_config: Either a plain SQL string or a dict with keys:
                - ``sql`` / ``query``: the SQL statement
                - ``params``: positional parameters (list)
                - ``named_parameters``: named ``@param`` parameters (dict)

        Returns:
            List of row dicts.
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        try:
            if isinstance(query_config, str):
                sql = query_config
                params = None
                named_parameters = None
            elif isinstance(query_config, dict):
                sql = query_config.get("sql", query_config.get("query", ""))
                params = query_config.get("params", query_config.get("parameters"))
                named_parameters = query_config.get("named_parameters")
            else:
                raise ValueError(f"Invalid query_config type: {type(query_config)}")

            loop = asyncio.get_running_loop()
            client = self._client
            assert client is not None

            # named_parameters take precedence over positional params
            job_config = (
                build_query_job_config(None, named_parameters)
                if named_parameters
                else build_query_job_config(params, None)
            )

            query_job = await loop.run_in_executor(
                None,
                lambda: client.query(sql, job_config=job_config),
            )
            results = await loop.run_in_executor(None, lambda: list(query_job.result()))
            return [dict(row) for row in results]

        except Exception as e:
            raise Exception(f"Query execution failed: {e}") from e

    async def get_table_info(self, table_name: str) -> list[dict[str, Any]]:
        """Return schema information for a table.

        Args:
            table_name: Accepts three formats:
                - ``"table"`` — uses default dataset and project from constructor
                - ``"dataset.table"`` — uses project from constructor
                - ``"project.dataset.table"`` — fully qualified

        Returns:
            List of column information dicts (name, type, mode, description).
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        try:
            parts = table_name.split(".")

            if len(parts) == 3:
                table_ref = table_name  # already fully qualified
            elif len(parts) == 2:
                table_ref = f"{self._project_id}.{table_name}"
            elif len(parts) == 1:
                if not self._dataset:
                    raise ValueError(
                        "Dataset not specified. Either provide dataset in table_name "
                        "(format: 'dataset.table' or 'project.dataset.table') or set "
                        "dataset in connector initialization."
                    )
                # _dataset may itself be "project.dataset" — handle both shapes
                if "." in self._dataset:
                    table_ref = f"{self._dataset}.{table_name}"
                else:
                    table_ref = f"{self._project_id}.{self._dataset}.{table_name}"
            else:
                raise ValueError(f"Invalid table name format: {table_name}")

            loop = asyncio.get_running_loop()
            client = self._client
            assert client is not None
            table = await loop.run_in_executor(
                None, lambda: client.get_table(table_ref)
            )

            if not table.schema:
                logger.warning(
                    "Table '%s' exists but has no schema. This may indicate a "
                    "problem with the query or permissions.",
                    table_name,
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

    async def list_tables(self, dataset: str | None = None) -> list[str]:
        """List all tables in a dataset.

        Args:
            dataset: Dataset name; falls back to the constructor default.

        Returns:
            List of table IDs.
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        dataset_id = dataset or self._dataset
        if not dataset_id:
            raise ValueError("Dataset must be specified")

        try:
            loop = asyncio.get_running_loop()
            client = self._client
            assert client is not None
            tables = await loop.run_in_executor(
                None, lambda: list(client.list_tables(dataset_id))
            )
            return [table.table_id for table in tables]

        except Exception as e:
            raise Exception(f"Failed to list tables: {e}")

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
