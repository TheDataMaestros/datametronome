"""
DataPulse PostgreSQL Connector using asyncpg

A high-performance, async-first PostgreSQL connector for the DataPulse ecosystem.
Built on asyncpg for maximum performance and connection pooling.
"""

from .connector import PostgresPulse
from .readonly_connector import PostgresReadOnlyPulse

__version__ = "0.1.0"
__all__ = [
    "PostgresPulse",  # read + write
    "PostgresReadOnlyPulse",  # Read-only only
]
