"""Analytics data access -- read-only aggregate queries."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from datametronome_podium.core.query import QueryExecutor


class AnalyticsRepo:
    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    async def get_check_summary(self) -> dict:
        rows = await self.db.query(
            "SELECT "
            "COUNT(*) as total, "
            "SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) as passed, "
            "SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) as failed, "
            "SUM(CASE WHEN status = 'warn' THEN 1 ELSE 0 END) as warning "
            "FROM checks"
        )
        if rows:
            return dict(rows[0])
        return {"total": 0, "passed": 0, "failed": 0, "warning": 0}

    async def get_active_sources_count(self) -> int:
        rows = await self.db.query(
            "SELECT COUNT(*) as count FROM staves WHERE is_active = ?", [True]
        )
        return rows[0]["count"] if rows else 0

    async def get_anomaly_count(self, hours: int = 24) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = await self.db.query(
            "SELECT COUNT(*) as count FROM checks "
            "WHERE anomalies_count > 0 AND timestamp >= ?",
            [cutoff]
        )
        return rows[0]["count"] if rows else 0

    async def get_recent_checks(self, limit: int = 20) -> list[dict]:
        rows = await self.db.query(
            "SELECT c.id, c.check_type, c.status, c.timestamp, c.execution_time, "
            "s.name as stave_name, cl.name as clef_name "
            "FROM checks c "
            "JOIN staves s ON c.stave_id = s.id "
            "JOIN clefs cl ON c.clef_id = cl.id "
            "ORDER BY c.timestamp DESC LIMIT ?",
            [limit]
        )
        return [dict(row) for row in rows]
