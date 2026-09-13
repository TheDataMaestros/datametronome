"""The API router must import and assemble.

Added after a repo method named `list` shadowed the builtin for annotations
later in the same class body, which raised TypeError at import. The whole
suite still passed, because nothing imported the assembled router.
"""

import pytest


def _route_pairs() -> list[tuple[str, str]]:
    """Every (path, method) the assembled router exposes."""
    from datametronome_podium.api.v1.api import api_router

    pairs: list[tuple[str, str]] = []
    for route in api_router.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not isinstance(path, str):
            continue
        pairs.extend((path, str(method)) for method in methods)
    return pairs


def _routes() -> set[tuple[str, str]]:
    return set(_route_pairs())


def test_api_router_imports():
    from datametronome_podium.api.v1.api import api_router

    assert api_router.routes


@pytest.mark.parametrize(
    "path,method",
    [
        ("/auth/login", "POST"),
        ("/staves/", "GET"),
        ("/clefs/", "GET"),
        ("/groups/", "GET"),
        ("/groups/{group_id}/members", "POST"),
        ("/users/", "POST"),
    ],
)
def test_expected_route_is_registered(path, method):
    assert (path, method) in _routes()


def test_public_registration_is_not_registered():
    paths = {path for path, _ in _routes()}
    assert "/auth/register" not in paths


def test_no_duplicate_route_definitions():
    """Two handlers on the same path and method means one silently wins."""
    seen = _route_pairs()
    duplicates = {item for item in seen if seen.count(item) > 1}
    assert not duplicates, f"duplicate routes: {sorted(duplicates)}"
