"""
End-to-end integration tests for YAML loader and scheduler integration.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from datametronome_podium.services.env_interpolator import interpolate_yaml_data
from datametronome_podium.services.scheduler_persistence import (
    create_scheduler_job,
    get_scheduler_job_by_clef_id,
)
from datametronome_podium.services.yaml_loader import load_and_parse_yaml


@pytest.mark.integration
class TestYAMLSchedulerIntegration:
    """Integration tests for YAML loader with scheduler."""

    @pytest.mark.asyncio
    async def test_yaml_import_creates_scheduled_jobs(self, tmp_path, monkeypatch):
        """Test that importing YAML with schedules creates scheduler jobs."""
        # Set environment variables
        monkeypatch.setenv("DB_PASSWORD", "secret123")

        yaml_content = """
staves:
  - id: stave-001
    name: Test DB
    data_source_type: postgres
    connection_config:
      host: localhost
      password: ${DB_PASSWORD}

clefs:
  - id: clef-001
    stave_id: stave-001
    name: Hourly Row Count
    check_type: row_count
    config:
      table: users
    schedule: "@hourly"
    warn: "> 50000"
    fail: "< 1000"

  - id: clef-002
    stave_id: stave-001
    name: Daily Freshness
    check_type: freshness
    config:
      table: users
      column: updated_at
    schedule: "0 8 * * *"
    warn: "> 12 hours"
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        # Load YAML data
        from datametronome_podium.services.yaml_loader import load_yaml_file

        yaml_data = load_yaml_file(str(yaml_file))

        # Interpolate environment variables
        yaml_data = interpolate_yaml_data(yaml_data, strict=True)

        # Parse staves and clefs
        from datametronome_podium.services.yaml_loader import parse_clefs, parse_staves

        staves = parse_staves(yaml_data)
        stave_id_map = {s.id: s.id for s in staves if s.id}
        clefs = parse_clefs(yaml_data, stave_id_map)

        assert len(staves) == 1
        assert len(clefs) == 2

        # Verify environment variable was interpolated
        assert staves[0].connection_config["password"] == "secret123"

        # Verify schedules are set
        assert clefs[0].schedule == "@hourly"
        assert clefs[1].schedule == "0 8 * * *"

        # Test that jobs can be created for these clefs
        with patch(
            "datametronome_podium.services.scheduler_persistence.get_db"
        ) as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value = []  # Job doesn't exist yet

            job1 = await create_scheduler_job(clefs[0].id, clefs[0].schedule)
            job2 = await create_scheduler_job(clefs[1].id, clefs[1].schedule)

            assert job1 is not None
            assert job2 is not None
            assert job1.clef_id == clefs[0].id
            assert job2.clef_id == clefs[1].id

    @pytest.mark.asyncio
    async def test_yaml_with_retry_config(self, tmp_path):
        """Test YAML with retry configuration."""
        yaml_content = """
staves:
  - id: stave-001
    name: Test DB
    data_source_type: sqlite
    connection_config:
      path: ":memory:"

clefs:
  - id: clef-001
    stave_id: stave-001
    name: Check with Retry
    check_type: row_count
    config:
      table: users
    schedule: "@hourly"
    retry_config:
      max_retries: 3
      backoff_factor: 2.0
      max_delay_seconds: 300
"""
        yaml_file = tmp_path / "retry.yaml"
        yaml_file.write_text(yaml_content)

        staves, clefs = load_and_parse_yaml(str(yaml_file))

        assert len(clefs) == 1
        assert clefs[0].retry_config is not None
        assert clefs[0].retry_config["max_retries"] == 3
        assert clefs[0].retry_config["backoff_factor"] == 2.0

    def test_nested_format_with_schedules(self, tmp_path):
        """Test nested YAML format with schedules."""
        yaml_content = """
staves:
  - id: stave-users
    name: User Database
    data_source_type: postgres
    connection_config:
      host: localhost
      database: users

clef:
  stave_id: stave-users
  table: users
  checks:
    - check: row_count
      name: User Count
      warn: "> 50000"
      fail: "< 1000"
      schedule: "@hourly"

    - check: freshness
      name: Data Freshness
      column: updated_at
      warn: "> 12 hours"
      schedule: "@daily"
"""
        yaml_file = tmp_path / "nested.yaml"
        yaml_file.write_text(yaml_content)

        staves, clefs = load_and_parse_yaml(str(yaml_file))

        assert len(staves) == 1
        assert len(clefs) == 2

        # Verify all clefs have schedules
        assert all(c.schedule for c in clefs)
        assert clefs[0].schedule == "@hourly"
        assert clefs[1].schedule == "@daily"

        # Verify all clefs reference the stave
        assert all(c.stave_id == staves[0].id for c in clefs)


@pytest.mark.integration
class TestSchedulerPersistenceIntegration:
    """Integration tests for scheduler persistence."""

    @pytest.mark.asyncio
    async def test_job_persistence_flow(self):
        """Test complete job persistence flow."""
        with patch(
            "datametronome_podium.services.scheduler_persistence.get_db"
        ) as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock that job doesn't exist
            mock_db.query.return_value = []

            # Create job
            job = await create_scheduler_job("clef-001", "0 * * * *")

            assert job is not None
            assert job.clef_id == "clef-001"
            assert job.schedule == "0 * * * *"
            assert job.enabled is True

            # Verify job was saved
            assert mock_db.write.called

            # Now mock that job exists
            from datametronome_podium.services.scheduler_persistence import (
                get_scheduler_job,
            )

            mock_db.query.return_value = [job.to_dict()]

            # Retrieve job
            retrieved = await get_scheduler_job(job.id)

            assert retrieved is not None
            assert retrieved.id == job.id
            assert retrieved.clef_id == job.clef_id
