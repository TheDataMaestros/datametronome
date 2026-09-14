"""Tests for group-based write access.

The rule under test: reads are global, writes are restricted to members of the
stave's owning group, and global admins bypass both.
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

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


@contextmanager
def _executor(responses):
    """Patch get_executor so query() returns each queued response in order."""
    executor = MagicMock()
    executor.query = AsyncMock(side_effect=list(responses))
    with patch(
        "datametronome_podium.core.group_access.get_executor", return_value=executor
    ):
        yield executor


def test_super_admin_detection():
    assert is_super_admin(ADMIN)
    assert not is_super_admin(EDITOR_A)
    assert not is_super_admin({})


@pytest.mark.asyncio
async def test_user_group_ids_returns_memberships():
    with _executor([[{"group_id": "g1"}, {"group_id": "g2"}]]) as executor:
        assert await user_group_ids(EDITOR_A) == ["g1", "g2"]


@pytest.mark.asyncio
async def test_user_without_id_has_no_groups():
    with _executor([]) as executor:
        assert await user_group_ids({"username": "nobody"}) == []
        executor.query.assert_not_called()


@pytest.mark.asyncio
async def test_member_may_write_own_group_stave():
    with _executor([
        [{"group_id": "g1"}],              # stave lookup
        [{"group_id": "g1"}],              # caller's memberships
    ]) as executor:
        await assert_stave_group_access("stave-1", EDITOR_A)


@pytest.mark.asyncio
async def test_non_member_is_refused():
    with _executor([
        [{"group_id": "g1"}],              # stave belongs to g1
        [{"group_id": "g2"}],              # caller is only in g2
    ]) as executor:
        with pytest.raises(HTTPException) as exc:
            await assert_stave_group_access("stave-1", EDITOR_B)

        assert exc.value.status_code == 403
        assert "another group" in exc.value.detail


@pytest.mark.asyncio
async def test_super_admin_bypasses_without_querying():
    with _executor([]) as executor:
        await assert_stave_group_access("stave-1", ADMIN)
        executor.query.assert_not_called()


@pytest.mark.asyncio
async def test_missing_stave_is_404_not_403():
    """A non-existent stave must not look like a permission problem."""
    with _executor([[]]) as executor:
        with pytest.raises(HTTPException) as exc:
            await assert_stave_group_access("ghost", EDITOR_A)

        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ungrouped_stave_is_refused():
    """A stave with no owner must not be writable by everyone."""
    with _executor([[{"group_id": None}]]) as executor:
        with pytest.raises(HTTPException) as exc:
            await assert_stave_group_access("orphan", EDITOR_A)

        assert exc.value.status_code == 403
        assert "no owning group" in exc.value.detail


@pytest.mark.asyncio
async def test_clef_inherits_group_from_its_stave():
    with _executor([
        [{"stave_id": "stave-1"}],         # clef lookup
        [{"group_id": "g1"}],              # stave lookup
        [{"group_id": "g1"}],              # caller's memberships
    ]) as executor:
        await assert_clef_group_access("clef-1", EDITOR_A)


@pytest.mark.asyncio
async def test_clef_write_refused_when_stave_belongs_elsewhere():
    with _executor([
        [{"stave_id": "stave-1"}],
        [{"group_id": "g1"}],
        [{"group_id": "g2"}],
    ]) as executor:
        with pytest.raises(HTTPException) as exc:
            await assert_clef_group_access("clef-1", EDITOR_B)

        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_clef_is_404():
    with _executor([[]]) as executor:
        with pytest.raises(HTTPException) as exc:
            await assert_clef_group_access("ghost", EDITOR_A)

        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_member_may_create_in_own_group():
    with _executor([[{"group_id": "g1"}]]):
        await assert_group_membership("g1", EDITOR_A)


@pytest.mark.asyncio
async def test_non_member_may_not_create_in_group():
    with _executor([[{"group_id": "g1"}]]):
        with pytest.raises(HTTPException) as exc:
            await assert_group_membership("g2", EDITOR_A)
    assert exc.value.status_code == 403
