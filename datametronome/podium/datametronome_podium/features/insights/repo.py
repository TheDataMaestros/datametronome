"""Intelligence Store data access."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

from datametronome_podium.core.query import QueryExecutor
from datametronome_podium.features.insights.model import (
    BusinessReport,
    DataProfile,
    BaselineSnapshot,
    InsightReport,
    InsightSuggestion,
    InsightCreatedCheck,
    Notification,
    StaveQueryPlan,
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
    "schema_interpretation",
)
_REPORT_JSON_FIELDS = ("dimensions", "anomalies", "suggestions", "key_findings")
_SNAPSHOT_JSON_FIELDS = ("table_metrics", "column_stats")
_BUSINESS_REPORT_JSON_FIELDS = (
    "kpis", "top_performers", "bottom_performers", "trends", "opportunities", "risks"
)
_PLAN_JSON_FIELDS = ("kpi_queries", "performer_queries")


def _deserialize_plan(row: dict) -> StaveQueryPlan:
    """Deserialize a stave_query_plans row into a StaveQueryPlan model."""
    return StaveQueryPlan(
        id=row["id"],
        stave_id=row["stave_id"],
        tenant_id=row.get("tenant_id", "default"),
        schema_fingerprint=row["schema_fingerprint"],
        kpi_queries=_parse_json(row.get("kpi_queries", "{}")),
        performer_queries=_parse_json(row.get("performer_queries", "{}")),
        generated_by_model=row.get("generated_by_model", ""),
        generated_at=row["generated_at"],
        invalidated_at=row.get("invalidated_at"),
    )


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
        data = suggestion.model_dump()
        if data.get("check_spec") is not None and not isinstance(data["check_spec"], str):
            data["check_spec"] = _json_field(data["check_spec"])
        return await self.db.insert("insight_suggestions", data)

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
        if not rows:
            return None
        row = dict(rows[0])
        cs = row.get("check_spec")
        row["check_spec"] = _parse_json(cs) if cs and cs != "null" else None
        return InsightSuggestion(**row)

    async def update_suggestion_status(
        self, suggestion_id: str, status: str, dismiss_reason: str | None = None
    ) -> int:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        data: dict = {"status": status, "resolved_at": now}
        if dismiss_reason is not None:
            data["dismiss_reason"] = dismiss_reason
        return await self.db.update(
            "insight_suggestions", data, where={"id": suggestion_id}
        )

    async def mark_suggestion_read(self, suggestion_id: str, username: str) -> int:
        """Record when a user first viewed this suggestion."""
        rows = await self.db.select(
            "insight_suggestions", where={"id": suggestion_id}
        )
        if not rows or rows[0].get("read_at"):
            return 0  # already read or not found
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return await self.db.update(
            "insight_suggestions",
            {"read_at": now, "read_by": username},
            where={"id": suggestion_id},
        )

    async def assign_suggestion(
        self, suggestion_id: str, assigned_to: str
    ) -> int:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return await self.db.update(
            "insight_suggestions",
            {"assigned_to": assigned_to, "assigned_at": now},
            where={"id": suggestion_id},
        )

    # --- Notification ---

    async def create_notification(self, notification: Notification) -> int:
        return await self.db.insert("notifications", notification.model_dump())

    async def list_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50
    ) -> list[Notification]:
        if unread_only:
            rows = await self.db.query(
                "SELECT * FROM notifications WHERE user_id = ? AND read_at IS NULL "
                "ORDER BY created_at DESC LIMIT ?",
                [user_id, limit],
            )
        else:
            rows = await self.db.query(
                "SELECT * FROM notifications WHERE user_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                [user_id, limit],
            )
        return [Notification(**dict(row)) for row in rows]

    async def mark_notification_read(self, notification_id: str) -> int:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return await self.db.update(
            "notifications", {"read_at": now}, where={"id": notification_id}
        )

    async def get_user_by_username(self, username: str) -> dict | None:
        rows = await self.db.select("users", where={"username": username})
        return dict(rows[0]) if rows else None

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

    # --- BusinessReport ---

    async def create_business_report(self, report: BusinessReport) -> int:
        data = report.model_dump()
        for field in _BUSINESS_REPORT_JSON_FIELDS:
            data[field] = _json_field(data[field])
        return await self.db.insert("business_reports", data)

    async def get_latest_business_report(
        self, stave_id: str
    ) -> BusinessReport | None:
        rows = await self.db.query(
            "SELECT * FROM business_reports "
            "WHERE stave_id = ? ORDER BY generated_at DESC LIMIT 1",
            [stave_id],
        )
        if not rows:
            return None
        return self._row_to_business_report(rows[0])

    async def list_business_reports(
        self, stave_id: str, limit: int = 20
    ) -> list[BusinessReport]:
        rows = await self.db.query(
            "SELECT * FROM business_reports "
            "WHERE stave_id = ? ORDER BY generated_at DESC LIMIT ?",
            [stave_id, limit],
        )
        return [self._row_to_business_report(row) for row in rows]

    def _row_to_business_report(self, row: dict) -> BusinessReport:
        r = dict(row)
        for field in _BUSINESS_REPORT_JSON_FIELDS:
            r[field] = _parse_json(r.get(field))
        return BusinessReport(**r)

    # --- StaveQueryPlan ---

    async def get_valid_plan(self, stave_id: str) -> StaveQueryPlan | None:
        """Return the currently valid (non-invalidated) query plan for a stave."""
        rows = await self.db.query(
            "SELECT * FROM stave_query_plans "
            "WHERE stave_id = ? AND invalidated_at IS NULL LIMIT 1",
            [stave_id],
        )
        if not rows:
            return None
        return _deserialize_plan(rows[0])

    async def create_plan(self, plan: StaveQueryPlan) -> int:
        data = plan.model_dump()
        for field in _PLAN_JSON_FIELDS:
            data[field] = _json_field(data[field])
        return await self.db.insert("stave_query_plans", data)

    async def invalidate_plan(self, stave_id: str, now: str) -> int:
        """Set invalidated_at on the current valid plan for a stave."""
        return await self.db.execute(
            "UPDATE stave_query_plans SET invalidated_at = ? "
            "WHERE stave_id = ? AND invalidated_at IS NULL",
            [now, stave_id],
        )

    async def prune_old_plans(self, cutoff: str) -> int:
        """Delete invalidated plan rows older than the cutoff timestamp."""
        return await self.db.execute(
            "DELETE FROM stave_query_plans "
            "WHERE invalidated_at IS NOT NULL AND invalidated_at < ?",
            [cutoff],
        )
