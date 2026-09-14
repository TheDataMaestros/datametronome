"""In-memory virtual table engine for dbt artifact data."""
from __future__ import annotations
from typing import Any


class VirtualTableEngine:
    """Stores parsed dbt artifact rows in named tables and supports filtering queries.

    Query interface accepts either a string (table name → all rows) or a dict:

        {
            "table": "models",
            "where": {"materialization": "table", "tags": "finance"},
            "limit": 10,
        }

    Where clause supports:
    - Simple equality: {"materialization": "table"} matches rows where
      materialization == "table"
    - List containment: {"tags": "finance"} matches rows where "finance" is
      in the tags list
    """

    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}

    def register_table(self, name: str, rows: list[dict[str, Any]]) -> None:
        """Register (or overwrite) a virtual table with its rows."""
        self._tables[name] = rows

    def list_tables(self) -> list[str]:
        """Return sorted list of registered table names."""
        return sorted(self._tables.keys())

    def query(self, query_config: str | dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a query against virtual tables.

        Args:
            query_config: Either a table name string or a query dict.

        Returns:
            List of matching row dicts.

        Raises:
            ValueError: If the table is not found.
        """
        if isinstance(query_config, str):
            return self._query_by_name(query_config.strip())

        return self._query_by_dict(query_config)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _unknown_table(self, table_name: str) -> ValueError:
        return ValueError(
            f"Virtual table '{table_name}' not found. "
            f"Available tables: {', '.join(self.list_tables())}"
        )

    def _query_by_name(self, table_name: str) -> list[dict[str, Any]]:
        """Return all rows for a table name string."""
        if table_name not in self._tables:
            raise self._unknown_table(table_name)
        # Return a shallow copy so callers can't mutate internal state.
        return list(self._tables[table_name])

    def _query_by_dict(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Apply where and limit from a query dict."""
        table_name = config.get("table", "")
        if table_name not in self._tables:
            raise self._unknown_table(table_name)

        rows: list[dict[str, Any]] = self._tables[table_name]

        where = config.get("where")
        if where:
            rows = [r for r in rows if _matches(r, where)]

        limit = config.get("limit")
        if limit is not None:
            rows = rows[:limit]

        return rows


def _matches(row: dict[str, Any], where: dict[str, Any]) -> bool:
    """Return True if the row satisfies all where conditions.

    List columns use containment semantics: {"tags": "finance"} is True when
    "finance" appears anywhere in the tags list.  All other columns use strict
    equality.
    """
    for key, expected in where.items():
        actual = row.get(key)
        if isinstance(actual, list):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True
