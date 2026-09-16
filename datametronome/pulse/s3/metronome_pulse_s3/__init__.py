"""DataPulse S3 connector.

Query Parquet, CSV and JSON objects in an S3 bucket as SQL tables, using
DuckDB's httpfs extension. Read-only: there is no write path, and statements
that would write are rejected.
"""

from .connector import S3ReadonlyPulse

__version__ = "0.1.0"
__all__ = ["S3ReadonlyPulse"]
