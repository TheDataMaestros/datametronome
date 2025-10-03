"""
DataPulse Core Interfaces Package

This package defines the abstract interfaces that all DataPulse connectors must implement.
It contains no logic; only the contracts for lifecycle management and data interaction.
"""

from .interfaces import Pulse, Readable, Writable, ReadOnlyConnector, WriteOnlyConnector, ReadWriteConnector

__version__ = "0.1.0"
__all__ = ["Pulse", "Readable", "Writable", "ReadOnlyConnector", "WriteOnlyConnector", "ReadWriteConnector"]
