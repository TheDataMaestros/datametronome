"""DbtReadonlyPulse — read-only Pulse connector for dbt artifacts."""
from __future__ import annotations

import logging
from typing import Any

from metronome_pulse_core.interfaces import Pulse, Readable

from .artifact_reader import ArtifactReader, CloudArtifactReader, LocalArtifactReader
from .parsers import (
    parse_columns,
    parse_exposures,
    parse_models,
    parse_sources,
    parse_test_results,
    parse_tests,
)
from .virtual_tables import VirtualTableEngine

logger = logging.getLogger(__name__)


class DbtReadonlyPulse(Pulse, Readable):
    """Read-only connector that exposes dbt project metadata as virtual tables.

    Supports two modes:
    - local: reads artifacts from filesystem ({project_path}/{target_path}/)
    - cloud: fetches artifacts from dbt Cloud API

    Connection config:
        Local:  DbtReadonlyPulse(mode="local", project_path="/path/to/dbt")
        Cloud:  DbtReadonlyPulse(mode="cloud", api_token="...", account_id="123", job_id="456")
    """

    def __init__(
        self,
        *,
        mode: str = "local",
        project_path: str = "",
        target_path: str = "target",
        api_token: str = "",
        account_id: str = "",
        job_id: str = "",
        base_url: str = "https://cloud.getdbt.com/api/v2",
        **kwargs: Any,
    ) -> None:
        self._mode = mode
        self._connected = False
        self._engine = VirtualTableEngine()
        self._reader: ArtifactReader

        if mode == "local":
            if not project_path:
                raise ValueError("project_path is required for local mode")
            self._reader = LocalArtifactReader(project_path, target_path)
        elif mode == "cloud":
            # All three cloud credentials are required — partial config is not valid
            if not all([api_token, account_id, job_id]):
                raise ValueError(
                    "api_token, account_id, and job_id are required for cloud mode"
                )
            self._reader = CloudArtifactReader(api_token, account_id, job_id, base_url)
        else:
            raise ValueError(f"Unsupported mode: {mode!r}. Use 'local' or 'cloud'.")

    # --- Lifecycle ---

    async def connect(self) -> None:
        """Load artifacts and build virtual tables."""
        if self._connected:
            return

        manifest = await self._reader.read_manifest()
        run_results = await self._reader.read_run_results()
        catalog = await self._reader.read_catalog()

        self._engine.register_table("models", parse_models(manifest))
        self._engine.register_table("sources", parse_sources(manifest))
        self._engine.register_table("tests", parse_tests(manifest))
        self._engine.register_table("exposures", parse_exposures(manifest))

        # run_results and catalog are optional — register only when available
        if run_results:
            self._engine.register_table("test_results", parse_test_results(run_results))
        if catalog:
            self._engine.register_table("columns", parse_columns(catalog))

        self._connected = True
        logger.info(
            "dbt connector ready — %d virtual tables loaded",
            len(self._engine.list_tables()),
        )

    async def close(self) -> None:
        self._connected = False

    async def is_connected(self) -> bool:
        return self._connected

    # --- Read ---

    async def query(self, query_config: str | dict) -> list[dict]:
        """Query virtual tables by table name string or query dict."""
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._engine.query(query_config)

    async def query_with_params(self, sql: str, params: list[Any] | None = None) -> list[dict]:
        """Delegate to query() for plain identifiers; reject SQL strings with a helpful error.

        The params argument is accepted for protocol compatibility but ignored —
        virtual table queries do not support SQL parameter binding.
        """
        stripped = sql.strip()
        # Plain identifier has no spaces and doesn't start with a SQL keyword
        if stripped and " " not in stripped and not _is_sql(stripped):
            return await self.query(stripped)
        raise ValueError(
            f"SQL queries are not supported by the dbt connector. "
            f"Pass a virtual table name instead."
        )

    # --- Introspection ---

    async def list_tables(self) -> list[str]:
        """Return dbt model names (the user's data objects, not internal virtual table names).

        This contract mirrors other connectors: list_tables exposes what the user
        cares about (their models), not the connector's internal organisation.
        """
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")
        models = self._engine.query("models")
        return [m["name"] for m in models]

    async def get_table_info(self, table_name: str) -> list[dict]:
        """Return column info for a dbt model by name.

        Uses the columns virtual table populated from catalog.json.
        Matching is case-insensitive because some warehouses (e.g. Snowflake)
        uppercase catalog names while manifest names stay lowercase.
        Returns an empty list when no catalog was loaded or the model
        has no column metadata.
        """
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")
        try:
            all_cols = self._engine.query("columns")
        except ValueError:
            return []
        needle = table_name.lower()
        return [
            {"column_name": c["column_name"], "column_type": c["column_type"]}
            for c in all_cols
            if c.get("model_name", "").lower() == needle
        ]

    # --- Write (not supported) ---

    async def execute(self, sql: str, params: list[Any] | None = None) -> int:
        raise NotImplementedError("dbt connector is read-only")

    async def execute_many(self, sql: str, params_list: list[list[Any]]) -> None:
        raise NotImplementedError("dbt connector is read-only")

    async def write(
        self,
        data: list[dict],
        destination: str,
        config: dict | None = None,
    ) -> None:
        raise NotImplementedError("dbt connector is read-only")

    # --- Transactions (no-ops for read-only connector) ---

    async def begin_transaction(self) -> None:
        pass

    async def commit_transaction(self) -> None:
        pass

    async def rollback_transaction(self) -> None:
        pass

    # --- Context manager ---

    async def __aenter__(self) -> "DbtReadonlyPulse":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def _is_sql(text: str) -> bool:
    """Return True if text starts with a SQL keyword (case-insensitive)."""
    _SQL_PREFIXES = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")
    upper = text.upper()
    return any(upper.startswith(prefix) for prefix in _SQL_PREFIXES)
