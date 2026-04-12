"""
BigQuery DataPulse connector using google-cloud-bigquery.

This connector provides async-first BigQuery connectivity with full support
for the DataPulse ecosystem, including write operations.
"""

import asyncio
from typing import Any

from google.cloud import bigquery  # type: ignore
from metronome_pulse_core.interfaces import Writable

from metronome_pulse_bigquery.base import _BigQueryBase


class BigQueryPulse(_BigQueryBase, Writable):
    """Full-featured BigQuery DataPulse connector.

    Implements all interfaces: Pulse, Readable, and Writable.
    Read operations are inherited from _BigQueryBase.
    """

    async def write(
        self,
        data: list[dict],
        destination: str,
        config: dict | None = None,
    ) -> None:
        """Write data to a BigQuery table via a load job.

        Args:
            data: Rows to write as a list of dicts.
            destination: Target table. Accepts ``"table"`` (uses the dataset
                from the constructor) or ``"dataset.table"``.
            config: Optional write settings. Pass ``{"mode": "replace"}`` to
                truncate the table before loading (default is append).
        """
        if not await self.is_connected():
            raise RuntimeError("Not connected to BigQuery")

        if not data:
            return

        try:
            if "." in destination:
                dataset_id, table_id = destination.split(".", 1)
            else:
                dataset_id = self._dataset
                table_id = destination

            if not dataset_id:
                raise ValueError(
                    "Dataset must be specified in destination or constructor"
                )

            assert self._client is not None
            table_ref = self._client.dataset(dataset_id).table(table_id)

            write_disposition = bigquery.WriteDisposition.WRITE_APPEND
            if config and config.get("mode") == "replace":
                write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE

            job_config = bigquery.LoadJobConfig(
                write_disposition=write_disposition,
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            )

            loop = asyncio.get_event_loop()
            client = self._client
            assert client is not None
            load_job = await loop.run_in_executor(
                None,
                lambda: client.load_table_from_json(
                    data, table_ref, job_config=job_config
                ),
            )
            await loop.run_in_executor(None, load_job.result)

        except Exception as e:
            raise Exception(f"Write operation failed: {e}")
