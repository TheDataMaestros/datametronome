"""
BigQuery DataPulse connector for Google BigQuery.

This package provides async-first connectivity to Google BigQuery with full
support for the DataPulse ecosystem.
"""

from .connector import BigQueryPulse
from .readonly_connector import BigQueryReadonlyPulse

__all__ = ["BigQueryPulse", "BigQueryReadonlyPulse"]
__version__ = "0.1.0"
