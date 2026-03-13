"""SQL dialect translation between SQLite and PostgreSQL.

Translates placeholders, boolean literals, and DDL type names so that
all application code can write SQL with `?` placeholders regardless
of the active database backend.
"""


class QueryAdapter:
    """Translates SQL between SQLite and PostgreSQL dialects."""

    def __init__(self, dialect: str) -> None:
        if dialect not in ("sqlite", "postgresql"):
            raise ValueError(f"Unsupported dialect: {dialect}")
        self.dialect = dialect

    def adapt(self, sql: str, params: list | None = None) -> tuple[str, list]:
        """Adapt SQL and params for the active dialect.

        Args:
            sql: SQL string with `?` placeholders
            params: Parameter list (may be empty or None)

        Returns:
            (adapted_sql, adapted_params)
        """
        params = list(params) if params else []
        if self.dialect == "postgresql":
            sql = self._rewrite_placeholders(sql)
        elif self.dialect == "sqlite":
            # SQLite needs bools as 1/0
            params = [int(p) if isinstance(p, bool) else p for p in params]
        return sql, params

    def adapt_ddl(self, sql: str) -> str:
        """Adapt DDL statements for the active dialect.

        PostgreSQL DDL is the canonical format. This method translates
        for SQLite when needed.
        """
        if self.dialect == "sqlite":
            sql = sql.replace("JSONB", "TEXT")
            sql = sql.replace("DOUBLE PRECISION", "REAL")
        return sql

    def _rewrite_placeholders(self, sql: str) -> str:
        """Replace ? placeholders with $1, $2, ... for PostgreSQL.

        Skips ? characters inside string literals (single quotes).
        Handles PostgreSQL-style escaped quotes ('') correctly.
        """
        result = []
        param_index = 0
        in_string = False

        i = 0
        while i < len(sql):
            char = sql[i]
            if char == "'":
                # Check for doubled quote ('') — escaped single quote
                if in_string and i + 1 < len(sql) and sql[i + 1] == "'":
                    result.append("''")
                    i += 2
                    continue
                in_string = not in_string
                result.append(char)
            elif char == "?" and not in_string:
                param_index += 1
                result.append(f"${param_index}")
            else:
                result.append(char)
            i += 1

        return "".join(result)
