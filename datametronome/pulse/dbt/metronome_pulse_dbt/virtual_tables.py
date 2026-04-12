"""In-memory virtual table engine for dbt artifact data."""
from __future__ import annotations
from typing import Any

# SQL keyword prefixes we detect to give a helpful error instead of a silent miss.
_SQL_PREFIXES = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")


class VirtualTableEngine:
    """Stores parsed dbt artifact rows in named tables and supports filtering queries.

    Query interface accepts either a string (table name → all rows) or a dict:

        {
            "table": "models",
            "where": {"materialization": "table", "tags": "finance"},
            "columns": ["name", "schema"],
            "limit": 10,
            "order_by": "name",        # prefix with "-" for descending
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

    def get_table_info(self, table_name: str) -> list[dict[str, str]]:
        """Return column names and inferred types for a table.

        Types are inferred from the first row only. Returns an empty list for
        unknown table names or tables with no rows.
        """
        rows = self._tables.get(table_name, [])
        if not rows:
            return []
        return [
            {"column_name": col, "column_type": _infer_type(val)}
            for col, val in rows[0].items()
        ]

    def query(self, query_config: str | dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a query against virtual tables.

        Args:
            query_config: Either a table name string or a query dict.

        Returns:
            List of matching row dicts.

        Raises:
            ValueError: If the table is not found, or a raw SQL string is passed.
        """
        if isinstance(query_config, str):
            return self._query_by_name(query_config.strip())

        return self._query_by_dict(query_config)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _query_by_name(self, table_name: str) -> list[dict[str, Any]]:
        """Return all rows for a table name string, rejecting SQL strings."""
        upper = table_name.upper()
        if any(upper.startswith(prefix) for prefix in _SQL_PREFIXES):
            raise ValueError(
                f"SQL queries are not supported by the dbt connector. "
                f"Use table name strings or query dicts instead. "
                f"Available tables: {', '.join(self.list_tables())}"
            )
        if table_name not in self._tables:
            raise ValueError(
                f"Virtual table '{table_name}' not found. "
                f"Available tables: {', '.join(self.list_tables())}"
            )
        # Return a shallow copy so callers can't mutate internal state.
        return list(self._tables[table_name])

    def _query_by_dict(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Apply where / order_by / columns / limit from a query dict."""
        table_name = config.get("table", "")
        if table_name not in self._tables:
            raise ValueError(
                f"Virtual table '{table_name}' not found. "
                f"Available tables: {', '.join(self.list_tables())}"
            )

        rows: list[dict[str, Any]] = self._tables[table_name]

        where = config.get("where")
        if where:
            rows = [r for r in rows if _matches(r, where)]

        order_by = config.get("order_by")
        if order_by:
            rows = _sort_rows(rows, order_by)

        columns = config.get("columns")
        if columns:
            rows = [{k: r.get(k) for k in columns} for r in rows]

        limit = config.get("limit")
        if limit is not None:
            rows = rows[:limit]

        return rows


# ------------------------------------------------------------------
# Module-level helpers (no self needed — easier to test in isolation)
# ------------------------------------------------------------------


def _infer_type(value: Any) -> str:
    """Return a simple type label for a Python value."""
    if isinstance(value, bool):
        # bool is a subclass of int, so this check must come first.
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "text"


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


def _sort_rows(rows: list[dict[str, Any]], order_by: str) -> list[dict[str, Any]]:
    """Sort rows by a column name.  Prefix with '-' for descending order.

    None values are sorted last regardless of direction so that missing data
    never bubbles to the top.
    """
    desc = order_by.startswith("-")
    col = order_by[1:] if desc else order_by
    return sorted(rows, key=lambda r: (r.get(col) is None, r.get(col, "")), reverse=desc)
