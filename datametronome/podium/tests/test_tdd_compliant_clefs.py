"""
Tests demonstrating TDD-compliant Clefs implementation.

This test file shows how our implementation aligns with the TDD Clefs specification
and demonstrates the proper usage of the new structure.
"""

from datetime import datetime

import pytest
from datametronome_podium.models.clef import (
    CHECK_LEVEL_MAPPING,
    LEGACY_CHECK_MAPPING,
    LEVEL_1_CHECKS,
    LEVEL_2_CHECKS,
    LEVEL_3_CHECKS,
    LEVEL_4_CHECKS,
    Clef,
)
from datametronome_podium.models.severity import SeverityLevel
from datametronome_podium.models.stave import Stave
from datametronome_podium.services.clef_executor import CheckResult


class TestTDDCompliantClefs:
    """Tests demonstrating TDD-compliant Clef structure and behavior."""

    def test_tdd_check_types_alignment(self):
        """Test that our check types match the TDD specification."""
        print(f"\n🎵 TDD CHECK TYPES ALIGNMENT")

        # Level 1: Declarative Checks
        print(f"   📊 Level 1 - Declarative Checks:")
        for check_type in LEVEL_1_CHECKS:
            # Provide minimal config for each check type
            config = {"table": "test_table"}
            if check_type == "freshness":
                config = {"column": "test_column"}
            elif check_type == "column_values":
                config = {"column": "test_column"}

            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config=config,
            )
            print(f"      ✅ {check_type}: {clef.level_description}")
            assert clef.level == 1

        # Level 2: Intelligent Checks
        print(f"   📊 Level 2 - Intelligent Checks:")
        for check_type in LEVEL_2_CHECKS:
            # Provide minimal config for each check type
            config = {"metric": "test_metric"}
            if check_type == "data_profile_drift":
                config = {"column": "test_column"}

            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config=config,
            )
            print(f"      ✅ {check_type}: {clef.level_description}")
            assert clef.level == 2

        # Level 3: Advanced Declarative Checks
        print(f"   📊 Level 3 - Advanced Declarative Checks:")
        for check_type in LEVEL_3_CHECKS:
            # Provide minimal config for lookup_validation
            config = {
                "lookup": {"pulse": "test", "query": "SELECT 1", "key_column": "id"}
            }

            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config=config,
            )
            print(f"      ✅ {check_type}: {clef.level_description}")
            assert clef.level == 3

        # Level 4: Custom Code
        print(f"   📊 Level 4 - Custom Code:")
        for check_type in LEVEL_4_CHECKS:
            # Provide minimal config for python
            config = {"script_path": "test.py"}

            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config=config,
            )
            print(f"      ✅ {check_type}: {clef.level_description}")
            assert clef.level == 4

    def test_tdd_compliant_clef_structure(self):
        """Test TDD-compliant Clef structure with warn/fail conditions."""
        print(f"\n🎵 TDD-COMPLIANT CLEF STRUCTURE")

        # Create a TDD-compliant clef
        clef = Clef(
            id="clef-001",
            stave_id="stave-001",
            name="Daily User Registration Volume",
            check_type="row_count",
            config={"table": "users"},
            warn="> 50000",  # TDD-compliant warn condition
            fail="< 1000",  # TDD-compliant fail condition
            schedule="@hourly",
        )

        print(f"   ✅ TDD-Compliant Clef: {clef}")
        print(f"      Warn condition: {clef.warn}")
        print(f"      Fail condition: {clef.fail}")
        print(f"      Level: {clef.level} ({clef.level_description})")

        # Verify structure
        assert clef.check_type == "row_count"
        assert clef.warn == "> 50000"
        assert clef.fail == "< 1000"
        assert clef.level == 1
        assert clef.level_description == "Declarative Checks"

    def test_tdd_checkresult_structure(self):
        """Test TDD-compliant CheckResult structure."""
        print(f"\n🎵 TDD-COMPLIANT CHECKRESULT STRUCTURE")

        # Create TDD-compliant CheckResult
        result = CheckResult(
            clef_id="clef-001",
            stave_id="stave-001",
            status="pass",  # TDD-compliant status
            observed_value=2500,  # TDD-compliant observed_value
            message="Row count check passed: 2500 rows within expected range",
            metadata={
                "total_rows": 2500,
                "expected_range": {"min": 1000, "max": 5000},
                "table": "users",
            },
            execution_time=0.123,
            anomalies_count=0,
        )

        print(f"   ✅ TDD-Compliant CheckResult: {result}")
        print(f"      Status: {result.status}")
        print(f"      Observed Value: {result.observed_value}")
        print(f"      Severity: {result.severity}")
        print(f"      Message: {result.message}")

        # Verify TDD compliance
        assert result.status == "pass"
        assert result.observed_value == 2500
        assert result.severity == SeverityLevel.HARMONY
        assert result.metadata is not None
        assert "total_rows" in result.metadata
        assert result.anomalies_count == 0

    def test_severity_mapping_tdd_compliance(self):
        """Test that status maps correctly to severity levels per TDD."""
        print(f"\n🎵 SEVERITY MAPPING TDD COMPLIANCE")

        # Test all status mappings
        test_cases = [
            ("pass", SeverityLevel.HARMONY, "✅"),
            ("warn", SeverityLevel.DISSONANCE, "⚠️"),
            ("fail", SeverityLevel.CACOPHONY, "❌"),
        ]

        for status, expected_severity, expected_icon in test_cases:
            result = CheckResult(
                clef_id="test",
                stave_id="test",
                status=status,
                observed_value=100,
                message=f"Test {status} result",
            )

            print(f"   {expected_icon} Status '{status}' → {result.severity}")
            assert result.severity == expected_severity
            assert result.severity.icon == expected_icon

    def test_legacy_check_mapping(self):
        """Test backward compatibility with legacy check types."""
        print(f"\n🎵 LEGACY CHECK MAPPING (BACKWARD COMPATIBILITY)")

        legacy_tests = [
            ("volume_check", "row_count"),
            ("freshness_check", "freshness"),
            ("null_check", "column_values"),
            ("range_check", "column_values"),
            ("pattern_check", "column_values"),
            ("uniqueness_check", "column_values"),
            ("drift_detection", "data_profile_drift"),
            ("custom_python", "python"),
        ]

        for legacy_type, tdd_type in legacy_tests:
            print(f"   📝 {legacy_type} → {tdd_type}")
            assert LEGACY_CHECK_MAPPING[legacy_type] == tdd_type

        print(f"   ✅ All {len(legacy_tests)} legacy mappings verified")

    def test_tdd_level_1_declarative_checks(self):
        """Test Level 1 Declarative Checks examples."""
        print(f"\n🎵 LEVEL 1: DECLARATIVE CHECKS EXAMPLES")

        # Row count check
        row_count_clef = Clef(
            id="clef-row-count",
            stave_id="stave-users",
            name="Daily User Registration Volume",
            check_type="row_count",
            config={"table": "users"},
            warn="> 50000",
            fail="< 1000",
            schedule="@hourly",
        )

        # Freshness check
        freshness_clef = Clef(
            id="clef-freshness",
            stave_id="stave-users",
            name="User Data Freshness",
            check_type="freshness",
            config={"column": "last_updated"},
            warn="> 12 hours",
            fail="> 48 hours",
            schedule="@hourly",
        )

        # Column values check
        column_values_clef = Clef(
            id="clef-email-null",
            stave_id="stave-users",
            name="Email NULL Check",
            check_type="column_values",
            config={"column": "email"},
            fail="if_null > 5%",
            schedule="@daily",
        )

        clefs = [row_count_clef, freshness_clef, column_values_clef]

        for clef in clefs:
            print(f"   ✅ {clef.name}: {clef.check_type} (Level {clef.level})")
            assert clef.level == 1
            assert clef.level_description == "Declarative Checks"

    def test_tdd_level_2_intelligent_checks(self):
        """Test Level 2 Intelligent Checks examples."""
        print(f"\n🎵 LEVEL 2: INTELLIGENT CHECKS EXAMPLES")

        # Forecast check
        forecast_clef = Clef(
            id="clef-forecast",
            stave_id="stave-users",
            name="User Registration Anomaly Detection",
            check_type="forecast",
            config={
                "metric": "row_count",
                "strategy": {"model": "sarima", "confidence": 95, "lookback_days": 30},
            },
            warn="> 80",
            fail="> 95",
            schedule="@daily",
        )

        # Data profile drift check
        drift_clef = Clef(
            id="clef-drift",
            stave_id="stave-users",
            name="User Age Distribution Drift",
            check_type="data_profile_drift",
            config={
                "column": "age",
                "strategy": {
                    "test": "kolmogorov_smirnov",
                    "critical_p_value": 0.05,
                    "reference_period": "last_30_days",
                    "comparison_period": "last_7_days",
                },
            },
            warn="> 0.10",
            fail="> 0.25",
            schedule="@weekly",
        )

        clefs = [forecast_clef, drift_clef]

        for clef in clefs:
            print(f"   ✅ {clef.name}: {clef.check_type} (Level {clef.level})")
            assert clef.level == 2
            assert clef.level_description == "Intelligent Checks"

    def test_tdd_level_3_advanced_declarative_checks(self):
        """Test Level 3 Advanced Declarative Checks examples."""
        print(f"\n🎵 LEVEL 3: ADVANCED DECLARATIVE CHECKS EXAMPLES")

        # Lookup validation check
        lookup_clef = Clef(
            id="clef-lookup",
            stave_id="stave-users",
            name="User API vs Database Reconciliation",
            check_type="lookup_validation",
            config={
                "lookup": {
                    "pulse": "stave-users",
                    "query": "SELECT DISTINCT id FROM users WHERE active = true",
                    "key_column": "id",
                },
                "validation": {
                    "pulse": "stave-api",
                    "query": "SELECT DISTINCT user_id FROM active_users WHERE user_id IN ({{ lookup_keys }})",
                    "key_column": "user_id",
                },
                "enforce": "existence_for_all",
            },
            warn="> 5%",
            fail="> 20%",
            schedule="@hourly",
        )

        print(
            f"   ✅ {lookup_clef.name}: {lookup_clef.check_type} (Level {lookup_clef.level})"
        )
        assert lookup_clef.level == 3
        assert lookup_clef.level_description == "Advanced Declarative Checks"

    def test_tdd_level_4_custom_code(self):
        """Test Level 4 Custom Code examples."""
        print(f"\n🎵 LEVEL 4: CUSTOM CODE EXAMPLES")

        # Python custom script check
        python_clef = Clef(
            id="clef-python",
            stave_id="stave-users",
            name="Complex User Business Rules Validation",
            check_type="python",
            config={
                "script_path": "datametronome_scripts/user_business_rules.py",
                "params": {
                    "min_age": 18,
                    "required_fields": ["email", "name", "phone"],
                    "business_rules": "premium_user_validation",
                    "compliance_threshold": 0.95,
                },
            },
            warn="> 0",
            fail="> 10",
            schedule="@daily",
        )

        print(
            f"   ✅ {python_clef.name}: {python_clef.check_type} (Level {python_clef.level})"
        )
        assert python_clef.level == 4
        assert python_clef.level_description == "Custom Code"

    def test_condition_string_examples(self):
        """Test various condition string formats per TDD specification."""
        print(f"\n🎵 CONDITION STRING EXAMPLES (TDD SPECIFICATION)")

        # Test various condition string formats
        condition_examples = [
            # Numeric comparisons
            ("> 1000", "Greater than 1000"),
            ("< 100", "Less than 100"),
            (">= 50", "Greater than or equal to 50"),
            ("<= 200", "Less than or equal to 200"),
            ("== 0", "Equal to 0"),
            ("!= 1", "Not equal to 1"),
            # Percentage comparisons
            ("> 5%", "Greater than 5%"),
            ("< 1%", "Less than 1%"),
            (">= 10%", "Greater than or equal to 10%"),
            # Time-based comparisons
            ("> 12 hours", "Greater than 12 hours"),
            ("< 1 hour", "Less than 1 hour"),
            ("> 2 days", "Greater than 2 days"),
            ("< 30 minutes", "Less than 30 minutes"),
            # Range comparisons
            ("between 1000 and 2000", "Between 1000 and 2000"),
            ("outside 0 and 100", "Outside the range 0-100"),
            # List comparisons
            ("in: ['A', 'B', 'C']", "Value must be in the list"),
            ("not_in: ['X', 'Y', 'Z']", "Value must not be in the list"),
            # Column-specific conditions
            ("if_null > 5%", "If NULL percentage greater than 5%"),
            ("if_not_unique > 0", "If not unique count greater than 0"),
            (
                "if_out_of_range: [0, 150] > 1%",
                "If out of range percentage greater than 1%",
            ),
            (
                "if_not_matching: '^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$' > 5%",
                "If not matching pattern percentage greater than 5%",
            ),
        ]

        for condition, description in condition_examples:
            print(f"   📝 '{condition}': {description}")

        print(f"   ✅ All {len(condition_examples)} condition string formats documented")

    def test_complete_tdd_workflow_example(self):
        """Test a complete TDD-compliant workflow example."""
        print(f"\n🎵 COMPLETE TDD WORKFLOW EXAMPLE")

        # Create a stave
        stave = Stave(
            id="stave-ecommerce",
            name="E-commerce Production Database",
            data_source_type="postgres",
            connection_config={
                "host": "prod-db.example.com",
                "database": "ecommerce",
                "user": "monitor",
            },
        )

        # Create TDD-compliant clefs from all levels
        tdd_clefs = [
            # Level 1: Declarative
            Clef(
                id="clef-orders-count",
                stave_id=stave.id,
                name="Daily Order Volume",
                check_type="row_count",
                config={"table": "orders"},
                warn="> 40000",
                fail="< 1000",
                schedule="@hourly",
            ),
            # Level 2: Intelligent
            Clef(
                id="clef-orders-forecast",
                stave_id=stave.id,
                name="Order Volume Anomaly Detection",
                check_type="forecast",
                config={
                    "metric": "row_count",
                    "strategy": {"model": "sarima", "confidence": 95},
                },
                warn="> 80",
                fail="> 95",
                schedule="@daily",
            ),
            # Level 3: Advanced Declarative
            Clef(
                id="clef-orders-lookup",
                stave_id=stave.id,
                name="Order-Customer Reconciliation",
                check_type="lookup_validation",
                config={
                    "lookup": {
                        "pulse": "stave-ecommerce",
                        "query": "SELECT DISTINCT customer_id FROM orders",
                        "key_column": "customer_id",
                    },
                    "validation": {
                        "pulse": "stave-customers",
                        "query": "SELECT DISTINCT id FROM customers WHERE id IN ({{ lookup_keys }})",
                        "key_column": "id",
                    },
                    "enforce": "existence_for_all",
                },
                warn="> 5%",
                fail="> 20%",
                schedule="@hourly",
            ),
            # Level 4: Custom Code
            Clef(
                id="clef-orders-business",
                stave_id=stave.id,
                name="Order Business Rules Validation",
                check_type="python",
                config={
                    "script_path": "business_rules/order_validation.py",
                    "params": {"min_amount": 0.01, "max_amount": 100000},
                },
                warn="> 0",
                fail="> 5",
                schedule="@daily",
            ),
        ]

        print(f"   🎼 Complete TDD-Compliant E-commerce Data Quality Pipeline:")
        print(f"      Stave: {stave}")
        print(f"      Total Clefs: {len(tdd_clefs)}")

        # Group by level
        level_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for clef in tdd_clefs:
            level_counts[clef.level] += 1
            print(f"      ✅ Level {clef.level} ({clef.level_description}): {clef.name}")

        print(f"   📊 Level Distribution:")
        for level, count in level_counts.items():
            if count > 0:
                level_desc = [
                    "",
                    "Declarative",
                    "Intelligent",
                    "Advanced Declarative",
                    "Custom Code",
                ][level]
                print(f"      Level {level} ({level_desc}): {count} checks")

        print(f"   🎯 TDD Compliance Benefits:")
        print(f"      • Consistent structure across all check types")
        print(
            f"      • Clear severity mapping (pass/warn/fail → Harmony/Dissonance/Cacophony)"
        )
        print(f"      • Standardized condition string syntax")
        print(f"      • Proper level organization per TDD specification")
        print(f"      • Backward compatibility with legacy check types")
