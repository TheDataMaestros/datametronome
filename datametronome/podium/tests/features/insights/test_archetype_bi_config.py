"""Verify that BI-enabled archetypes have kpi_definitions and no hardcoded SQL."""
import pytest
from datametronome_podium.archetypes import load_archetype


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_kpi_definitions(domain):
    arch = load_archetype(domain)
    assert arch is not None, f"Archetype {domain} not found"
    assert "kpi_definitions" in arch, f"{domain} missing kpi_definitions"
    assert len(arch["kpi_definitions"]) > 0, f"{domain} kpi_definitions is empty"
    for kpi in arch["kpi_definitions"]:
        assert "name" in kpi, f"{domain} kpi_definition missing name"
        assert "description" in kpi, f"{domain} kpi_definition missing description"


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_no_sql(domain):
    arch = load_archetype(domain)
    assert "kpi_queries" not in arch, f"{domain} still has legacy kpi_queries key"  # type: ignore
    for dim in arch.get("performer_dimensions", []):  # type: ignore
        assert "rank_query" not in dim, f"{domain} performer_dimensions still has rank_query SQL"
        assert "drill_query" not in dim, f"{domain} performer_dimensions still has drill_query SQL"
        assert "description" in dim, f"{domain} performer_dimension missing description"


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_metrics_have_no_query_hint(domain):
    arch = load_archetype(domain)
    for metric in arch.get("metrics", []):  # type: ignore
        assert "query_hint" not in metric, (
            f"{domain} metric '{metric.get('name')}' still has legacy query_hint"
        )


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_performer_dimensions_structure(domain):
    """Each performer dimension must have entity + description, no SQL."""
    arch = load_archetype(domain)
    for dim in arch.get("performer_dimensions", []):  # type: ignore
        assert "entity" in dim, f"{domain} performer_dimension missing entity"
        assert "description" in dim, f"{domain} performer_dimension missing description"
        assert "rank_query" not in dim
        assert "drill_query" not in dim


def test_generic_archetype_has_no_sql_keys():
    # generic has no BI config at all — BI track is skipped in service.py
    # when domain_type == "generic" (checked before loading archetype kpi_definitions)
    arch = load_archetype("generic")
    assert arch is not None
    assert "kpi_queries" not in arch
    assert "kpi_definitions" not in arch  # generic intentionally has no KPIs


def test_iot_archetype_unchanged():
    arch = load_archetype("iot")
    assert arch is not None
    assert "kpi_queries" not in arch
    assert "kpi_definitions" not in arch  # IoT has no BI KPIs defined
