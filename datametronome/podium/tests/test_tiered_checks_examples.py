"""
Examples demonstrating the tiered checks and severity system.

This test file shows how the four tiers of data quality checks work
with the Harmony/Dissonance/Cacophony severity classification system.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from datametronome_podium.models.clef import (
    CHECK_TIER_MAPPING,
    TIER_1_CHECKS,
    TIER_2_CHECKS,
    TIER_3_CHECKS,
    TIER_4_CHECKS,
    Clef,
)
from datametronome_podium.models.severity import (
    SeverityLevel,
    SeverityThreshold,
    evaluate_severity,
)
from datametronome_podium.models.stave import Stave
from datametronome_podium.services.clef_executor import CheckResult, ClefExecutor


class TestTieredChecksExamples:
    """Examples showing the four tiers of data quality checks."""

    def test_tier_1_simple_declarative_checks(self):
        """Example: Tier 1 - Simple Declarative Checks for Analysts."""
        print(f"\n🎵 TIER 1: SIMPLE DECLARATIVE CHECKS")
        print(f"   Persona: Anyone (Analysts, Ops)")
        print(f"   Purpose: Basic data hygiene on a single data source")

        # Create a stave
        stave = Stave(
            id="stave-users",
            name="User Database",
            data_source_type="postgres",
            connection_config={
                "host": "db.example.com",
                "database": "users",
                "user": "monitor",
            },
        )

        # Tier 1 checks
        tier_1_clefs = [
            Clef(
                id="clef-email-null",
                stave_id=stave.id,
                name="Email NULL Check",
                check_type="null_check",
                config={"table": "users", "column": "email", "threshold": 0.01},
                severity_config={"warn": "> 5%", "fail": "> 20%"},
            ),
            Clef(
                id="clef-age-range",
                stave_id=stave.id,
                name="Age Range Validation",
                check_type="range_check",
                config={"table": "users", "column": "age", "min": 0, "max": 150},
                severity_config={"warn": "> 1%", "fail": "> 10%"},
            ),
            Clef(
                id="clef-user-volume",
                stave_id=stave.id,
                name="User Registration Volume",
                check_type="volume_check",
                config={"table": "users", "expected_min": 100, "expected_max": 10000},
                severity_config={"warn": "> 8000", "fail": "< 100"},
            ),
            Clef(
                id="clef-email-unique",
                stave_id=stave.id,
                name="Email Uniqueness",
                check_type="uniqueness_check",
                config={"table": "users", "column": "email"},
                severity_config={"warn": "> 0", "fail": "> 10"},
            ),
            Clef(
                id="clef-email-pattern",
                stave_id=stave.id,
                name="Email Format Validation",
                check_type="pattern_check",
                config={
                    "table": "users",
                    "column": "email",
                    "pattern": "^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$",
                },
                severity_config={"warn": "> 5%", "fail": "> 25%"},
            ),
        ]

        # Verify all are Tier 1
        for clef in tier_1_clefs:
            assert clef.tier == 1
            assert clef.tier_description == "Simple Declarative"
            assert clef.check_type in TIER_1_CHECKS
            print(f"   ✅ {clef.name}: {clef.check_type} (Tier {clef.tier})")

        print(f"   📊 Total Tier 1 checks: {len(tier_1_clefs)}")

    def test_tier_2_advanced_declarative_checks(self):
        """Example: Tier 2 - Advanced Declarative Checks for Power Users."""
        print(f"\n🎵 TIER 2: ADVANCED DECLARATIVE CHECKS")
        print(f"   Persona: Power Users, Data Analysts, Engineers")
        print(f"   Purpose: Complex, multi-source logic without writing Python")

        # Create staves for multi-source checks
        api_stave = Stave(
            id="stave-api",
            name="User API",
            data_source_type="api",
            connection_config={"base_url": "https://api.example.com"},
        )

        analytics_stave = Stave(
            id="stave-analytics",
            name="Analytics Database",
            data_source_type="postgres",
            connection_config={
                "host": "analytics.example.com",
                "database": "analytics",
            },
        )

        # Tier 2 checks
        tier_2_clefs = [
            Clef(
                id="clef-reconciliation",
                stave_id="stave-users",
                name="API vs DB User Count Reconciliation",
                check_type="reconciliation",
                config={
                    "source_a": {
                        "type": "stave-users",
                        "query": "SELECT COUNT(*) as total FROM users",
                    },
                    "source_b": {
                        "type": "stave-api",
                        "query": {"endpoint": "/users/count"},
                    },
                    "strategy": {
                        "type": "field_match",
                        "field": "total",
                        "tolerance": 0.01,
                    },
                },
                severity_config={"warn": "> 0.05", "fail": "> 0.10"},
            ),
            Clef(
                id="clef-freshness",
                stave_id="stave-users",
                name="User Data Freshness",
                check_type="freshness_check",
                config={
                    "table": "users",
                    "column": "last_updated",
                    "max_age_hours": 24,
                },
                severity_config={"warn": "> 12", "fail": "> 48"},
            ),
            Clef(
                id="clef-schema",
                stave_id="stave-users",
                name="User Table Schema",
                check_type="schema_check",
                config={
                    "table": "users",
                    "expected_columns": ["id", "email", "name", "age", "created_at"],
                    "expected_types": {
                        "id": "integer",
                        "email": "varchar",
                        "age": "integer",
                    },
                },
                severity_config={"warn": "> 0", "fail": "> 0"},
            ),
            Clef(
                id="clef-lookup",
                stave_id="stave-users",
                name="User Analytics Cross-Reference",
                check_type="lookup_validation",
                config={
                    "source_table": "users",
                    "source_column": "id",
                    "lookup_source": "stave-analytics",
                    "lookup_query": "SELECT DISTINCT user_id FROM user_events",
                    "lookup_column": "user_id",
                    "strategy": "all_source_must_exist_in_lookup",
                },
                severity_config={"warn": "> 5%", "fail": "> 20%"},
            ),
        ]

        # Verify all are Tier 2
        for clef in tier_2_clefs:
            assert clef.tier == 2
            assert clef.tier_description == "Advanced Declarative"
            assert clef.check_type in TIER_2_CHECKS
            print(f"   ✅ {clef.name}: {clef.check_type} (Tier {clef.tier})")

        print(f"   📊 Total Tier 2 checks: {len(tier_2_clefs)}")

    def test_tier_3_intelligent_checks(self):
        """Example: Tier 3 - Intelligent ML-Driven Checks."""
        print(f"\n🎵 TIER 3: INTELLIGENT CHECKS (ML-DRIVEN)")
        print(f"   Persona: The Platform (configured by analysts/engineers)")
        print(
            f"   Purpose: Proactive, stateful monitoring that learns from historical data"
        )

        # Tier 3 checks
        tier_3_clefs = [
            Clef(
                id="clef-forecast",
                stave_id="stave-users",
                name="User Registration Anomaly Detection",
                check_type="forecast",
                config={
                    "metric": "row_count",
                    "table": "users",
                    "time_column": "created_at",
                    "aggregation": "daily",
                    "model": "sarima",
                    "confidence": 95,
                    "lookback_days": 30,
                },
                severity_config={"warn": "> 80", "fail": "> 95"},
            ),
            Clef(
                id="clef-drift",
                stave_id="stave-users",
                name="User Age Distribution Drift",
                check_type="drift_detection",
                config={
                    "table": "users",
                    "column": "age",
                    "reference_period": "last_30_days",
                    "comparison_period": "last_7_days",
                    "method": "ks_test",
                    "threshold": 0.05,
                },
                severity_config={"warn": "> 0.10", "fail": "> 0.25"},
            ),
            Clef(
                id="clef-anomaly",
                stave_id="stave-analytics",
                name="User Activity Anomaly Detection",
                check_type="anomaly_detection",
                config={
                    "table": "user_events",
                    "metric": "event_count",
                    "time_column": "timestamp",
                    "aggregation": "hourly",
                    "algorithm": "isolation_forest",
                    "contamination": 0.1,
                },
                severity_config={"warn": "> 0.05", "fail": "> 0.15"},
            ),
        ]

        # Verify all are Tier 3
        for clef in tier_3_clefs:
            assert clef.tier == 3
            assert clef.tier_description == "Intelligent (ML-Driven)"
            assert clef.check_type in TIER_3_CHECKS
            print(f"   ✅ {clef.name}: {clef.check_type} (Tier {clef.tier})")

        print(f"   📊 Total Tier 3 checks: {len(tier_3_clefs)}")

    def test_tier_4_custom_python_checks(self):
        """Example: Tier 4 - Custom Python Checks for Data Engineers."""
        print(f"\n🎵 TIER 4: CUSTOM PYTHON CHECKS")
        print(f"   Persona: Data Engineers")
        print(
            f"   Purpose: Implementing any business rule that is too complex for declarative checks"
        )

        # Tier 4 checks
        tier_4_clefs = [
            Clef(
                id="clef-custom-python",
                stave_id="stave-users",
                name="Custom User Business Rule",
                check_type="custom_python",
                config={
                    "script_path": "datametronome_scripts/user_business_rules.py",
                    "function_name": "check_user_compliance",
                    "parameters": {
                        "min_age": 18,
                        "required_fields": ["email", "name", "phone"],
                        "business_rules": "premium_user_validation",
                    },
                },
                severity_config={"warn": "> 0", "fail": "> 10"},
            ),
            Clef(
                id="clef-custom-sql",
                stave_id="stave-users",
                name="Complex User Segmentation Check",
                check_type="custom_sql",
                config={
                    "query": """
                        SELECT
                          COUNT(*) as total_users,
                          COUNT(CASE WHEN age >= 18 AND age <= 65 THEN 1 END) as working_age_users,
                          COUNT(CASE WHEN email LIKE '%@gmail.com' THEN 1 END) as gmail_users
                        FROM users
                        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    """,
                    "expected_min": 1000,
                    "expected_max": 50000,
                },
                severity_config={"warn": "> 40000", "fail": "< 1000"},
            ),
        ]

        # Verify all are Tier 4
        for clef in tier_4_clefs:
            assert clef.tier == 4
            assert clef.tier_description == "Custom Python"
            assert clef.check_type in TIER_4_CHECKS
            print(f"   ✅ {clef.name}: {clef.check_type} (Tier {clef.tier})")

        print(f"   📊 Total Tier 4 checks: {len(tier_4_clefs)}")


class TestSeveritySystemExamples:
    """Examples demonstrating the Harmony/Dissonance/Cacophony severity system."""

    def test_severity_levels_basic(self):
        """Example: Basic severity level usage."""
        print(f"\n🎵 SEVERITY LEVELS: HARMONY/DISSONANCE/CACOPHONY")

        # Test each severity level
        harmony = SeverityLevel.HARMONY
        dissonance = SeverityLevel.DISSONANCE
        cacophony = SeverityLevel.CACOPHONY

        print(f"   {harmony}: {harmony.description}")
        print(f"   {dissonance}: {dissonance.description}")
        print(f"   {cacophony}: {cacophony.description}")

        # Test priority ordering
        assert harmony.priority == 1
        assert dissonance.priority == 2
        assert cacophony.priority == 3

        print(
            f"   📊 Priority order: {harmony.priority} < {dissonance.priority} < {cacophony.priority}"
        )

    def test_severity_thresholds_examples(self):
        """Example: Different severity threshold configurations."""
        print(f"\n🎵 SEVERITY THRESHOLD CONFIGURATIONS")

        # Conservative (strict) thresholds
        conservative = SeverityThreshold(
            dissonance_condition="> 1%", cacophony_condition="> 5%"
        )

        # Moderate thresholds
        moderate = SeverityThreshold(
            dissonance_condition="> 5%", cacophony_condition="> 20%"
        )

        # Lenient thresholds
        lenient = SeverityThreshold(
            dissonance_condition="> 10%", cacophony_condition="> 50%"
        )

        # Test different values against each threshold
        test_values = [0.005, 0.03, 0.15, 0.60]  # 0.5%, 3%, 15%, 60%

        print(f"   📊 Testing values: {[f'{v:.1%}' for v in test_values]}")
        print(f"   🎯 Conservative: {conservative}")
        print(f"   🎯 Moderate: {moderate}")
        print(f"   🎯 Lenient: {lenient}")

        for value in test_values:
            conservative_result = conservative.evaluate(value)
            moderate_result = moderate.evaluate(value)
            lenient_result = lenient.evaluate(value)

            print(
                f"   {value:.1%}: Conservative={conservative_result.icon}, Moderate={moderate_result.icon}, Lenient={lenient_result.icon}"
            )

    def test_severity_evaluation_examples(self):
        """Example: Real-world severity evaluation scenarios."""
        print(f"\n🎵 REAL-WORLD SEVERITY EVALUATION EXAMPLES")

        # Example 1: NULL percentage check
        null_percentage = 0.08  # 8% NULLs
        null_severity = evaluate_severity(
            value=null_percentage,
            dissonance_condition="> 5%",
            cacophony_condition="> 20%",
        )
        print(
            f"   📊 NULL Check (8% NULLs): {null_severity} - {null_severity.description}"
        )

        # Example 2: Volume check
        user_count = 150  # 150 users registered today
        volume_severity = evaluate_severity(
            value=user_count, dissonance_condition="> 500", cacophony_condition="< 100"
        )
        print(
            f"   📊 Volume Check (150 users): {volume_severity} - {volume_severity.description}"
        )

        # Example 3: Range violation check
        violations_percentage = 0.25  # 25% of values out of range
        range_severity = evaluate_severity(
            value=violations_percentage,
            dissonance_condition="> 5%",
            cacophony_condition="> 20%",
        )
        print(
            f"   📊 Range Check (25% violations): {range_severity} - {range_severity.description}"
        )

        # Example 4: Duplicate count check
        duplicate_count = 3  # 3 duplicate values found
        duplicate_severity = evaluate_severity(
            value=duplicate_count,
            dissonance_condition="> 0",
            cacophony_condition="> 10",
        )
        print(
            f"   📊 Uniqueness Check (3 duplicates): {duplicate_severity} - {duplicate_severity.description}"
        )

    def test_check_result_with_severity_examples(self):
        """Example: CheckResult objects with severity classification."""
        print(f"\n🎵 CHECK RESULT EXAMPLES WITH SEVERITY")

        # Create example results
        results = [
            CheckResult(
                clef_id="clef-001",
                stave_id="stave-001",
                severity=SeverityLevel.HARMONY,
                message="NULL check passed: 0.5% NULLs (threshold: 1%)",
                details={"null_percentage": 0.005, "total_rows": 1000, "null_rows": 5},
                execution_time=0.123,
                timestamp=datetime.now(),
                check_value=0.005,
            ),
            CheckResult(
                clef_id="clef-002",
                stave_id="stave-001",
                severity=SeverityLevel.DISSONANCE,
                message="Volume check warning: 5100 users exceeds warning threshold",
                details={
                    "actual_count": 5100,
                    "expected_range": {"min": 100, "max": 5000},
                },
                execution_time=0.456,
                timestamp=datetime.now(),
                anomalies_count=1,
                check_value=5100,
            ),
            CheckResult(
                clef_id="clef-003",
                stave_id="stave-001",
                severity=SeverityLevel.CACOPHONY,
                message="Range check failed: 25 values outside range [0, 1000]",
                details={
                    "out_of_range_rows": 25,
                    "total_rows": 100,
                    "violation_percentage": 0.25,
                },
                execution_time=0.789,
                timestamp=datetime.now(),
                anomalies_count=25,
                check_value=0.25,
            ),
        ]

        print(f"   📊 Check Results with Severity Classification:")
        for result in results:
            print(f"   {result}")
            print(f"      Details: {result.details}")
            print(f"      Anomalies: {result.anomalies_count}")
            print(f"      Check Value: {result.check_value}")
            print()

    def test_executor_stats_with_severity(self):
        """Example: Executor statistics using severity system."""
        print(f"\n🎵 EXECUTOR STATISTICS WITH SEVERITY SYSTEM")

        # Create executor and simulate results
        executor = ClefExecutor()

        # Simulate different results
        results = [
            CheckResult(
                "clef-1",
                "stave-1",
                SeverityLevel.HARMONY,
                "Pass",
                {},
                0.1,
                datetime.now(),
            ),
            CheckResult(
                "clef-2",
                "stave-1",
                SeverityLevel.HARMONY,
                "Pass",
                {},
                0.2,
                datetime.now(),
            ),
            CheckResult(
                "clef-3",
                "stave-1",
                SeverityLevel.DISSONANCE,
                "Warning",
                {},
                0.3,
                datetime.now(),
            ),
            CheckResult(
                "clef-4",
                "stave-1",
                SeverityLevel.CACOPHONY,
                "Critical",
                {},
                0.4,
                datetime.now(),
            ),
            CheckResult(
                "clef-5",
                "stave-1",
                SeverityLevel.HARMONY,
                "Pass",
                {},
                0.5,
                datetime.now(),
            ),
        ]

        # Update stats
        for result in results:
            executor._update_stats(result)

        # Get stats
        stats = executor.get_execution_stats()

        print(f"   📊 Execution Statistics:")
        print(f"      Total Checks: {stats['total_checks']}")
        print(f"      ✅ Harmony: {stats['harmony']} ({stats['harmony_rate']:.1%})")
        print(
            f"      ⚠️ Dissonance: {stats['dissonance']} ({stats['dissonance_rate']:.1%})"
        )
        print(
            f"      ❌ Cacophony: {stats['cacophony']} ({stats['cacophony_rate']:.1%})"
        )
        print(f"      Average Time: {stats['average_time']:.3f}s")

        # Verify stats
        assert stats["total_checks"] == 5
        assert stats["harmony"] == 3
        assert stats["dissonance"] == 1
        assert stats["cacophony"] == 1
        assert stats["harmony_rate"] == 0.6
        assert stats["dissonance_rate"] == 0.2
        assert stats["cacophony_rate"] == 0.2


class TestTieredChecksIntegrationExamples:
    """Examples showing how tiers work together in practice."""

    def test_tier_progression_example(self):
        """Example: How users might progress through tiers as they mature."""
        print(f"\n🎵 TIER PROGRESSION: USER MATURITY JOURNEY")

        # Stage 1: New team starts with Tier 1
        print(f"   📈 Stage 1: New Team - Tier 1 Simple Checks")
        tier_1_checks = [
            "null_check",
            "range_check",
            "volume_check",
            "uniqueness_check",
        ]
        for check_type in tier_1_checks:
            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config={},
            )
            print(f"      {clef.tier_description}: {check_type}")

        # Stage 2: Team grows, needs Tier 2
        print(f"   📈 Stage 2: Growing Team - Tier 2 Advanced Checks")
        tier_2_checks = [
            "reconciliation",
            "freshness_check",
            "schema_check",
            "lookup_validation",
        ]
        for check_type in tier_2_checks:
            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config={},
            )
            print(f"      {clef.tier_description}: {check_type}")

        # Stage 3: Mature team adopts Tier 3
        print(f"   📈 Stage 3: Mature Team - Tier 3 Intelligent Checks")
        tier_3_checks = ["forecast", "drift_detection", "anomaly_detection"]
        for check_type in tier_3_checks:
            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config={},
            )
            print(f"      {clef.tier_description}: {check_type}")

        # Stage 4: Expert team uses Tier 4
        print(f"   📈 Stage 4: Expert Team - Tier 4 Custom Checks")
        tier_4_checks = ["custom_python", "custom_sql"]
        for check_type in tier_4_checks:
            clef = Clef(
                id="temp",
                stave_id="temp",
                name="Example",
                check_type=check_type,
                config={},
            )
            print(f"      {clef.tier_description}: {check_type}")

    def test_severity_configuration_examples(self):
        """Example: Different severity configurations for different use cases."""
        print(f"\n🎵 SEVERITY CONFIGURATION EXAMPLES")

        # Financial data - very strict
        financial_config = {
            "warn": "> 0.1%",  # Dissonance at 0.1%
            "fail": "> 1%",  # Cacophony at 1%
        }

        # Marketing data - moderate
        marketing_config = {
            "warn": "> 5%",  # Dissonance at 5%
            "fail": "> 25%",  # Cacophony at 25%
        }

        # Experimental data - lenient
        experimental_config = {
            "warn": "> 20%",  # Dissonance at 20%
            "fail": "> 50%",  # Cacophony at 50%
        }

        # Test configurations
        test_value = 0.10  # 10%

        print(f"   📊 Testing 10% violation rate against different configurations:")

        for name, config in [
            ("Financial", financial_config),
            ("Marketing", marketing_config),
            ("Experimental", experimental_config),
        ]:
            severity = evaluate_severity(
                value=test_value,
                dissonance_condition=config["warn"],
                cacophony_condition=config["fail"],
            )
            print(f"      {name}: {severity} - {severity.description}")

    def test_complete_data_quality_pipeline_example(self):
        """Example: Complete data quality pipeline using all tiers."""
        print(f"\n🎵 COMPLETE DATA QUALITY PIPELINE EXAMPLE")

        # Create a comprehensive stave with checks from all tiers
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

        # Tier 1: Basic hygiene checks
        tier_1_clefs = [
            Clef(
                id="clef-orders-null",
                stave_id=stave.id,
                name="Order Amount NULL Check",
                check_type="null_check",
                config={"table": "orders", "column": "amount"},
                severity_config={"warn": "> 1%", "fail": "> 5%"},
            ),
            Clef(
                id="clef-orders-volume",
                stave_id=stave.id,
                name="Daily Order Volume",
                check_type="volume_check",
                config={"table": "orders", "expected_min": 1000, "expected_max": 50000},
                severity_config={"warn": "> 40000", "fail": "< 1000"},
            ),
        ]

        # Tier 2: Advanced checks
        tier_2_clefs = [
            Clef(
                id="clef-orders-freshness",
                stave_id=stave.id,
                name="Order Data Freshness",
                check_type="freshness_check",
                config={"table": "orders", "column": "created_at", "max_age_hours": 1},
                severity_config={"warn": "> 0.5", "fail": "> 2"},
            )
        ]

        # Tier 3: Intelligent checks
        tier_3_clefs = [
            Clef(
                id="clef-orders-forecast",
                stave_id=stave.id,
                name="Order Volume Anomaly Detection",
                check_type="forecast",
                config={
                    "metric": "row_count",
                    "table": "orders",
                    "time_column": "created_at",
                    "aggregation": "hourly",
                    "model": "sarima",
                },
                severity_config={"warn": "> 80", "fail": "> 95"},
            )
        ]

        # Tier 4: Custom business logic
        tier_4_clefs = [
            Clef(
                id="clef-orders-business",
                stave_id=stave.id,
                name="Order Business Rules Validation",
                check_type="custom_python",
                config={
                    "script_path": "business_rules/order_validation.py",
                    "function_name": "validate_order_rules",
                },
                severity_config={"warn": "> 0", "fail": "> 5"},
            )
        ]

        # Combine all checks
        all_clefs = tier_1_clefs + tier_2_clefs + tier_3_clefs + tier_4_clefs

        print(f"   🎼 Complete E-commerce Data Quality Pipeline:")
        print(f"      Stave: {stave}")
        print(f"      Total Checks: {len(all_clefs)}")

        # Group by tier
        tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for clef in all_clefs:
            tier_counts[clef.tier] += 1

        for tier, count in tier_counts.items():
            if count > 0:
                tier_desc = [
                    "",
                    "Simple Declarative",
                    "Advanced Declarative",
                    "Intelligent (ML-Driven)",
                    "Custom Python",
                ][tier]
                print(f"      Tier {tier} ({tier_desc}): {count} checks")

        print(f"   🎯 This provides comprehensive coverage:")
        print(f"      • Basic data hygiene (Tier 1)")
        print(f"      • Advanced multi-source validation (Tier 2)")
        print(f"      • Intelligent anomaly detection (Tier 3)")
        print(f"      • Custom business logic (Tier 4)")
        print(f"      • All using Harmony/Dissonance/Cacophony severity classification")
