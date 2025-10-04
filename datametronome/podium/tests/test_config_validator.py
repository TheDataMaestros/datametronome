"""
Tests for configuration validation and conflict detection.

These tests demonstrate how the validator detects dissonance and cacophony
in stave and clef configurations.
"""

import pytest
import tempfile
from pathlib import Path

from datametronome_podium.models.stave import Stave
from datametronome_podium.models.clef import Clef
from datametronome_podium.services.stave_service import (
    create_postgres_stave,
    create_redis_stave,
    create_null_check,
    create_range_check,
    create_volume_check
)
from datametronome_podium.services.config_validator import (
    ConfigurationValidator,
    ConfigurationIssue,
    validate_configuration
)


class TestConfigurationValidatorExamples:
    """Examples showing how the validator detects conflicts and dissonance."""
    
    def test_detect_missing_references(self):
        """Example: Detect when clefs reference non-existent staves."""
        # Create staves
        stave1 = create_postgres_stave(
            name="Production DB",
            host="db.example.com",
            database="prod",
            user="monitor"
        )
        
        # Create clef that references non-existent stave
        clef = create_null_check(
            stave_id="stave-nonexistent",  # This doesn't exist!
            name="Email Check",
            table="users",
            column="email"
        )
        
        # Validate
        result = validate_configuration([stave1], [clef])
        
        # Should detect the missing reference
        assert not result["valid"]
        assert len(result["issues"]) > 0
        
        missing_ref_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "missing" and "non-existent" in issue.message:
                missing_ref_issue = issue
                break
        
        assert missing_ref_issue is not None
        assert missing_ref_issue.severity == "error"
        assert "Email Check" in missing_ref_issue.affected_items
        
        print(f"\n✅ Detected missing reference:")
        print(f"   {missing_ref_issue}")
    
    def test_detect_duplicate_ids(self):
        """Example: Detect duplicate IDs across staves and clefs."""
        # Create staves with duplicate IDs
        stave1 = create_postgres_stave(
            name="DB 1",
            host="localhost",
            database="db1",
            user="user"
        )
        stave1.id = "duplicate-id"
        
        stave2 = create_postgres_stave(
            name="DB 2",
            host="localhost",
            database="db2",
            user="user"
        )
        stave2.id = "duplicate-id"  # Same ID!
        
        # Validate
        result = validate_configuration([stave1, stave2], [])
        
        # Should detect duplicate IDs
        assert not result["valid"]
        
        duplicate_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "conflict" and "Duplicate ID" in issue.message:
                duplicate_issue = issue
                break
        
        assert duplicate_issue is not None
        assert duplicate_issue.severity == "error"
        assert len(duplicate_issue.affected_items) == 2
        
        print(f"\n✅ Detected duplicate IDs:")
        print(f"   {duplicate_issue}")
    
    def test_detect_connection_conflicts(self):
        """Example: Detect when multiple staves connect to same database."""
        # Create staves that connect to the same database
        stave1 = create_postgres_stave(
            name="Users DB",
            host="db.example.com",
            port=5432,
            database="prod",
            user="monitor"
        )
        
        stave2 = create_postgres_stave(
            name="Orders DB",
            host="db.example.com",
            port=5432,
            database="prod",  # Same database!
            user="monitor"
        )
        
        # Validate
        result = validate_configuration([stave1, stave2], [])
        
        # Should detect connection conflict
        conflict_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "conflict" and "same PostgreSQL database" in issue.message:
                conflict_issue = issue
                break
        
        assert conflict_issue is not None
        assert conflict_issue.severity == "warning"
        assert "Users DB" in conflict_issue.affected_items
        assert "Orders DB" in conflict_issue.affected_items
        
        print(f"\n✅ Detected connection conflict:")
        print(f"   {conflict_issue}")
    
    def test_detect_range_check_conflicts(self):
        """Example: Detect invalid range configurations."""
        # Create a stave
        stave = create_postgres_stave(
            name="Test DB",
            host="localhost",
            database="test",
            user="user"
        )
        
        # Create invalid range check (min > max)
        clef = create_range_check(
            stave_id=stave.id,
            name="Invalid Range",
            table="users",
            column="age",
            min_value=150,
            max_value=0  # Invalid: min > max
        )
        
        # Validate
        result = validate_configuration([stave], [clef])
        
        # Should detect range conflict
        range_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "conflict" and "min > max" in issue.message:
                range_issue = issue
                break
        
        assert range_issue is not None
        assert range_issue.severity == "error"
        assert "Invalid Range" in range_issue.affected_items
        
        print(f"\n✅ Detected range conflict:")
        print(f"   {range_issue}")
    
    def test_detect_inappropriate_check_types(self):
        """Example: Detect when check type doesn't match data source type."""
        # Create Redis stave
        stave = create_redis_stave(
            name="Cache",
            host="redis.example.com"
        )
        
        # Create inappropriate check for Redis
        clef = create_null_check(
            stave_id=stave.id,
            name="Redis Null Check",
            table="users",  # Redis doesn't have tables!
            column="email"
        )
        
        # Validate
        result = validate_configuration([stave], [clef])
        
        # Should detect inappropriate check type
        inappropriate_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "inconsistent" and "Redis" in issue.message:
                inappropriate_issue = issue
                break
        
        assert inappropriate_issue is not None
        assert inappropriate_issue.severity == "warning"
        
        print(f"\n✅ Detected inappropriate check type:")
        print(f"   {inappropriate_issue}")
    
    def test_detect_schedule_conflicts(self):
        """Example: Detect too many checks scheduled at the same time."""
        # Create a stave
        stave = create_postgres_stave(
            name="Busy DB",
            host="localhost",
            database="busy",
            user="user"
        )
        
        # Create many checks scheduled hourly
        clefs = []
        for i in range(15):  # More than the threshold
            clef = create_volume_check(
                stave_id=stave.id,
                name=f"Hourly Check {i}",
                table=f"table_{i}",
                schedule="@hourly"
            )
            clefs.append(clef)
        
        # Validate
        result = validate_configuration([stave], clefs)
        
        # Should detect schedule conflict
        schedule_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "conflict" and "@hourly" in issue.message:
                schedule_issue = issue
                break
        
        assert schedule_issue is not None
        assert schedule_issue.severity == "warning"
        
        print(f"\n✅ Detected schedule conflict:")
        print(f"   {schedule_issue}")
    
    def test_detect_hardcoded_passwords(self):
        """Example: Detect hardcoded passwords in configurations."""
        # Create stave with hardcoded password
        stave = Stave(
            name="DB with Hardcoded Password",
            data_source_type="postgres",
            connection_config={
                "host": "db.example.com",
                "database": "prod",
                "user": "monitor",
                "password": "hardcoded_secret_123"  # Bad!
            }
        )
        
        # Validate
        result = validate_configuration([stave], [])
        
        # Should detect hardcoded password
        password_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "deprecated" and "hardcoded password" in issue.message:
                password_issue = issue
                break
        
        assert password_issue is not None
        assert password_issue.severity == "warning"
        
        print(f"\n✅ Detected hardcoded password:")
        print(f"   {password_issue}")
    
    def test_detect_production_localhost_conflict(self):
        """Example: Detect production staves using localhost."""
        # Create "production" stave using localhost
        stave = create_postgres_stave(
            name="Production Database",
            host="localhost",  # Production using localhost?
            database="prod",
            user="monitor"
        )
        
        # Validate
        result = validate_configuration([stave], [])
        
        # Should detect localhost conflict
        localhost_issue = None
        for issue in result["issues"]:
            if issue.issue_type == "inconsistent" and "localhost" in issue.message:
                localhost_issue = issue
                break
        
        assert localhost_issue is not None
        assert localhost_issue.severity == "warning"
        
        print(f"\n✅ Detected production localhost conflict:")
        print(f"   {localhost_issue}")
    
    def test_comprehensive_validation_example(self):
        """Example: Comprehensive validation with multiple issues."""
        # Create staves with various issues
        staves = [
            # Good stave
            create_postgres_stave(
                name="Good DB",
                host="good.example.com",
                database="good",
                user="monitor"
            ),
            
            # Stave with hardcoded password
            create_postgres_stave(
                name="Bad DB",
                host="bad.example.com",
                database="bad",
                user="monitor"
            )
        ]
        # Manually set hardcoded password
        staves[1].connection_config["password"] = "hardcoded123"
        
        # Create clefs with various issues
        clefs = [
            # Good clef
            create_null_check(
                stave_id=staves[0].id,
                name="Good Check",
                table="users",
                column="email"
            ),
            
            # Clef referencing non-existent stave
            create_null_check(
                stave_id="nonexistent",
                name="Bad Check",
                table="users",
                column="email"
            )
        ]
        
        # Validate
        result = validate_configuration(staves, clefs)
        
        # Should detect multiple issues
        assert not result["valid"]
        assert len(result["issues"]) >= 2
        
        print(f"\n✅ Comprehensive validation results:")
        print(f"   {result['summary']}")
        print(f"   Issues found: {len(result['issues'])}")
        
        for issue in result["issues"]:
            print(f"   - {issue}")
        
        # Check recommendations
        assert len(result["recommendations"]) > 0
        print(f"\n   Recommendations:")
        for rec in result["recommendations"]:
            print(f"   - {rec}")


class TestYAMLValidationExamples:
    """Examples showing YAML validation with conflict detection."""
    
    def test_validate_conflicting_yaml(self, tmp_path):
        """Example: Validate YAML with conflicts."""
        # Use the example conflicting config
        example_file = Path(__file__).parent.parent / "examples" / "conflicting-config.yaml"
        
        if not example_file.exists():
            pytest.skip("Example conflicting config file not found")
        
        # Validate the conflicting config
        from datametronome_podium.services.stave_yaml_loader import validate_yaml_config
        
        result = validate_yaml_config(example_file)
        
        # Should detect many issues
        assert not result["valid"]
        assert len(result["issues"]) > 10  # Should have many conflicts
        
        print(f"\n✅ YAML validation results:")
        print(f"   {result['summary']}")
        print(f"   Issues found: {len(result['issues'])}")
        
        # Group issues by severity
        errors = [i for i in result["issues"] if i.severity == "error"]
        warnings = [i for i in result["issues"] if i.severity == "warning"]
        info = [i for i in result["issues"] if i.severity == "info"]
        
        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")
        print(f"   Info: {len(info)}")
        
        # Show a few examples
        print(f"\n   Sample errors:")
        for issue in errors[:3]:
            print(f"   - {issue}")
        
        print(f"\n   Sample warnings:")
        for issue in warnings[:3]:
            print(f"   - {issue}")
    
    def test_validate_clean_yaml(self, tmp_path):
        """Example: Validate clean YAML with no conflicts."""
        # Create a clean YAML config
        yaml_content = """
staves:
  - id: stave-001
    name: Production Database
    data_source_type: postgres
    connection_config:
      host: db.example.com
      port: 5432
      database: prod_db
      user: monitor_user
      
  - id: stave-002
    name: Cache Database
    data_source_type: redis
    connection_config:
      host: redis.example.com
      port: 6379

clefs:
  - id: clef-001
    stave_id: stave-001
    name: Email Check
    check_type: null_check
    config:
      table: users
      column: email
      threshold: 0.0
    schedule: "@daily"
    
  - id: clef-002
    stave_id: stave-002
    name: Cache Volume Check
    check_type: volume_check
    config:
      table: sessions
      expected_min: 100
    schedule: "@hourly"
"""
        
        yaml_file = tmp_path / "clean-config.yaml"
        yaml_file.write_text(yaml_content)
        
        # Validate
        from datametronome_podium.services.stave_yaml_loader import validate_yaml_config
        
        result = validate_yaml_config(yaml_file)
        
        # Should be valid (no errors)
        assert result["valid"]
        assert len([i for i in result["issues"] if i.severity == "error"]) == 0
        
        print(f"\n✅ Clean YAML validation:")
        print(f"   {result['summary']}")
        print(f"   Issues: {len(result['issues'])}")
        
        for issue in result["issues"]:
            print(f"   - {issue}")


class TestValidatorOutputExamples:
    """Examples showing different types of validator output."""
    
    def test_issue_formatting_example(self):
        """Example: Show how issues are formatted."""
        issue = ConfigurationIssue(
            severity="error",
            issue_type="conflict",
            message="Duplicate ID 'stave-001' found",
            affected_items=["stave 'DB 1'", "stave 'DB 2'"],
            suggestion="Ensure all staves and clefs have unique IDs"
        )
        
        print(f"\n✅ Issue formatting example:")
        print(f"   {issue}")
        
        # Test different severities
        warning_issue = ConfigurationIssue(
            severity="warning",
            issue_type="conflict",
            message="Multiple staves connect to same database",
            affected_items=["Users DB", "Orders DB"],
            suggestion="Consider if you need separate staves"
        )
        
        print(f"   {warning_issue}")
        
        info_issue = ConfigurationIssue(
            severity="info",
            issue_type="performance",
            message="Stave has many clefs",
            affected_items=["Analytics DB"],
            suggestion="Consider consolidating some checks"
        )
        
        print(f"   {info_issue}")
    
    def test_validation_summary_example(self):
        """Example: Show validation summary format."""
        # Create some issues
        issues = [
            ConfigurationIssue("error", "conflict", "Duplicate ID found", ["DB 1", "DB 2"]),
            ConfigurationIssue("warning", "conflict", "Same connection used", ["DB 3", "DB 4"]),
            ConfigurationIssue("info", "performance", "Many checks scheduled", ["Check 1", "Check 2", "Check 3"])
        ]
        
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")
        
        summary = f"Configuration {'✅ VALID' if error_count == 0 else '❌ INVALID'}: "
        summary += f"{error_count} errors, {warning_count} warnings, {info_count} info"
        
        print(f"\n✅ Validation summary example:")
        print(f"   {summary}")
        print(f"   Total issues: {len(issues)}")
