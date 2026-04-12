"""
BigQuery read-only DataPulse connector.

This connector provides read-only access to BigQuery for data quality checks.
All implementation is inherited from _BigQueryBase.
"""

from metronome_pulse_bigquery.base import _BigQueryBase


class BigQueryReadonlyPulse(_BigQueryBase):
    """Read-only BigQuery DataPulse connector.

    Implements Pulse and Readable interfaces for safe read-only operations.
    Write operations are intentionally absent.
    """
