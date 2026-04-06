"""Domain archetype loader and deterministic matcher."""

from __future__ import annotations

from pathlib import Path

import yaml

_ARCHETYPE_DIR = Path(__file__).parent

_cache: dict[str, dict] = {}


def _load_yaml(name: str) -> dict | None:
    """Load a single archetype YAML by its ``name`` field."""
    if name in _cache:
        return _cache[name]
    for f in _ARCHETYPE_DIR.glob("*.yaml"):
        data = yaml.safe_load(f.read_text())
        if data and data.get("name") == name:
            _cache[name] = data
            return data
    return None


def load_archetype(name: str) -> dict | None:
    """Load a single archetype by name. Returns None if not found."""
    return _load_yaml(name)


def load_all_archetypes() -> list[dict]:
    """Load all archetype YAML files."""
    archetypes: list[dict] = []
    for f in sorted(_ARCHETYPE_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        if data and "name" in data:
            _cache[data["name"]] = data
            archetypes.append(data)
    return archetypes


def match_archetypes(table_names: list[str]) -> list[tuple[str, float]]:
    """Score all archetypes against discovered table names.

    Returns list of (archetype_name, score) sorted by score descending.
    Score formula: (required_matches / required_count) * 0.7
                 + (optional_matches / optional_count) * 0.3
    """
    archetypes = load_all_archetypes()
    table_set = {t.lower() for t in table_names}
    results: list[tuple[str, float]] = []

    for arch in archetypes:
        sigs = arch.get("signatures", {})
        required = [r.lower() for r in sigs.get("required", [])]
        optional = [o.lower() for o in sigs.get("optional", [])]

        if not required and not optional:
            results.append((arch["name"], 0.0))
            continue

        req_matches = sum(1 for r in required if r in table_set)
        opt_matches = sum(1 for o in optional if o in table_set)

        req_score = (req_matches / len(required)) if required else 0.0
        opt_score = (opt_matches / len(optional)) if optional else 0.0

        score = req_score * 0.7 + opt_score * 0.3
        results.append((arch["name"], round(score, 4)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results
