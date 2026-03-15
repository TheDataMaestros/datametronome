"""Verify that BI-enabled archetypes have kpi_queries and performer_dimensions."""
import pytest
from datametronome_podium.archetypes import load_archetype


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_kpi_queries(domain):
    arch = load_archetype(domain)
    assert arch is not None, f"Archetype {domain} not found"
    assert "kpi_queries" in arch, f"{domain} missing kpi_queries"
    assert len(arch["kpi_queries"]) > 0, f"{domain} kpi_queries is empty"


@pytest.mark.parametrize("domain", ["e-commerce", "saas", "crm"])
def test_archetype_has_performer_dimensions(domain):
    arch = load_archetype(domain)
    assert "performer_dimensions" in arch, f"{domain} missing performer_dimensions"
    # crm may have fewer dimensions — just check the key exists (can be empty list)


def test_generic_archetype_has_kpi_queries_key():
    arch = load_archetype("generic")
    assert arch is not None
    assert "kpi_queries" in arch
    # generic is intentionally empty — the key must exist but can be an empty dict
    assert isinstance(arch["kpi_queries"], dict)


def test_iot_archetype_unchanged():
    arch = load_archetype("iot")
    assert arch is not None
    # IoT does not get BI config — these keys must NOT be present
    assert "kpi_queries" not in arch
    assert "performer_dimensions" not in arch
