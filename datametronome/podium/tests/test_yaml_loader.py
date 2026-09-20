"""
Tests for YAML configuration loading.

These tests demonstrate how to load staves and clefs from YAML files.
"""

import tempfile
from pathlib import Path

import pytest
from datametronome_podium.features.clefs.model import Clef
from datametronome_podium.features.staves.model import Stave
from datametronome_podium.services.stave_yaml_loader import (
    import_staves_from_yaml,
    load_single_stave_yaml,
    load_staves_from_yaml,
    validate_yaml_config,
)


class TestYAMLLoaderExamples:
    """Examples showing how to load staves from YAML files."""

    def test_load_multi_stave_yaml(self, tmp_path):
        """Example: Load multiple staves from YAML."""
        # Create a YAML file
        yaml_content = """
staves:
  - name: Production PostgreSQL
    data_source_type: postgres
    connection_config:
      host: db.example.com
      port: 5432
      database: prod_db
      user: monitor_user

  - name: Local SQLite
    data_source_type: sqlite
    connection_config:
      path: /data/local.db

clefs:
  - stave_id: stave-001
    name: Email NULL Check
    check_type: column_values
    config:
      table: users
      column: email
      condition: if_null
    fail: if_null > 0%
    schedule: "@hourly"
"""

        yaml_file = tmp_path / "staves.yaml"
        yaml_file.write_text(yaml_content)

        # Load from YAML
        staves, clefs = load_staves_from_yaml(yaml_file, resolve_env=False)

        # Verify staves loaded
        assert len(staves) == 2
        assert staves[0].name == "Production PostgreSQL"
        assert staves[0].data_source_type == "postgres"
        assert staves[0].connection_config["host"] == "db.example.com"

        assert staves[1].name == "Local SQLite"
        assert staves[1].data_source_type == "sqlite"

        # Verify clefs loaded
        assert len(clefs) == 1
        assert clefs[0].name == "Email NULL Check"
        assert clefs[0].check_type == "column_values"

        for stave in staves:
            pass

        for clef in clefs:
            pass

    def test_load_single_stave_yaml(self, tmp_path):
        """Example: Load a single stave with its clefs."""
        yaml_content = """
stave:
  name: Production Database
  data_source_type: postgres
  connection_config:
    host: db.example.com
    database: prod_db
    user: monitor

clefs:
  - name: Email Check
    check_type: column_values
    config:
      table: users
      column: email
      condition: if_null
    fail: if_null > 0%
    schedule: "@hourly"

  - name: Age Range Check
    check_type: column_values
    config:
      table: users
      column: age
      min: 0
      max: 150
"""

        yaml_file = tmp_path / "production-db.yaml"
        yaml_file.write_text(yaml_content)

        # Load from YAML
        stave, clefs = load_single_stave_yaml(yaml_file, resolve_env=False)

        # Verify stave
        assert stave.name == "Production Database"
        assert stave.data_source_type == "postgres"
        assert stave.id is not None  # Auto-generated

        # Verify clefs
        assert len(clefs) == 2
        assert clefs[0].name == "Email Check"
        assert clefs[1].name == "Age Range Check"

        # All clefs should reference the stave
        for clef in clefs:
            assert clef.stave_id == stave.id

        for clef in clefs:
            pass

    def test_yaml_with_env_vars(self, tmp_path, monkeypatch):
        """Example: YAML with environment variable substitution."""
        # Set environment variables
        monkeypatch.setenv("TEST_DB_HOST", "test-db.example.com")
        monkeypatch.setenv("TEST_DB_PORT", "5433")
        monkeypatch.setenv("TEST_DB_PASSWORD", "secret123")

        yaml_content = """
stave:
  name: Test Database
  data_source_type: postgres
  connection_config:
    host: ${TEST_DB_HOST}
    port: ${TEST_DB_PORT}
    database: testdb
    password: ${TEST_DB_PASSWORD}
    ssl_mode: ${SSL_MODE:-require}
"""

        yaml_file = tmp_path / "test-db.yaml"
        yaml_file.write_text(yaml_content)

        # Load with env var resolution
        stave, clefs = load_single_stave_yaml(yaml_file, resolve_env=True)

        # Verify env vars were resolved
        assert stave.connection_config["host"] == "test-db.example.com"
        assert stave.connection_config["port"] == 5433  # Converted to int
        assert stave.connection_config["password"] == "secret123"
        assert stave.connection_config["ssl_mode"] == "require"  # Default value


    def test_auto_generated_ids(self, tmp_path):
        """Example: IDs are auto-generated if not provided."""
        yaml_content = """
staves:
  - name: DB 1
    data_source_type: postgres
    connection_config:
      host: localhost

  - name: DB 2
    data_source_type: postgres
    connection_config:
      host: localhost

clefs:
  - stave_id: stave-001
    name: Check 1
    check_type: column_values
    config:
      table: users
      column: email
      condition: if_null
    fail: if_null > 0%
"""

        yaml_file = tmp_path / "auto-ids.yaml"
        yaml_file.write_text(yaml_content)

        staves, clefs = load_staves_from_yaml(yaml_file, resolve_env=False)

        # IDs should be auto-generated
        assert staves[0].id is not None
        assert staves[1].id is not None
        assert staves[0].id != staves[1].id  # Unique

        assert staves[0].id.startswith("stave-")
        assert staves[1].id.startswith("stave-")

        assert clefs[0].id is not None
        assert clefs[0].id.startswith("clef-")


    def test_validate_yaml(self, tmp_path):
        """Example: Validate YAML configuration."""
        # Valid configuration
        yaml_content = """
staves:
  - id: stave-001
    name: Test DB
    data_source_type: postgres
    connection_config:
      host: localhost

clefs:
  - id: clef-001
    stave_id: stave-001
    name: Test Check
    check_type: column_values
    config:
      table: users
      column: email
      condition: if_null
    fail: if_null > 0%
"""

        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(yaml_content)

        # Validate
        result = validate_yaml_config(yaml_file)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

        if result.get("warnings"):
            for warning in result["warnings"]:
                pass

    def test_validate_yaml_with_errors(self, tmp_path):
        """Example: Validation catches errors."""
        # Invalid configuration - clef references non-existent stave
        yaml_content = """
staves:
  - id: stave-001
    name: Test DB
    data_source_type: postgres
    connection_config:
      host: localhost

clefs:
  - stave_id: stave-999
    name: Test Check
    check_type: column_values
    config:
      table: users
      column: email
      condition: if_null
    fail: if_null > 0%
"""

        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)

        # Validate
        result = validate_yaml_config(yaml_file)

        assert result["valid"] is False
        assert len(result["issues"]) > 0

        for issue in result["issues"]:
            pass


class TestRealExampleFiles:
    """Test loading the actual example files."""

    def test_load_example_staves_yaml(self):
        """Example: Load the multi-stave example file."""
        example_file = Path(__file__).parent.parent / "examples" / "staves.yaml"

        if not example_file.exists():
            pytest.skip("Example file not found")  # ty: ignore

        # Load the example
        staves, clefs = load_staves_from_yaml(example_file, resolve_env=False)

        # Should have multiple staves and clefs
        assert len(staves) > 0
        assert len(clefs) > 0


        for stave in staves:
            pass


class _FakeDb:
    """write() returns None, matching Writable.write."""

    def __init__(self, existing=None):
        self.existing = existing or []
        self.writes = []
        self.executes = []

    async def query(self, _config):
        return self.existing

    async def write(self, data, destination, config=None):
        self.writes.append((data, destination))
        return None

    async def execute(self, sql, params=None):
        self.executes.append((sql, params))


class TestImportStavesFromYaml:
    @pytest.mark.asyncio
    async def test_counts_success_when_write_returns_none(self, tmp_path):
        yaml_file = tmp_path / "staves.yaml"
        yaml_file.write_text(
            """
staves:
  - id: stave-001
    name: Test DB
    data_source_type: sqlite
    connection_config:
      path: /tmp/test.db
clefs:
  - id: clef-001
    stave_id: stave-001
    name: Row count
    check_type: row_count
    config:
      table: users
"""
        )
        db = _FakeDb()
        counts = await import_staves_from_yaml(yaml_file, db, resolve_env=False)

        assert counts == {"staves": 1, "clefs": 1}
        assert [dest for _, dest in db.writes] == ["staves", "clefs"]
        assert db.executes == []
        for rows, _dest in db.writes:
            assert "table" not in rows[0]

    @pytest.mark.asyncio
    async def test_overwrite_updates_instead_of_inserting(self, tmp_path):
        yaml_file = tmp_path / "staves.yaml"
        yaml_file.write_text(
            """
staves:
  - id: stave-001
    name: Test DB
    data_source_type: sqlite
    connection_config:
      path: /tmp/test.db
clefs:
  - id: clef-001
    stave_id: stave-001
    name: Row count
    check_type: row_count
    config:
      table: users
"""
        )
        db = _FakeDb(existing=[{"id": "stave-001"}])
        counts = await import_staves_from_yaml(
            yaml_file, db, resolve_env=False, overwrite=True
        )

        assert counts == {"staves": 1, "clefs": 1}
        assert db.writes == []
        assert len(db.executes) == 2
        for sql, params in db.executes:
            assert sql.startswith("UPDATE ")
            assert " WHERE id = ?" in sql
            assert params[-1] in {"stave-001", "clef-001"}
            assert "group_id" not in sql
            assert "paused" not in sql

