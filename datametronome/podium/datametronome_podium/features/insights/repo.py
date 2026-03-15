"""Intelligence Store data access."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.insights.model import (
    DataProfile,
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
)


def _json_field(value: dict | list | None) -> str:
    """Serialize a dict/list to JSON string for storage."""
    if value is None:
        return "null"
    return json.dumps(value)


def _parse_json(value: str | dict | list | None) -> dict | list:
    """Parse a JSON string back to dict/list."""
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


_PROFILE_JSON_FIELDS = (
    "domain_context", "schema_map", "entity_roles", "learned_patterns",
)
_REPORT_JSON_FIELDS = ("dimensions", "anomalies", "suggestions", "key_findings")
_SNAPSHOT_JSON_FIELDS = ("table_metrics", "column_stats")


class InsightsRepo:
    """CRUD for all Intelligence Store tables."""

    def __init__(self, executor: QueryExecutor) -> None:
        self.db = executor

    # --- DataProfile ---

    async def create_profile(self, profile: DataProfile) -> int:
        data = profile.model_dump()
        for field in (*_PROFILE_JSON_FIELDS, "previous_classification"):
            data[field] = _json_field(data[field])
        return await self.db.insert("data_profiles", data)

    async def get_profile(self, stave_id: str) -> DataProfile | None:
        rows = await self.db.select("data_profiles", where={"stave_id": stave_id})
        if not rows:
            return None
        row = dict(rows[0])
        for field in _PROFILE_JSON_FIELDS:
            row[field] = _parse_json(row.get(field))
        prev = row.get("previous_classification")
        row["previous_classification"] = (
            _parse_json(prev) if prev and prev != "null" else None
        )
        return DataProfile(**row)

    async def update_profile(self, stave_id: str, data: dict) -> int:
        for field in (*_PROFILE_JSON_FIELDS, "previous_classification"):
            if field in data and not isinstance(data[field], str):
                data[field] = _json_field(data[field])
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        data["updated_at"] = now
        return await self.db.update(
            "data_profiles", data, where={"stave_id": stave_id}
        )

    # --- BaselineSnapshot ---

    async def create_snapshot(self, snapshot: BaselineSnapshot) -> int:
        data = snapshot.model_dump()
        for field in _SNAPSHOT_JSON_FIELDS:
            data[field] = _json_field(data[field])
        return await self.db.insert("baseline_snapshots", data)

    async def list_snapshots(
        self, stave_id: str, days: int = 7, limit: int = 100
    ) -> list[BaselineSnapshot]:
        cutoff = (
            (datetime.now(timezone.utc) - timedelta(days=days))
            .isoformat()
            .replace("+00:00", "Z")
        )
        rows = await self.db.query(
            "SELECT * FROM baseline_snapshots "
            "WHERE stave_id = ? AND captured_at >= ? "
            "ORDER BY captured_at DESC LIMIT ?",
            [stave_id, cutoff, limit],
        )
        return [self._row_to_snapshot(row) for row in rows]

    async def get_snapshot(self, snapshot_id: str) -> BaselineSnapshot | None:
        rows = await self.db.select(
            "baseline_snapshots", where={"id": snapshot_id}
        )
        if not rows:
            return None
        return self._row_to_snapshot(rows[0])

    def _row_to_snapshot(self, row: dict) -> BaselineSnapshot:
        r = dict(row)
        for field in _SNAPSHOT_JSON_FIELDS:
            r[field] = _parse_json(r.get(field))
        return BaselineSnapshot(**r)

    # --- InsightReport ---

    async def create_report(self, report: InsightReport) -> int:
        data = report.model_dump()
        for field in _REPORT_JSON_FIELDS:
            data[field] = _json_field(data[field])
        return await self.db.insert("insight_reports", data)

    async def get_latest_report(self, stave_id: str) -> InsightReport | None:
        rows = await self.db.query(
            "SELECT * FROM insight_reports "
            "WHERE stave_id = ? ORDER BY created_at DESC LIMIT 1",
            [stave_id],
        )
        if not rows:
            return None
        return self._row_to_report(rows[0])

    async def list_reports(
        self, stave_id: str, limit: int = 20, offset: int = 0
    ) -> list[InsightReport]:
        rows = await self.db.query(
            "SELECT * FROM insight_reports "
            "WHERE stave_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [stave_id, limit, offset],
        )
        return [self._row_to_report(row) for row in rows]

    def _row_to_report(self, row: dict) -> InsightReport:
        r = dict(row)
        for field in _REPORT_JSON_FIELDS:
            r[field] = _parse_json(r.get(field))
        return InsightReport(**r)

    # --- InsightSuggestion ---

    async def create_suggestion(self, suggestion: InsightSuggestion) -> int:
        return await self.db.insert(
            "insight_suggestions", suggestion.model_dump()
        )

    async def list_suggestions(
        self, stave_id: str, status: str | None = None, limit: int = 50
    ) -> list[InsightSuggestion]:
        if status:
            rows = await self.db.query(
                "SELECT * FROM insight_suggestions "
                "WHERE stave_id = ? AND status = ? "
                "ORDER BY created_at DESC LIMIT ?",
                [stave_id, status, limit],
            )
        else:
            rows = await self.db.query(
                "SELECT * FROM insight_suggestions "
                "WHERE stave_id = ? ORDER BY created_at DESC LIMIT ?",
                [stave_id, limit],
            )
        return [InsightSuggestion(**dict(row)) for row in rows]

    async def get_suggestion(
        self, suggestion_id: str
    ) -> InsightSuggestion | None:
        rows = await self.db.select(
            "insight_suggestions", where={"id": suggestion_id}
        )
        return InsightSuggestion(**dict(rows[0])) if rows else None

    async def update_suggestion_status(
        self, suggestion_id: str, status: str
    ) -> int:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return await self.db.update(
            "insight_suggestions",
            {"status": status, "resolved_at": now},
            where={"id": suggestion_id},
        )

    # --- InsightCreatedCheck ---

    async def create_check_link(self, link: InsightCreatedCheck) -> int:
        return await self.db.insert(
            "insight_created_checks", link.model_dump()
        )

    async def list_check_links(
        self, report_id: str
    ) -> list[InsightCreatedCheck]:
        rows = await self.db.select(
            "insight_created_checks", where={"report_id": report_id}
        )
        return [InsightCreatedCheck(**dict(row)) for row in rows]
