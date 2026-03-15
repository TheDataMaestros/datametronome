"""Dialect-aware DDL operations for Alembic migrations."""


def adapt_ddl(sql: str, dialect: str) -> str:
    """Adapt DDL for dialect. Same logic as QueryAdapter.adapt_ddl()."""
    if dialect == "sqlite":
        sql = sql.replace("JSONB", "TEXT")
        sql = sql.replace("DOUBLE PRECISION", "REAL")
    return sql


class DialectAwareOps:
    """Wraps Alembic's op.execute to apply dialect adaptation."""

    @staticmethod
    def execute(sql):
        """Execute SQL with dialect adaptation for SQLite."""
        from alembic import op as _op
        dialect_name = _op.get_bind().dialect.name
        adapted = adapt_ddl(sql, dialect_name)
        _op.execute(adapted)
