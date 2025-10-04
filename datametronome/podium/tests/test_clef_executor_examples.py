"""
Example tests for Clef Executor - showing how to execute data quality checks.

These tests demonstrate how to use the clef executor to run different types
of data quality checks against data sources.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from datametronome_podium.models.stave import Stave
from datametronome_podium.models.clef import Clef
from datametronome_podium.services.stave_service import (
    create_postgres_stave,
    create_null_check,
    create_range_check,
    create_volume_check,
    create_uniqueness_check,
    create_pattern_check,
    create_freshness_check
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
        assert "Email NULL Check" in result.message
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
            threshold=0.01  # Allow max 1% NULLs
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
        assert "exceeds threshold" in result.message
        assert result.anomalies_count == 100
        
        print(f"\n❌ NULL Check Failure: {result}")
        print(f"   Anomalies: {result.anomalies_count}")
    
    def test_execute_range_check_example(self, mock_db_connector):
        """Example: Execute a range validation check."""
        stave = create_postgres_stave(
            name="Product Database",
            host="db.example.com",
            database="products",
            user="monitor"
        )
        
        clef = create_range_check(
            stave_id=stave.id,
            name="Price Range Check",
            table="products",
            column="price",
            min_value=0.0,
            max_value=10000.0
        )
        
        # Mock database response
        mock_db_connector.query.return_value = [{
            "total_rows": 500,
            "out_of_range_rows": 0,  # All prices are valid
            "min_value": 1.99,
            "max_value": 999.99
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "pass"
        assert "within range" in result.message
        assert result.details["actual_range"]["min"] == 1.99
        assert result.details["actual_range"]["max"] == 999.99
        
        print(f"\n✅ Range Check Result: {result}")
        print(f"   Expected range: {result.details['expected_range']}")
        print(f"   Actual range: {result.details['actual_range']}")
    
    def test_execute_range_check_failure_example(self, mock_db_connector):
        """Example: Range check that fails."""
        stave = create_postgres_stave(
            name="Product Database",
            host="db.example.com",
            database="products",
            user="monitor"
        )
        
        clef = create_range_check(
            stave_id=stave.id,
            name="Price Range Check",
            table="products",
            column="price",
            min_value=0.0,
            max_value=1000.0
        )
        
        # Mock database response with out-of-range values
        mock_db_connector.query.return_value = [{
            "total_rows": 500,
            "out_of_range_rows": 25,  # 25 prices are out of range
            "min_value": -5.99,  # Negative price!
            "max_value": 1500.00  # Too expensive!
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "fail"
        assert "outside range" in result.message
        assert result.anomalies_count == 25
        
        print(f"\n❌ Range Check Failure: {result}")
        print(f"   Out of range: {result.details['out_of_range_rows']} rows")
    
    def test_execute_volume_check_example(self, mock_db_connector):
        """Example: Execute a row count (volume) check."""
        stave = create_postgres_stave(
            name="Orders Database",
            host="db.example.com",
            database="orders",
            user="monitor"
        )
        
        clef = create_volume_check(
            stave_id=stave.id,
            name="Daily Orders Volume",
            table="orders",
            expected_min=100,
            expected_max=1000
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
        assert "within expected range" in result.message
        assert result.details["actual_count"] == 750
        
        print(f"\n✅ Volume Check Result: {result}")
        print(f"   Actual count: {result.details['actual_count']}")
        print(f"   Expected range: {result.details['expected_range']}")
    
    def test_execute_volume_check_too_few_example(self, mock_db_connector):
        """Example: Volume check that fails due to too few rows."""
        stave = create_postgres_stave(
            name="Orders Database",
            host="db.example.com",
            database="orders",
            user="monitor"
        )
        
        clef = create_volume_check(
            stave_id=stave.id,
            name="Daily Orders Volume",
            table="orders",
            expected_min=100,
            expected_max=1000
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
        assert "too few rows" in result.message
        assert result.anomalies_count == 1
        
        print(f"\n❌ Volume Check Failure: {result}")
    
    def test_execute_custom_sql_check_example(self, mock_db_connector):
        """Example: Execute a custom SQL check."""
        stave = create_postgres_stave(
            name="Analytics Database",
            host="db.example.com",
            database="analytics",
            user="monitor"
        )
        
        clef = Clef(
            id="clef-custom-001",
            stave_id=stave.id,
            name="Active Users Check",
            check_type="custom_sql",
            config={
                "query": "SELECT COUNT(*) as active_users FROM users WHERE last_login > NOW() - INTERVAL '7 days'",
                "expected_min": 100
            }
        )
        
        # Mock database response
        mock_db_connector.query.return_value = [{
            "active_users": 150  # Above minimum
        }]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "pass"
        assert "within range" in result.message
        assert result.details["result"] == 150
        
        print(f"\n✅ Custom SQL Check Result: {result}")
        print(f"   Query: {clef.config['query']}")
        print(f"   Result: {result.details['result']}")
    
    def test_execute_uniqueness_check_example(self, mock_db_connector):
        """Example: Execute a uniqueness check."""
        stave = create_postgres_stave(
            name="User Database",
            host="db.example.com",
            database="users",
            user="monitor"
        )
        
        clef = create_uniqueness_check(
            stave_id=stave.id,
            name="Email Uniqueness Check",
            table="users",
            column="email"
        )
        
        # Mock database response - no duplicates
        mock_db_connector.query.return_value = []
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "pass"
        assert "no duplicate values" in result.message
        
        print(f"\n✅ Uniqueness Check Result: {result}")
    
    def test_execute_uniqueness_check_with_duplicates_example(self, mock_db_connector):
        """Example: Uniqueness check that finds duplicates."""
        stave = create_postgres_stave(
            name="User Database",
            host="db.example.com",
            database="users",
            user="monitor"
        )
        
        clef = create_uniqueness_check(
            stave_id=stave.id,
            name="Email Uniqueness Check",
            table="users",
            column="email"
        )
        
        # Mock database response - found duplicates
        mock_db_connector.query.return_value = [
            {"email": "duplicate@example.com", "duplicate_count": 3},
            {"email": "another@example.com", "duplicate_count": 2}
        ]
        
        # Execute the check
        import asyncio
        result = asyncio.run(execute_clef(clef, stave, mock_db_connector))
        
        # Verify the result
        assert result.status == "fail"
        assert "duplicate values found" in result.message
        assert result.anomalies_count == 2
        
        print(f"\n❌ Uniqueness Check Failure: {result}")
        print(f"   Duplicates found: {result.details['duplicates']}")
    
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
                column="email"
            ),
            create_range_check(
                stave_id=stave.id,
                name="Product Price Check",
                table="products",
                column="price",
                min_value=0.01,
                max_value=10000.0
            ),
            create_volume_check(
                stave_id=stave.id,
                name="Daily Orders Check",
                table="orders",
                expected_min=10,
                expected_max=1000
            )
        ]
        
        # Mock database responses
        def mock_query(query_dict):
            sql = query_dict["sql"]
            if "users" in sql and "email" in sql:
                return [{"total_rows": 1000, "non_null_rows": 995, "null_rows": 5}]
            elif "products" in sql and "price" in sql:
                return [{"total_rows": 500, "out_of_range_rows": 0, "min_value": 1.99, "max_value": 999.99}]
            elif "orders" in sql and "COUNT(*)" in sql:
                return [{"row_count": 150}]
            else:
                return []
        
        mock_db_connector.query.side_effect = mock_query
        
        # Execute all clefs
        import asyncio
        results = asyncio.run(execute_stave_clefs(stave, clefs, mock_db_connector))
        
        # Verify results
        assert len(results) == 3
        
        # Check individual results
        email_check = results[0]
        price_check = results[1]
        orders_check = results[2]
        
        assert email_check.status == "pass"
        assert price_check.status == "pass"
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
        mock_db_connector.query.return_value = [{"total_rows": 100, "non_null_rows": 95, "null_rows": 5}]
        
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
                message="NULL check passed: 0.5% NULLs (threshold: 1%)",
                details={"null_percentage": 0.005},
                execution_time=0.123,
                timestamp=datetime.now()
            ),
            CheckResult(
                clef_id="clef-002",
                stave_id="stave-001",
                status="fail",
                message="Range check failed: 25 values outside range [0, 1000]",
                details={"out_of_range_rows": 25},
                execution_time=0.456,
                timestamp=datetime.now(),
                anomalies_count=25
            ),
            CheckResult(
                clef_id="clef-003",
                stave_id="stave-001",
                status="error",
                message="Custom SQL execution failed: syntax error",
                details={"error": "syntax error"},
                execution_time=0.789,
                timestamp=datetime.now(),
                severity="high"
            )
        ]
        
        print(f"\n✅ Check Result Formatting Examples:")
        for result in results:
            print(f"   {result}")
            print(f"      Details: {result.details}")
            if result.anomalies_count > 0:
                print(f"      Anomalies: {result.anomalies_count}")


class TestClefExecutorIntegrationExamples:
    """Examples showing integration with real database connectors."""
    
    def test_execute_clef_with_real_connector_example(self):
        """Example: Execute clef with a real database connector (if available)."""
        # This example shows how you would use a real connector
        # In practice, you'd use one of the DataPulse connectors
        
        print(f"\n💡 Real Connector Integration Example:")
        print(f"   # Create a real PostgreSQL connector")
        print(f"   from metronome_pulse_postgres import PostgresPulse")
        print(f"   ")
        print(f"   # Connect to database")
        print(f"   connector = PostgresPulse(")
        print(f"       host='localhost',")
        print(f"       port=5432,")
        print(f"       database='mydb',")
        print(f"       user='monitor',")
        print(f"       password='secret'")
        print(f"   )")
        print(f"   await connector.connect()")
        print(f"   ")
        print(f"   # Execute clef")
        print(f"   result = await execute_clef(clef, stave, connector)")
        print(f"   print(f'Check result: {{result}}')")
        print(f"   ")
        print(f"   # Clean up")
        print(f"   await connector.disconnect()")
    
    def test_schedule_clef_execution_example(self):
        """Example: How clefs would be scheduled for execution."""
        print(f"\n💡 Scheduling Example:")
        print(f"   # Using APScheduler to run clefs on schedule")
        print(f"   from apscheduler.schedulers.asyncio import AsyncIOScheduler")
        print(f"   ")
        print(f"   scheduler = AsyncIOScheduler()")
        print(f"   ")
        print(f"   # Schedule a clef to run hourly")
        print(f"   scheduler.add_job(")
        print(f"       func=execute_clef,")
        print(f"       args=[clef, stave, connector],")
        print(f"       trigger='cron',")
        print(f"       minute=0,  # Every hour at minute 0")
        print(f"       id=f'clef_{clef.id}'")
        print(f"   )")
        print(f"   ")
        print(f"   # Schedule all clefs for a stave")
        print(f"   for clef in stave_clefs:")
        print(f"       if clef.schedule:")
        print(f"           scheduler.add_job(")
        print(f"               func=execute_clef,")
        print(f"               args=[clef, stave, connector],")
        print(f"               trigger='cron',")
        print(f"               **parse_cron(clef.schedule),")
        print(f"               id=f'clef_{clef.id}'")
        print(f"           )")
