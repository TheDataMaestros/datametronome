"""
DataPulse PostgreSQL Connector using asyncpg

A high-performance, async-first PostgreSQL connector for the DataPulse ecosystem.
Built on asyncpg for maximum performance and connection pooling.
"""

from .connector import PostgresPulse
from .readonly_connector import PostgresReadOnlyPulse
from .writeonly_connector import PostgresWriteOnlyPulse

__version__ = "0.1.0"
__all__ = [
    "PostgresPulse",           # Full-featured (read + write)
    "PostgresReadOnlyPulse",   # Read-only only
    "PostgresWriteOnlyPulse"   # Write-only only
]
