"""preview-data and tables reach into the source database, so they are scoped
to the owning group rather than gated by role.

Viewing our own metadata about a stave stays open to every authenticated user;
these two do not, because they return the owning team's schema and rows.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

MEMBER = {"id": "alice", "username": "alice", "role": "viewer"}
OUTSIDER = {"id": "bob", "username": "bob", "role": "editor"}
ADMIN = {"id": "root", "username": "root", "role": "admin"}


def _client(user):
    from datametronome_podium.core.auth import get_current_user, require_editor
    from datametronome_podium.features.staves.router import router

    app = FastAPI()
    app.include_router(router, prefix="/staves")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_editor] = lambda: user
    return TestClient(app)


def _executor(stave_group, member_groups):
    """Executor answering the stave lookup then the membership lookup."""
    executor = MagicMock()
    executor.query = AsyncMock(
        side_effect=[
            [{"group_id": stave_group}],
            [{"group_id": g} for g in member_groups],
        ]
    )
    return executor


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/staves/s1/preview-data", {"table_name": "orders", "count": 10}),
        ("get", "/staves/s1/tables", None),
    ],
)
def test_outsider_is_refused(method, path, body):
    client = _client(OUTSIDER)
    executor = _executor(stave_group="g1", member_groups=["g2"])

    with patch(
        "datametronome_podium.core.group_access.get_executor", return_value=executor
    ):
        response = getattr(client, method)(path, **({"json": body} if body else {}))

    assert response.status_code == 403
    assert "another group" in response.json()["detail"]


@pytest.mark.parametrize(
    "method,path,body,service",
    [
        (
            "post",
            "/staves/s1/preview-data",
            {"table_name": "orders", "count": 10},
            "preview_data",
        ),
        ("get", "/staves/s1/tables", None, "list_tables"),
    ],
)
def test_member_is_allowed_even_as_viewer(method, path, body, service):
    """A viewer inside the owning group may read their own group's data."""
    client = _client(MEMBER)
    executor = _executor(stave_group="g1", member_groups=["g1"])

    with patch(
        "datametronome_podium.core.group_access.get_executor", return_value=executor
    ):
        with patch(
            f"datametronome_podium.features.staves.service.{service}",
            new=AsyncMock(return_value={"ok": True}),
        ):
            response = getattr(client, method)(path, **({"json": body} if body else {}))

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_admin_bypasses_group_scoping():
    client = _client(ADMIN)

    with patch(
        "datametronome_podium.features.staves.service.list_tables",
        new=AsyncMock(return_value={"tables": []}),
    ):
        response = client.get("/staves/s1/tables")

    assert response.status_code == 200
