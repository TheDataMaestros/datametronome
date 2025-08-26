"""
SQLite DataPulse Connector for DataMetronome.

This package provides SQLite-based DataPulse connectors for local storage
and development purposes. Business logic and table creation are handled by Podium.
"""

from .connector import SQLitePulse
from .readonly_connector import SQLiteReadonlyPulse
from .writeonly_connector import SQLiteWriteonlyPulse

__version__ = "0.1.0"
__all__ = ["SQLitePulse", "SQLiteReadonlyPulse", "SQLiteWriteonlyPulse"]
