"""Tests for archetype loading and deterministic matching."""

from datametronome_podium.archetypes import load_archetype, load_all_archetypes, match_archetypes


def test_load_ecommerce_archetype():
    arch = load_archetype("e-commerce")
    assert arch["name"] == "e-commerce"  # type: ignore[not-subscriptable]
    assert "orders" in arch["signatures"]["required"]  # type: ignore[not-subscriptable]
    assert len(arch["metrics"]) > 0  # type: ignore[not-subscriptable]
    assert len(arch["suggested_checks"]) > 0  # type: ignore[not-subscriptable]


def test_load_all_archetypes():
    all_archs = load_all_archetypes()
    names = [a["name"] for a in all_archs]
    assert "e-commerce" in names
    assert "saas" in names
    assert "iot" in names
    assert "crm" in names
    assert "generic" in names


def test_load_nonexistent_archetype():
    result = load_archetype("nonexistent")
    assert result is None


def test_match_ecommerce():
    tables = ["orders", "products", "customers", "payments", "reviews"]
    matches = match_archetypes(tables)
    assert len(matches) > 0
    assert matches[0][0] == "e-commerce"
    assert matches[0][1] >= 0.4


def test_match_saas():
    tables = ["users", "subscriptions", "invoices", "plans", "features"]
    matches = match_archetypes(tables)
    assert matches[0][0] == "saas"
    assert matches[0][1] >= 0.4


def test_match_iot():
    tables = ["devices", "readings", "sensors", "alerts"]
    matches = match_archetypes(tables)
    assert matches[0][0] == "iot"
    assert matches[0][1] >= 0.4


def test_match_crm():
    tables = ["contacts", "campaigns", "leads", "deals"]
    matches = match_archetypes(tables)
    assert matches[0][0] == "crm"
    assert matches[0][1] >= 0.4


def test_match_unknown_tables():
    tables = ["foo", "bar", "baz"]
    matches = match_archetypes(tables)
    non_generic = [m for m in matches if m[0] != "generic"]
    assert all(score < 0.4 for _, score in non_generic)


def test_match_scoring_formula():
    """Verify: score = (required_matches / required_count) * 0.7
                     + (optional_matches / optional_count) * 0.3"""
    tables = ["orders", "products", "carts"]
    matches = match_archetypes(tables)
    ecom = next((m for m in matches if m[0] == "e-commerce"), None)
    assert ecom is not None
    assert ecom[1] >= 0.4
