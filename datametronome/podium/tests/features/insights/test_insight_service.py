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
