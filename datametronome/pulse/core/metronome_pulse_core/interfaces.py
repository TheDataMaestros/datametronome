"""
Core interfaces for DataPulse connectors.

Three small contracts: lifecycle, read, write. A connector mixes in the ones
it can honour. Nothing here has a default implementation -- a connector that
cannot do something does not inherit the interface for it.
"""

from abc import ABC, abstractmethod


class Pulse(ABC):
    """Lifecycle contract every connector implements."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source.

        Raises:
            ConnectionError: If connection cannot be established
        """

    @abstractmethod
    async def close(self) -> None:
        """Close the connection. Call when the connector is no longer needed."""

    @abstractmethod
    async def is_connected(self) -> bool:
        """Return True while the connection is usable."""


class Readable(ABC):
    """Contract for connectors that can read data."""

    @abstractmethod
    async def query(self, query_config) -> list | dict:
        """Execute a query and return results.

        Args:
            query_config: SQL string, or a dict carrying the SQL plus options.

        Returns:
            List of dictionaries representing the query results

        Raises:
            RuntimeError: If not connected to the data source
            Exception: If the query fails
        """


class Writable(ABC):
    """Contract for connectors that can write data."""

    @abstractmethod
    async def write(self, data, destination: str, config: dict | None = None) -> None:
        """Write rows to a destination table.

        Args:
            data: List of dictionaries to write
            destination: Target table name
            config: Optional operation config. "replace" deletes then inserts;
                omitted means a plain insert.

        Raises:
            RuntimeError: If not connected to the data source
            Exception: If the write operation fails
        """
