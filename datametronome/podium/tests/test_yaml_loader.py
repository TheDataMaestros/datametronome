"""
Tests for YAML configuration loading.

These tests demonstrate how to load staves and clefs from YAML files.
"""

import tempfile
from pathlib import Path

import pytest
from datametronome_podium.models.clef import Clef
from datametronome_podium.models.stave import Stave
from datametronome_podium.services.stave_yaml_loader import (
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

        print(f"\n✅ Loaded {len(staves)} staves:")
        for stave in staves:
            print(f"   - {stave}")

        print(f"\n✅ Loaded {len(clefs)} clefs:")
        for clef in clefs:
            print(f"   - {clef}")

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

        print(f"\n✅ Loaded stave: {stave}")
        print(f"✅ Loaded {len(clefs)} clefs:")
        for clef in clefs:
            print(f"   - {clef}")

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

        print(f"\n✅ Environment variables resolved:")
        print(f"   host: {stave.connection_config['host']}")
        print(f"   port: {stave.connection_config['port']}")
        print(f"   ssl_mode: {stave.connection_config['ssl_mode']} (default)")

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

        print(f"\n✅ Auto-generated IDs:")
        print(f"   Stave 1: {staves[0].id}")
        print(f"   Stave 2: {staves[1].id}")
        print(f"   Clef 1:  {clefs[0].id}")

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

        print(f"\n{result['summary']}")
        if result.get("warnings"):
            print("Warnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")

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

        print(f"\n{result['summary']}")
        print("Issues:")
        for issue in result["issues"]:
            print(f"  - {issue}")


class TestRealExampleFiles:
    """Test loading the actual example files."""

    def test_load_example_staves_yaml(self):
        """Example: Load the multi-stave example file."""
        example_file = Path(__file__).parent.parent / "examples" / "staves.yaml"

        if not example_file.exists():
            pytest.skip("Example file not found")  # ty: ignore[too-many-positional-arguments, invalid-argument-type]

        # Load the example
        staves, clefs = load_staves_from_yaml(example_file, resolve_env=False)

        # Should have multiple staves and clefs
        assert len(staves) > 0
        assert len(clefs) > 0

        print(f"\n✅ Loaded example file: {example_file.name}")
        print(f"   Staves: {len(staves)}")
        print(f"   Clefs:  {len(clefs)}")

        for stave in staves:
            print(f"   - {stave.name} ({stave.data_source_type})")

    def test_load_example_production_db_yaml(self):
        """Example: Load the single-stave example file."""
        example_file = Path(__file__).parent.parent / "examples" / "production-db.yaml"

        if not example_file.exists():
            pytest.skip("Example file not found")  # ty: ignore[too-many-positional-arguments, invalid-argument-type]

        # Load the example
        stave, clefs = load_single_stave_yaml(example_file, resolve_env=False)

        assert stave is not None
        assert len(clefs) > 0

        print(f"\n✅ Loaded example file: {example_file.name}")
        print(f"   Stave: {stave.name}")
        print(f"   Clefs: {len(clefs)}")

        for clef in clefs:
            print(f"   - {clef.name} ({clef.check_type})")
