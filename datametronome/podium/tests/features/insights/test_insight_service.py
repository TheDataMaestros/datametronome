"""Tests for intelligence pipeline service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datametronome_podium.features.insights.service import InsightPipelineService


@pytest.fixture
def service():
    mock_executor = MagicMock()
    return InsightPipelineService(executor=mock_executor)


def test_service_instantiation(service):
    assert service is not None
    assert service.repo is not None


@pytest.mark.asyncio
async def test_classify_domain_uses_archetype_matching(service):
    """Stage 2: Classification should use deterministic matching + LLM."""
    tables = ["orders", "products", "customers", "payments"]
    schema = {"orders": {"columns": ["id", "total"]}}
    samples = {}

    with patch(
        "datametronome_podium.features.insights.service.match_archetypes"
    ) as mock_match:
        mock_match.return_value = [("e-commerce", 0.85), ("crm", 0.2)]
        with patch.object(service, "_llm_classify") as mock_llm:
            mock_llm.return_value = {
                "domain_type": "e-commerce",
                "confidence": 0.9,
                "business_context": "Online retail",
                "entity_roles": {"fact": ["orders"]},
                "matched_archetype": "e-commerce",
            }
            result = await service.classify_domain(tables, schema, samples)
            assert result["domain_type"] == "e-commerce"
            mock_match.assert_called_once_with(tables)


@pytest.mark.asyncio
async def test_classify_domain_falls_back_to_generic():
    """When no archetype matches, should fall back to generic."""
    mock_executor = MagicMock()
    svc = InsightPipelineService(executor=mock_executor)
    tables = ["foo", "bar", "baz"]

    with patch(
        "datametronome_podium.features.insights.service.match_archetypes"
    ) as mock_match:
        mock_match.return_value = [("generic", 0.0)]
        with patch.object(svc, "_llm_classify") as mock_llm:
            mock_llm.return_value = {
                "domain_type": "generic",
                "confidence": 0.3,
                "business_context": "Unknown domain",
                "entity_roles": {},
                "matched_archetype": None,
            }
            result = await svc.classify_domain(tables, {}, {})
            assert result["domain_type"] == "generic"


@pytest.mark.asyncio
async def test_classify_domain_fallback_on_llm_failure():
    """When LLM fails, should fall back to deterministic result."""
    mock_executor = MagicMock()
    svc = InsightPipelineService(executor=mock_executor)
    tables = ["orders", "products", "customers"]

    with patch(
        "datametronome_podium.features.insights.service.match_archetypes"
    ) as mock_match:
        mock_match.return_value = [("e-commerce", 0.85)]
        with patch.object(svc, "_llm_classify") as mock_llm:
            mock_llm.side_effect = RuntimeError("LLM unavailable")
            result = await svc.classify_domain(tables, {}, {})
            assert result["domain_type"] == "e-commerce"
            assert result["confidence"] == 0.85


@pytest.mark.asyncio
async def test_capture_baseline_creates_snapshot(service):
    """Stage 3: Should create and persist a BaselineSnapshot."""
    service.repo.create_snapshot = AsyncMock(return_value=1)
    discovery = {
        "tables": ["orders", "products"],
        "samples": {
            "orders": {"row_count": 5000, "analysis": {}},
            "products": {"row_count": 200, "analysis": {}},
        },
    }
    snapshot = await service.capture_baseline("stave-1", discovery, "daily")
    assert snapshot.stave_id == "stave-1"
    assert snapshot.snapshot_type == "daily"
    assert "orders" in snapshot.table_metrics
    service.repo.create_snapshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_results_creates_report(service):
    """Stage 5: Should persist report and suggestions."""
    from datametronome_podium.features.insights.model import BaselineSnapshot

    service.repo.get_profile = AsyncMock(return_value=None)
    service.repo.create_profile = AsyncMock(return_value=1)
    service.repo.create_report = AsyncMock(return_value=1)
    service.repo.create_suggestion = AsyncMock(return_value=1)

    snapshot = BaselineSnapshot(
        id="snap-1",
        stave_id="stave-1",
        tenant_id="default",
        snapshot_type="daily",
        table_metrics={"orders": {"row_count": 5000}},
        column_stats={},
        captured_at="2026-03-15T06:00:00Z",
    )
    classification = {
        "domain_type": "e-commerce",
        "confidence": 0.85,
        "business_context": "Online retail",
        "entity_roles": {"fact": ["orders"]},
    }
    analysis = {
        "health_score": 78,
        "report_type": "daily",
        "dimensions": [],
        "anomalies": [],
        "suggestions": [
            {
                "priority": "high",
                "category": "ops",
                "action": "Check gateway",
                "reasoning": "Revenue loss",
                "based_on": "7-day trend",
            }
        ],
        "summary": "Looking good.",
        "key_findings": ["All clear"],
        "checks_to_create": [],
    }
    report = await service.persist_results(
        "stave-1", snapshot, analysis, classification
    )
    assert report.health_score == 78
    assert report.stave_id == "stave-1"
    service.repo.create_report.assert_awaited_once()
    service.repo.create_suggestion.assert_awaited_once()
    service.repo.create_profile.assert_awaited_once()


@pytest.mark.asyncio
async def test_classify_domain_llm_malformed_output():
    """When LLM returns garbage, should fall back to deterministic match."""
    mock_executor = MagicMock()
    service = InsightPipelineService(executor=mock_executor)

    with patch("datametronome_podium.features.insights.service.match_archetypes") as mock_match:
        mock_match.return_value = [("e-commerce", 0.85)]
        with patch.object(service, "_llm_classify", side_effect=Exception("Pydantic validation failed")):
            result = await service.classify_domain(["orders", "products", "customers"], {}, {})
            # Should fall back to deterministic match
            assert result["domain_type"] == "e-commerce"
            assert "LLM failed" in result["business_context"]


@pytest.mark.asyncio
async def test_classify_domain_llm_down_no_match():
    """When LLM is down AND no archetype matches, should return generic."""
    mock_executor = MagicMock()
    service = InsightPipelineService(executor=mock_executor)

    with patch("datametronome_podium.features.insights.service.match_archetypes") as mock_match:
        mock_match.return_value = [("generic", 0.0)]
        with patch.object(service, "_llm_classify", side_effect=Exception("API timeout")):
            result = await service.classify_domain(["foo", "bar"], {}, {})
            assert result["domain_type"] == "generic"


@pytest.mark.asyncio
async def test_analyze_business_llm_failure_raises():
    """When Stage 4 LLM fails, it should raise so the caller can save the snapshot."""
    mock_executor = MagicMock()
    service = InsightPipelineService(executor=mock_executor)
    service.repo = MagicMock()
    service.repo.list_snapshots = AsyncMock(return_value=[])

    snapshot = MagicMock()
    snapshot.table_metrics = {}

    with patch("datametronome_podium.services.agent_factory.build_model_from_settings"):
        with patch("pydantic_ai.Agent") as mock_agent_cls:
            mock_agent_cls.return_value.run = AsyncMock(side_effect=Exception("LLM down"))
            with pytest.raises(Exception, match="LLM down"):
                await service.analyze_business("stave-1", snapshot, profile=None)


@pytest.mark.asyncio
async def test_collect_schema_and_samples_gets_row_count():
    """Row counts should come from COUNT(*) queries, not sample data."""
    from datametronome_podium.features.insights.service import _collect_schema_and_samples

    mock_connector = AsyncMock()
    mock_connector.get_table_info = AsyncMock(return_value={"columns": ["id", "name"]})
    mock_connector.query = AsyncMock(return_value=[{"cnt": 500}])
    mock_connector.sample_table = AsyncMock(return_value=[{"id": 1, "name": "test"}])

    schema, samples = await _collect_schema_and_samples(mock_connector, ["orders"])
    assert samples["orders"]["row_count"] == 500


@pytest.mark.asyncio
async def test_collect_schema_and_samples_row_count_fallback_on_error():
    """When COUNT(*) query fails, row_count should default to 0."""
    from datametronome_podium.features.insights.service import _collect_schema_and_samples

    mock_connector = AsyncMock()
    mock_connector.get_table_info = AsyncMock(return_value={"columns": ["id"]})
    mock_connector.query = AsyncMock(side_effect=Exception("permission denied"))
    mock_connector.sample_table = AsyncMock(return_value=[{"id": 1}])

    schema, samples = await _collect_schema_and_samples(mock_connector, ["secret_table"])
    assert samples["secret_table"]["row_count"] == 0


# ------------------------------------------------------------------
# Fingerprint computation tests
# ------------------------------------------------------------------


def test_fingerprint_computed_from_discovery_schema():
    """compute_schema_fingerprint returns a 64-char hex SHA-256."""
    from datametronome_podium.services.agents.business_intelligence import (
        compute_schema_fingerprint,
    )

    discovery = {
        "schema": {
            "orders": {"order_id": {}, "customer_id": {}, "order_purchase_timestamp": {}},
            "products": {"product_id": {}, "product_category_name": {}},
        },
        "samples": {},
    }
    fp = compute_schema_fingerprint(discovery["schema"])
    assert isinstance(fp, str)
    assert len(fp) == 64


def test_fingerprint_order_independent():
    """Fingerprint is the same regardless of dict ordering."""
    from datametronome_podium.services.agents.business_intelligence import (
        compute_schema_fingerprint,
    )

    schema_a = {"orders": {"order_id": {}, "status": {}}, "products": {"id": {}}}
    schema_b = {"products": {"id": {}}, "orders": {"status": {}, "order_id": {}}}
    assert compute_schema_fingerprint(schema_a) == compute_schema_fingerprint(schema_b)


# ------------------------------------------------------------------
# BI track wiring tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bi_skips_when_no_profile(service):
    """BI track should return None when profile is None."""
    snapshot = MagicMock()
    result = await service._analyze_business_intelligence(
        "stave-1", snapshot, profile=None
    )
    assert result is None


@pytest.mark.asyncio
async def test_bi_skips_generic_domain(service):
    """BI track should return None for generic domain."""
    from datametronome_podium.features.insights.model import DataProfile

    profile = DataProfile(
        id="dp-1", stave_id="stave-1", tenant_id="default",
        domain_type="generic", domain_confidence=0.5,
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )
    snapshot = MagicMock()
    result = await service._analyze_business_intelligence(
        "stave-1", snapshot, profile=profile
    )
    assert result is None


@pytest.mark.asyncio
async def test_bi_skips_when_no_kpi_definitions(service):
    """BI track should return None when archetype has no kpi_definitions."""
    from datametronome_podium.features.insights.model import DataProfile

    profile = DataProfile(
        id="dp-1", stave_id="stave-1", tenant_id="default",
        domain_type="e-commerce", domain_confidence=0.9,
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )
    snapshot = MagicMock()
    with patch(
        "datametronome_podium.features.insights.service.load_archetype",
        return_value={"name": "e-commerce"},
    ):
        result = await service._analyze_business_intelligence(
            "stave-1", snapshot, profile=profile
        )
    assert result is None


@pytest.mark.asyncio
async def test_persist_results_extracts_schema_interpretation(service):
    """persist_results should pop _schema_interpretation and save to profile."""
    from datametronome_podium.features.insights.model import BaselineSnapshot

    service.repo.get_profile = AsyncMock(return_value=None)
    service.repo.create_report = AsyncMock(return_value=1)
    service.repo.update_profile = AsyncMock(return_value=1)
    service.repo.create_business_report = AsyncMock(return_value=1)

    snapshot = BaselineSnapshot(
        id="snap-1", stave_id="stave-1", tenant_id="default",
        snapshot_type="daily", table_metrics={}, column_stats={},
        captured_at="2026-03-15T06:00:00Z",
    )
    bi_analysis = {
        "business_health_score": 72,
        "executive_summary": "Good",
        "kpis": [], "top_performers": [], "bottom_performers": [],
        "trends": [], "opportunities": [], "risks": [],
        "_schema_interpretation": {
            "table_roles": {"orders": "fact_table"},
            "column_roles": {},
            "key_observations": [],
        },
    }
    await service.persist_results(
        "stave-1", snapshot, analysis=None, bi_analysis=bi_analysis,
    )
    # Schema interpretation should have been popped and saved
    service.repo.update_profile.assert_awaited()
    call_args = service.repo.update_profile.call_args
    assert "schema_interpretation" in call_args[0][1]
    # _schema_interpretation should have been removed from bi_analysis
    assert "_schema_interpretation" not in bi_analysis
