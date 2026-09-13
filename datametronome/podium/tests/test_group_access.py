"""Tests for group-based write access.

The rule under test: reads are global, writes are restricted to members of the
stave's owning group, and global admins bypass both.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from datametronome_podium.core.group_access import (
    assert_clef_group_access,
    assert_group_membership,
    assert_stave_group_access,
    is_super_admin,
    user_group_ids,
)

ADMIN = {"id": "root", "username": "root", "role": "admin"}
EDITOR_A = {"id": "alice", "username": "alice", "role": "editor"}
EDITOR_B = {"id": "bob", "username": "bob", "role": "editor"}


def _executor(responses):
    """Executor whose query() returns each queued response in order."""
    executor = MagicMock()
    executor.query = AsyncMock(side_effect=list(responses))
    return executor


def test_super_admin_detection():
    assert is_super_admin(ADMIN)
    assert not is_super_admin(EDITOR_A)
    assert not is_super_admin({})


@pytest.mark.asyncio
async def test_user_group_ids_returns_memberships():
    executor = _executor([[{"group_id": "g1"}, {"group_id": "g2"}]])
    assert await user_group_ids(EDITOR_A, executor) == ["g1", "g2"]


@pytest.mark.asyncio
async def test_user_without_id_has_no_groups():
    executor = _executor([])
    assert await user_group_ids({"username": "nobody"}, executor) == []
    executor.query.assert_not_called()


@pytest.mark.asyncio
async def test_member_may_write_own_group_stave():
    executor = _executor([
        [{"group_id": "g1"}],              # stave lookup
        [{"group_id": "g1"}],              # caller's memberships
    ])
    await assert_stave_group_access("stave-1", EDITOR_A, executor)


@pytest.mark.asyncio
async def test_non_member_is_refused():
    executor = _executor([
        [{"group_id": "g1"}],              # stave belongs to g1
        [{"group_id": "g2"}],              # caller is only in g2
    ])
    with pytest.raises(HTTPException) as exc:
        await assert_stave_group_access("stave-1", EDITOR_B, executor)

    assert exc.value.status_code == 403
    assert "another group" in exc.value.detail


@pytest.mark.asyncio
async def test_super_admin_bypasses_without_querying():
    executor = _executor([])
    await assert_stave_group_access("stave-1", ADMIN, executor)
    executor.query.assert_not_called()


@pytest.mark.asyncio
async def test_missing_stave_is_404_not_403():
    """A non-existent stave must not look like a permission problem."""
    executor = _executor([[]])
    with pytest.raises(HTTPException) as exc:
        await assert_stave_group_access("ghost", EDITOR_A, executor)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ungrouped_stave_is_refused():
    """A stave with no owner must not be writable by everyone."""
    executor = _executor([[{"group_id": None}]])
    with pytest.raises(HTTPException) as exc:
        await assert_stave_group_access("orphan", EDITOR_A, executor)

    assert exc.value.status_code == 403
    assert "no owning group" in exc.value.detail


@pytest.mark.asyncio
async def test_clef_inherits_group_from_its_stave():
    executor = _executor([
        [{"stave_id": "stave-1"}],         # clef lookup
        [{"group_id": "g1"}],              # stave lookup
        [{"group_id": "g1"}],              # caller's memberships
    ])
    await assert_clef_group_access("clef-1", EDITOR_A, executor)


@pytest.mark.asyncio
async def test_clef_write_refused_when_stave_belongs_elsewhere():
    executor = _executor([
        [{"stave_id": "stave-1"}],
        [{"group_id": "g1"}],
        [{"group_id": "g2"}],
    ])
    with pytest.raises(HTTPException) as exc:
        await assert_clef_group_access("clef-1", EDITOR_B, executor)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_clef_is_404():
    executor = _executor([[]])
    with pytest.raises(HTTPException) as exc:
        await assert_clef_group_access("ghost", EDITOR_A, executor)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_group_membership_required_to_create_in_group():
    executor = _executor([[{"group_id": "g1"}]])
    await assert_group_membership("g1", EDITOR_A, executor)

    executor = _executor([[{"group_id": "g1"}]])
    with pytest.raises(HTTPException) as exc:
        await assert_group_membership("g2", EDITOR_A, executor)
    assert exc.value.status_code == 403
