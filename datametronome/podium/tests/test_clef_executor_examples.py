"""
Example tests for Clef Executor - showing how to execute data quality checks.

These tests demonstrate how to use the clef executor to run different types
of data quality checks against data sources.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from datametronome_podium.services.stave_service import (
    create_postgres_stave,
    create_null_check,
    create_clef
)
from datametronome_podium.services.clef_executor import (
    ClefExecutor,
    execute_clef,
    execute_stave_clefs,
    CheckResult
)


class TestClefExecutorExamples:
    """Examples showing how to execute different types of clefs."""
    
    @pytest.fixture
    def mock_db_connector(self):
        """Mock database connector for testing."""
        connector = AsyncMock()
        return connector
    
    def test_execute_null_check_example(self, mock_db_connector):
        """Example: Execute a NULL value check."""
        # Create a stave (data source)
        stave = create_postgres_stave(
            name="User Database",
            host="db.example.com",
            database="users",
            user="monitor"
        )
        
        # Create a NULL check clef
        clef = create_null_check(
            stave_id=stave.id,
            name="Email NULL Check",
            table="users",
            column="email",
            threshold=0.01  # Allow max 1% NULLs
        )
        
        # Mock database response
        mock_db_connector.query.return_value = [{
            "total_rows": 1000,
            "non_null_rows": 990,
            "null_rows": 10
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "pass"  # 1% NULLs is within 1% threshold
        assert "within acceptable limits" in result.message
        assert result.details["total_rows"] == 1000
        assert result.details["null_rows"] == 10
        assert result.details["null_percentage"] == 0.01
        
        print(f"\n✅ NULL Check Result: {result}")
        print(f"   Details: {result.details}")
    
    def test_execute_null_check_failure_example(self, mock_db_connector):
        """Example: NULL check that fails."""
        stave = create_postgres_stave(
            name="User Database",
            host="db.example.com",
            database="users",
            user="monitor"
        )
        
        clef = create_null_check(
            stave_id=stave.id,
            name="Email NULL Check",
            table="users",
            column="email",
            threshold=0.0  # No NULLs allowed for failure scenario
        )
        
        # Mock database response with too many NULLs
        mock_db_connector.query.return_value = [{
            "total_rows": 1000,
            "non_null_rows": 900,
            "null_rows": 100  # 10% NULLs - exceeds threshold!
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "fail"
        assert "violates fail condition" in result.message
        assert result.anomalies_count == 100
        
        print(f"\n❌ NULL Check Failure: {result}")
        print(f"   Anomalies: {result.anomalies_count}")
    
    def test_execute_row_count_check_example(self, mock_db_connector):
        """Example: Execute a row count (volume) check."""
        stave = create_postgres_stave(
            name="Orders Database",
            host="db.example.com",
            database="orders",
            user="monitor"
        )
        
        clef = create_clef(
            stave_id=stave.id,
            name="Daily Orders Volume",
            check_type="row_count",
            config={"table": "orders"},
            warn="< 200",
            fail="< 100"
        )
        
        # Mock database response
        mock_db_connector.query.return_value = [{
            "row_count": 750  # Within expected range
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "pass"
        assert "within acceptable range" in result.message
        assert result.details["row_count"] == 750
        
        print(f"\n✅ Volume Check Result: {result}")
        print(f"   Actual count: {result.details['row_count']}")
        print(f"   Conditions: warn={result.details['warn_condition']} fail={result.details['fail_condition']}")
    
    def test_execute_row_count_check_failure_example(self, mock_db_connector):
        """Example: Row count check that fails due to too few rows."""
        stave = create_postgres_stave(
            name="Orders Database",
            host="db.example.com",
            database="orders",
            user="monitor"
        )
        
        clef = create_clef(
            stave_id=stave.id,
            name="Daily Orders Volume",
            check_type="row_count",
            config={"table": "orders"},
            warn="< 200",
            fail="< 100"
        )
        
        # Mock database response with too few rows
        mock_db_connector.query.return_value = [{
            "row_count": 50  # Too few orders!
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "fail"
        assert "violates fail condition" in result.message
        assert result.anomalies_count == 1
        
        print(f"\n❌ Volume Check Failure: {result}")
    
    def test_execute_column_values_warn_example(self, mock_db_connector):
        """Example: Column values check that triggers a warning."""
        stave = create_postgres_stave(
            name="User Database",
            host="db.example.com",
            database="users",
            user="monitor"
        )
        
        clef = create_clef(
            stave_id=stave.id,
            name="Email NULL Warning",
            check_type="column_values",
            config={
                "table": "users",
                "column": "email",
                "condition": "if_null"
            },
            warn="if_null > 5%",
            fail="if_null > 20%"
        )
        
        # Mock database response with null rate between warn and fail thresholds (10%)
        mock_db_connector.query.return_value = [{
            "total_rows": 100,
            "non_null_rows": 90,
            "null_rows": 10
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "warn"
        assert "breaches warning condition" in result.message
        assert result.details["null_percentage"] == 0.1
        assert result.details["warn_condition"] == "if_null > 5%"
        
        print(f"\n⚠️  Column Values Warning Result: {result}")
    
    def test_execute_column_values_fail_example(self, mock_db_connector):
        """Example: Column values check that fails."""
        stave = create_postgres_stave(
            name="User Database",
            host="db.example.com",
            database="users",
            user="monitor"
        )
        
        clef = create_clef(
            stave_id=stave.id,
            name="Email NULL Failure",
            check_type="column_values",
            config={
                "table": "users",
                "column": "email",
                "condition": "if_null"
            },
            warn="if_null > 5%",
            fail="if_null > 20%"
        )
        
        # Mock database response with null rate above fail threshold (40%)
        mock_db_connector.query.return_value = [{
            "total_rows": 50,
            "non_null_rows": 30,
            "null_rows": 20
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "fail"
        assert "violates fail condition" in result.message
        assert result.anomalies_count == 20
        
        print(f"\n❌ Column Values Failure: {result}")
        print(f"   Null rows detected: {result.details['null_rows']}")
    
    def test_execute_multiple_clefs_example(self, mock_db_connector):
        """Example: Execute multiple clefs for a single stave."""
        # Create a stave
        stave = create_postgres_stave(
            name="E-commerce Database",
            host="db.example.com",
            database="ecommerce",
            user="monitor"
        )
        
        # Create multiple clefs
        clefs = [
            create_null_check(
                stave_id=stave.id,
                name="User Email Check",
                table="users",
                column="email",
                threshold=0.05
            ),
            create_clef(
                stave_id=stave.id,
                name="Abandoned Cart Warning",
                check_type="column_values",
                config={
                    "table": "carts",
                    "column": "abandoned_flag",
                    "condition": "if_null"
                },
                warn="if_null > 10%",
                fail="if_null > 25%"
            ),
            create_clef(
                stave_id=stave.id,
                name="Daily Orders Check",
                check_type="row_count",
                config={"table": "orders"},
                warn="< 120",
                fail="< 50"
            )
        ]
        
        # Mock database responses
        def mock_query(sql, *args, **kwargs):
            normalized_sql = " ".join(sql.split()).lower()
            if "from users" in normalized_sql and "count(*) - count(email)" in normalized_sql:
                return [{"total_rows": 1000, "non_null_rows": 990, "null_rows": 10}]
            if "from carts" in normalized_sql:
                return [{"total_rows": 80, "non_null_rows": 70, "null_rows": 10}]
            if "from orders" in normalized_sql:
                return [{"row_count": 140}]
            return []
        
        mock_db_connector.query.side_effect = mock_query
        
        # Execute all clefs
        import asyncio
        results = asyncio.run(execute_stave_clefs(stave, clefs, mock_db_connector))
        
        # Verify results
        assert len(results) == 3
        
        # Check individual results
        email_check, carts_check, orders_check = results
        
        assert email_check.status == "pass"
        assert carts_check.status == "warn"
        assert orders_check.status == "pass"
        
        print(f"\n✅ Multiple Clefs Results:")
        for i, result in enumerate(results):
            print(f"   {i+1}. {result}")
    
    def test_clef_executor_stats_example(self, mock_db_connector):
        """Example: Using clef executor with statistics."""
        # Create executor
        executor = ClefExecutor()
        
        # Create test data
        stave = create_postgres_stave(
            name="Test Database",
            host="localhost",
            database="test",
            user="test"
        )
        
        clefs = [
            create_null_check(stave_id=stave.id, name="Check 1", table="table1", column="col1"),
            create_null_check(stave_id=stave.id, name="Check 2", table="table2", column="col2"),
            create_null_check(stave_id=stave.id, name="Check 3", table="table3", column="col3")
        ]
        
        # Mock responses
        mock_db_connector.query.return_value = [{"total_rows": 100, "non_null_rows": 100, "null_rows": 0}]
        
        # Execute clefs
        import asyncio
        
        async def run_checks():
            results = []
            for clef in clefs:
                result = await executor.execute_clef(clef, stave, mock_db_connector)
                results.append(result)
            return results
        
        results = asyncio.run(run_checks())
        
        # Check stats
        stats = executor.get_execution_stats()
        
        assert stats["total_checks"] == 3
        assert stats["passed"] == 3
        assert stats["failed"] == 0
        assert stats["errors"] == 0
        assert stats["pass_rate"] == 1.0
        
        print(f"\n✅ Executor Statistics:")
        print(f"   Total checks: {stats['total_checks']}")
        print(f"   Passed: {stats['passed']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Errors: {stats['errors']}")
        print(f"   Pass rate: {stats['pass_rate']:.1%}")
        print(f"   Average time: {stats['average_time']:.3f}s")
    
    def test_check_result_formatting_example(self):
        """Example: Show how CheckResult objects are formatted."""
        # Create different types of results
        results = [
            CheckResult(
                clef_id="clef-001",
                stave_id="stave-001",
                status="pass",
                observed_value=0.005,
                message="NULL check passed: 0.5% NULLs (threshold: 1%)",
                metadata={"null_percentage": 0.005},
                execution_time=0.123,
                timestamp=datetime.now()
            ),
            CheckResult(
                clef_id="clef-002",
                stave_id="stave-001",
                status="fail",
                observed_value=25,
                message="Row count violated fail condition",
                metadata={"observed": 25, "fail_condition": "< 30"},
                execution_time=0.456,
                timestamp=datetime.now(),
                anomalies_count=25
            ),
            CheckResult(
                clef_id="clef-003",
                stave_id="stave-001",
                status="warn",
                observed_value=12.5,
                message="Freshness approaching threshold",
                metadata={"age_hours": 12.5, "warn_condition": "> 12h"},
                execution_time=0.789,
                timestamp=datetime.now()
            )
        ]
        
        print(f"\n✅ Check Result Formatting Examples:")
