"""
DataPulse PostgreSQL Connector using psycopg3

A modern, async-first PostgreSQL connector for the DataPulse ecosystem.
Built on psycopg3 for maximum compatibility and performance.

This is also the Redshift path: asyncpg cannot connect to Redshift, psycopg3
can.
"""

from .connector import PostgresPsycopg3Pulse
from .readonly_connector import PostgresPsycopg3ReadOnlyPulse

__version__ = "0.1.0"
__all__ = ["PostgresPsycopg3Pulse", "PostgresPsycopg3ReadOnlyPulse"]
