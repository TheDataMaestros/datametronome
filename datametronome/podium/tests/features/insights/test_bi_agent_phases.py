"""Unit tests for BusinessIntelligenceAgent phase functions."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datametronome_podium.services.agents.bi_models import (
    SchemaInterpretation,
    GeneratedQueryPlan,
)


# ── run_raw_query enforcement ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_raw_query_appends_limit():
    """run_raw_query appends LIMIT 1000 when not present."""
    from datametronome_podium.services.agents.business_intelligence import _enforce_limit

    sql = "SELECT * FROM orders"
    result = _enforce_limit(sql)
    assert "LIMIT 1000" in result.upper()


@pytest.mark.asyncio
async def test_run_raw_query_preserves_existing_limit():
    """run_raw_query does not add a second LIMIT when one already exists."""
    from datametronome_podium.services.agents.business_intelligence import _enforce_limit

    sql = "SELECT * FROM orders LIMIT 50"
    result = _enforce_limit(sql)
    assert result.count("LIMIT") == 1 or result.count("limit") == 1


# ── schema fingerprint ────────────────────────────────────────────────────────

def test_compute_schema_fingerprint_is_stable():
    from datametronome_podium.services.agents.business_intelligence import compute_schema_fingerprint

    schema = {
        "orders": {"order_id": {}, "customer_id": {}, "order_status": {}},
        "products": {"product_id": {}, "price": {}},
    }
    fp1 = compute_schema_fingerprint(schema)
    fp2 = compute_schema_fingerprint(schema)
    assert fp1 == fp2
    assert len(fp1) == 64  # sha256 hex


def test_compute_schema_fingerprint_changes_on_column_add():
    from datametronome_podium.services.agents.business_intelligence import compute_schema_fingerprint

    schema_before = {"orders": {"order_id": {}, "status": {}}}
    schema_after = {"orders": {"order_id": {}, "status": {}, "new_col": {}}}
    assert compute_schema_fingerprint(schema_before) != compute_schema_fingerprint(schema_after)


# ── abort threshold ───────────────────────────────────────────────────────────

def test_abort_threshold_triggers_when_majority_fail():
    from datametronome_podium.services.agents.business_intelligence import _should_abort

    # 3 total queries, 2 failed = 67% failed -> abort
    assert _should_abort(total=3, succeeded=1) is True


def test_abort_threshold_does_not_trigger_when_majority_succeed():
    from datametronome_podium.services.agents.business_intelligence import _should_abort

    # 4 total queries, 3 succeeded = 75% succeed -> do not abort
    assert _should_abort(total=4, succeeded=3) is False


def test_abort_threshold_exactly_half_does_not_abort():
    from datametronome_podium.services.agents.business_intelligence import _should_abort

    # 4 total, 2 succeeded = exactly half -> do not abort (spec: "fewer than half")
    assert _should_abort(total=4, succeeded=2) is False


@pytest.mark.asyncio
async def test_run_phase2_returns_none_on_abort_threshold():
    """run_phase2_generate_and_validate returns None when fewer than half queries succeed."""
    from datametronome_podium.services.agents.business_intelligence import (
        run_phase2_generate_and_validate,
    )

    schema_interp = SchemaInterpretation(
        table_roles={"orders": "fact_table"},
        column_roles={"orders.created_at": "transaction_time"},
        key_observations=[],
    )
    archetype = {
        "kpi_definitions": [
            {"name": "kpi_a", "description": "A"},
            {"name": "kpi_b", "description": "B"},
            {"name": "kpi_c", "description": "C"},
            {"name": "kpi_d", "description": "D"},
        ],
        "performer_dimensions": [{"entity": "product", "description": "Products"}],
    }
    # Agent returns a plan with only 1 of 6 expected queries -> abort
    sparse_plan = GeneratedQueryPlan(
        kpi_queries={"kpi_a": "SELECT 1 as value"},
        performer_queries={},
        skipped=[
            {"name": "kpi_b", "reason": "failed"},
            {"name": "kpi_c", "reason": "failed"},
            {"name": "kpi_d", "reason": "failed"},
        ],
    )
    mock_model = MagicMock()
    mock_connector = AsyncMock()

    with patch(
        "datametronome_podium.services.agents.business_intelligence.build_phase2_agent"
    ) as mock_build:
        mock_agent = AsyncMock()
        mock_result = AsyncMock()
        mock_result.output = sparse_plan
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_build.return_value = mock_agent

        result = await run_phase2_generate_and_validate(
            schema_interp, archetype, mock_connector, '"public".', mock_model
        )
    assert result is None  # abort threshold hit


@pytest.mark.asyncio
async def test_execute_sql_propagates_db_errors():
    """_execute_sql raises on connector errors so run_raw_query can signal failure to the agent."""
    from datametronome_podium.services.agents.business_intelligence import _execute_sql

    connector = AsyncMock()
    connector.query = AsyncMock(side_effect=RuntimeError("syntax error"))
    with pytest.raises(RuntimeError, match="syntax error"):
        await _execute_sql(connector, "SELECT bad sql")
