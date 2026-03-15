"""
Structural typing boundary for Pulse connectors.

PulseProtocol defines the shared interface that all Pulse connectors
(PostgresPulse, SQLitePulse, etc.) must satisfy. It uses Python's
Protocol for structural subtyping — connectors don't need to inherit
from this class, they just need to implement the methods.

The existing ABC hierarchy (Pulse, Readable, Writable) in interfaces.py
remains as the internal inheritance contract. PulseProtocol is the
external contract used by consumers (e.g. podium's QueryExecutor).
"""
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PulseProtocol(Protocol):
    """Shared interface all Pulse connectors must satisfy."""

    # --- Lifecycle ---
    async def connect(self) -> None: ...
    async def close(self) -> None: ...

    # --- Read ---
    async def query(self, query_config: str | dict) -> list[dict]: ...
    async def query_with_params(
        self, sql: str, params: list[Any] | None = None
    ) -> list[dict]: ...

    # --- Write ---
    async def execute(
        self, sql: str, params: list[Any] | None = None
    ) -> int: ...
    async def execute_many(
        self, sql: str, params_list: list[list[Any]]
    ) -> None: ...
    async def write(
        self,
        data: list[dict[str, Any]],
        destination: str,
        config: dict[str, Any] | None = None,
    ) -> None: ...

    # --- Introspection ---
    async def list_tables(self) -> list[str]: ...
    async def get_table_info(self, table_name: str) -> list[dict]: ...

    # --- Transactions ---
    async def begin_transaction(self) -> None: ...
    async def commit_transaction(self) -> None: ...
    async def rollback_transaction(self) -> None: ...

    # --- Context manager ---
    async def __aenter__(self) -> "PulseProtocol": ...
    async def __aexit__(self, *args: Any) -> None: ...
