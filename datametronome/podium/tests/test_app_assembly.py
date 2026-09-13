"""The API router must import and assemble into a usable app.

Added after a repo method named `list` shadowed the builtin for annotations
later in the same class body, which raised TypeError at import. The whole
suite still passed, because nothing imported the assembled router.

Routes are read from the generated OpenAPI schema rather than by walking
router.routes. FastAPI changed include_router to store lazy _IncludedRouter
wrappers, so walking the list finds no paths on newer versions. The schema is
the public contract and behaves the same across both.
"""

import functools

import pytest


@functools.lru_cache(maxsize=1)
def _schema() -> dict:
    from fastapi import FastAPI

    from datametronome_podium.api.v1.api import api_router

    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    return app.openapi()


def _routes() -> set[tuple[str, str]]:
    """Every (path, METHOD) pair the assembled app exposes."""
    return {
        (path, method.upper())
        for path, operations in _schema().get("paths", {}).items()
        for method in operations
    }


def test_api_router_assembles():
    assert _routes(), "app exposes no routes at all"


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/auth/login", "POST"),
        ("/api/v1/staves/", "GET"),
        ("/api/v1/clefs/", "GET"),
        ("/api/v1/groups/", "GET"),
        ("/api/v1/groups/{group_id}/members", "POST"),
        ("/api/v1/users/", "POST"),
    ],
)
def test_expected_route_is_registered(path, method):
    assert (path, method) in _routes()


def test_public_registration_is_not_registered():
    """Self-service registration was removed deliberately."""
    paths = {path for path, _ in _routes()}
    assert "/api/v1/auth/register" not in paths
