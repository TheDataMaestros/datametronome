"""Tests for enriched intelligence block in dashboard metrics."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_db(query_results: dict):
    """Return a mock executor that returns different results per SQL keyword.
    Uses plain substring matching — keyword must be a substring of the SQL (lowercased).
    Accepts QueryExecutor.query(sql, params) signature.
    """
    async def mock_query(sql, params=None):
        sql_lower = sql.lower()
        for keyword, result in query_results.items():
            if keyword in sql_lower:
                return result
        return []

    mock_db = MagicMock()
    mock_db.query = mock_query
    return mock_db


@pytest.mark.asyncio
async def test_top_suggestions_include_stave_id_and_name():
    """top_suggestions items must have stave_id and stave_name fields."""
    from datametronome_podium.features.metrics.router import _fetch_intelligence_metrics

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
    from datametronome_podium.features.metrics.router import _fetch_intelligence_metrics

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


@pytest.mark.asyncio
async def test_intelligence_includes_stave_health_scores_map():
    """intelligence block must include stave_health_scores: {stave_id: score}."""
    from datametronome_podium.features.metrics.router import _fetch_intelligence_metrics

    db = _make_mock_db({
        "avg(health_score)": [{"avg_health": 80.0, "report_count": 3}],
        "order by created_at desc limit 1": [{"created_at": "2026-03-15T10:00:00", "snapshot_id": None}],
        "count(*) as count from data_profiles": [{"count": 2}],
        "count(*) as count from insight_suggestions": [{"count": 0}],
        "s.status = 'pending'": [],
        "from insight_reports r": [],
        # Plain substring — _make_mock_db does `keyword in sql` (lowercased)
        "group by ir.stave_id": [
            {"stave_id": "stave-1", "health_score": 92},
            {"stave_id": "stave-2", "health_score": 54},
        ],
    })

    result = await _fetch_intelligence_metrics(db)

    assert "stave_health_scores" in result
    scores = result["stave_health_scores"]
    assert scores["stave-1"] == 92
    assert scores["stave-2"] == 54


@pytest.mark.asyncio
async def test_top_anomalies_include_stave_id_and_name():
    """top_anomalies items must have stave_id and stave_name fields."""
    from datametronome_podium.features.metrics.router import _fetch_intelligence_metrics

    anomaly = {"severity": "critical", "category": "volume", "description": "Spike", "table": "orders", "evidence": "3x baseline"}
    report_row = {
        "anomalies": json.dumps([anomaly]),
        "stave_id": "stave-abc",
        "stave_name": "olist_prod",
        "report_at": "2026-03-15T10:00:00",
        "snapshot_at": "2026-03-15T09:00:00",
    }

    db = _make_mock_db({
        "avg(health_score)": [{"avg_health": 60.0, "report_count": 1}],
        "order by created_at desc limit 1": [{"created_at": "2026-03-15T10:00:00", "snapshot_id": None}],
        "count(*) as count from data_profiles": [{"count": 1}],
        "count(*) as count from insight_suggestions": [{"count": 0}],
        "s.status = 'pending'": [],
        "from insight_reports r": [report_row],
        "group by ir.stave_id": [],
    })

    result = await _fetch_intelligence_metrics(db)

    assert len(result["top_anomalies"]) == 1
    ano = result["top_anomalies"][0]
    assert ano["stave_id"] == "stave-abc"
    assert ano["stave_name"] == "olist_prod"


@pytest.mark.asyncio
async def test_top_anomalies_stave_name_falls_back_to_stave_id():
    """top_anomalies stave_name falls back to stave_id when name is None."""
    from datametronome_podium.features.metrics.router import _fetch_intelligence_metrics

    anomaly = {"severity": "high", "category": "schema", "description": "Missing col", "table": "users", "evidence": "null"}
    report_row = {
        "anomalies": json.dumps([anomaly]),
        "stave_id": "stave-xyz",
        "stave_name": None,
        "report_at": "2026-03-15T10:00:00",
        "snapshot_at": None,
    }

    db = _make_mock_db({
        "avg(health_score)": [{"avg_health": 40.0, "report_count": 1}],
        "order by created_at desc limit 1": [{"created_at": "2026-03-15T10:00:00", "snapshot_id": None}],
        "count(*) as count from data_profiles": [{"count": 1}],
        "count(*) as count from insight_suggestions": [{"count": 0}],
        "s.status = 'pending'": [],
        "from insight_reports r": [report_row],
        "group by ir.stave_id": [],
    })

    result = await _fetch_intelligence_metrics(db)

    ano = result["top_anomalies"][0]
    assert ano["stave_id"] == "stave-xyz"
    assert ano["stave_name"] == "stave-xyz"  # fallback to stave_id
