"""Tests for enriched intelligence block in dashboard metrics."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_db(query_results: dict):
    """Return a mock DB that returns different results per SQL keyword.
    Uses plain substring matching — keyword must be a substring of the SQL (lowercased).
    """
    async def mock_query(query_dict):
        sql = query_dict.get("sql", "").lower()
        for keyword, result in query_results.items():
            if keyword in sql:
                return result
        return []

    mock_db = MagicMock()
    mock_db.query = mock_query
    return mock_db


@pytest.mark.asyncio
async def test_top_suggestions_include_stave_id_and_name():
    """top_suggestions items must have stave_id and stave_name fields."""
    from datametronome_podium.api.v1.endpoints.metrics import _fetch_intelligence_metrics

    suggestion_row = {
        "priority": "high",
        "category": "quality",
        "action": "Add NOT NULL constraint",
        "reasoning": "Null rate is 15%",
        "stave_id": "stave-abc",
        "stave_name": "analytics_db",
    }

    db = _make_mock_db({
        "avg(health_score)": [{"avg_health": 75.0, "report_count": 2}],
        "order by created_at desc limit 1": [{"created_at": "2026-03-15T10:00:00", "snapshot_id": None}],
        "count(*) as count from data_profiles": [{"count": 1}],
        "count(*) as count from insight_suggestions": [{"count": 1}],
        "s.status = 'pending'": [suggestion_row],
        "from insight_reports r": [],
        "table_metrics from baseline_snapshots": [],
    })

    result = await _fetch_intelligence_metrics(db)

    assert len(result["top_suggestions"]) == 1
    sug = result["top_suggestions"][0]
    assert sug["stave_id"] == "stave-abc"
    assert sug["stave_name"] == "analytics_db"


@pytest.mark.asyncio
async def test_top_suggestions_stave_name_falls_back_to_stave_id():
    """If stave_name is None/missing, fall back to stave_id."""
    from datametronome_podium.api.v1.endpoints.metrics import _fetch_intelligence_metrics

    suggestion_row = {
        "priority": "medium",
        "category": "schema",
        "action": "Add index",
        "reasoning": "Slow queries",
        "stave_id": "stave-xyz",
        "stave_name": None,
    }

    db = _make_mock_db({
        "avg(health_score)": [{"avg_health": 80.0, "report_count": 1}],
        "order by created_at desc limit 1": [{"created_at": "2026-03-15T10:00:00", "snapshot_id": None}],
        "count(*) as count from data_profiles": [{"count": 1}],
        "count(*) as count from insight_suggestions": [{"count": 1}],
        "s.status = 'pending'": [suggestion_row],
        "from insight_reports r": [],
    })

    result = await _fetch_intelligence_metrics(db)

    sug = result["top_suggestions"][0]
    assert sug["stave_id"] == "stave-xyz"
    assert sug["stave_name"] == "stave-xyz"  # fallback
