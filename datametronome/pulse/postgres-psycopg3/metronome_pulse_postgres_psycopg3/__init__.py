"""
DataPulse PostgreSQL Connector using psycopg3

A modern, async-first PostgreSQL connector for the DataPulse ecosystem.
Built on psycopg3 for maximum compatibility and performance.
"""

from .connector import PostgresPsycopg3Pulse

__version__ = "0.1.0"
__all__ = ["PostgresPsycopg3Pulse"]

