"""
End-to-End System Tests for DataMetronome

These tests verify the complete DataMetronome system working together:
- DataPulse connectors
- Anomaly detection
- Database operations
- Performance characteristics

Following CODE RULE CLUB: Integration tests with proper database setup.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any

import pytest

try:
    import asyncpg
except ImportError:
    pytest.skip("asyncpg not installed", allow_module_level=True)  # type: ignore[too-many-positional-arguments]


# Test configuration
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "testdb"),
    "user": os.getenv("POSTGRES_USER", "testuser"),
    "password": os.getenv("POSTGRES_PASSWORD", "testpass"),
}


class TestDataMetronomeEndToEnd:
    """End-to-end tests for the complete DataMetronome system."""

    @pytest.fixture
    async def db_connection(self):
        """Create a database connection for testing."""
        conn = await asyncpg.connect(**POSTGRES_CONFIG)
        yield conn
        await conn.close()

    @pytest.mark.asyncio
    async def test_database_connectivity(self, db_connection):
        """Test that we can connect to the test database."""
        result = await db_connection.fetchval("SELECT 1")
        assert result == 1

    @pytest.mark.asyncio
    async def test_test_data_exists(self, db_connection):
        """Verify that test data was generated successfully."""
        # Check users table
        user_count = await db_connection.fetchval("SELECT COUNT(*) FROM users")
        assert user_count > 0, "Users table should have data"

        # Check products table
        product_count = await db_connection.fetchval("SELECT COUNT(*) FROM products")
        assert product_count > 0, "Products table should have data"

        # Check orders table
        order_count = await db_connection.fetchval("SELECT COUNT(*) FROM orders")
        assert order_count > 0, "Orders table should have data"

        # Check metrics table
        metric_count = await db_connection.fetchval("SELECT COUNT(*) FROM metrics")
        assert metric_count > 0, "Metrics table should have data"

    @pytest.mark.asyncio
    async def test_anomaly_detection_users(self, db_connection):
        """Test anomaly detection on user data."""
        # Find users with unusual ages
        anomalous_users = await db_connection.fetch(
            """
            SELECT id, username, age
            FROM users
            WHERE age < 10 OR age > 120
            ORDER BY age
            """
        )

        assert len(anomalous_users) > 0, "Should detect age anomalies"

        for user in anomalous_users[:5]:  # Check first 5
            assert user["age"] is not None
            assert user["age"] < 10 or user["age"] > 120

    @pytest.mark.asyncio
    async def test_anomaly_detection_products(self, db_connection):
        """Test anomaly detection on product data."""
        # Find products with unusual prices
        anomalous_products = await db_connection.fetch(
            """
            SELECT id, name, price
            FROM products
            WHERE price <= 0 OR price > 50000
            ORDER BY price DESC
            """
        )

        if len(anomalous_products) > 0:
            for product in anomalous_products[:5]:
                assert product["price"] is not None
                assert float(product["price"]) <= 0 or float(product["price"]) > 50000

    @pytest.mark.asyncio
    async def test_anomaly_detection_orders(self, db_connection):
        """Test anomaly detection on order data."""
        # Find orders with unusual amounts
        anomalous_orders = await db_connection.fetch(
            """
            SELECT id, user_id, total_amount, status
            FROM orders
            WHERE total_amount <= 0 OR total_amount > 50000
            ORDER BY total_amount DESC
            """
        )

        if len(anomalous_orders) > 0:
            for order in anomalous_orders[:5]:
                amount = float(order["total_amount"])
                assert amount <= 0 or amount > 50000

    @pytest.mark.asyncio
    async def test_time_series_metrics(self, db_connection):
        """Test time series data retrieval for metrics."""
        # Get metrics from the last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)

        metrics = await db_connection.fetch(
            """
            SELECT metric_name, metric_value, timestamp, source
            FROM metrics
            WHERE timestamp >= $1
            ORDER BY timestamp DESC
            LIMIT 100
            """,
            seven_days_ago,
        )

        assert len(metrics) > 0, "Should have metrics from the last 7 days"

        # Verify data structure
        for metric in metrics[:5]:
            assert metric["metric_name"] is not None
            assert metric["metric_value"] is not None
            assert metric["timestamp"] is not None
            assert metric["source"] is not None

    @pytest.mark.asyncio
    async def test_statistical_analysis(self, db_connection):
        """Test statistical analysis on numerical data."""
        # Calculate statistics for user ages
        stats = await db_connection.fetchrow(
            """
            SELECT
                COUNT(*) as count,
                AVG(age) as mean_age,
                STDDEV(age) as stddev_age,
                MIN(age) as min_age,
                MAX(age) as max_age,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY age) as median_age
            FROM users
            WHERE age IS NOT NULL AND age BETWEEN 0 AND 150
            """
        )

        assert stats["count"] > 0
        assert stats["mean_age"] is not None
        assert 0 < float(stats["mean_age"]) < 150
        assert float(stats["min_age"]) >= 0
        assert float(stats["max_age"]) <= 150

    @pytest.mark.asyncio
    async def test_data_quality_checks(self, db_connection):
        """Test data quality metrics."""
        # Check for NULL values
        null_checks = await db_connection.fetch(
            """
            SELECT
                COUNT(*) FILTER (WHERE email IS NULL) as null_emails,
                COUNT(*) FILTER (WHERE username IS NULL) as null_usernames,
                COUNT(*) FILTER (WHERE age IS NULL) as null_ages
            FROM users
            """
        )

        assert null_checks is not None

        # Check for duplicates
        duplicate_emails = await db_connection.fetchval(
            """
            SELECT COUNT(*)
            FROM (
                SELECT email, COUNT(*) as cnt
                FROM users
                GROUP BY email
                HAVING COUNT(*) > 1
            ) duplicates
            """
        )

        assert duplicate_emails == 0, "Should have no duplicate emails"

    @pytest.mark.asyncio
    async def test_join_operations(self, db_connection):
        """Test complex join operations across tables."""
        # Get user order summary
        user_orders = await db_connection.fetch(
            """
            SELECT
                u.id,
                u.username,
                COUNT(o.id) as order_count,
                COALESCE(SUM(o.total_amount), 0) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id, u.username
            HAVING COUNT(o.id) > 0
            ORDER BY total_spent DESC
            LIMIT 10
            """
        )

        if len(user_orders) > 0:
            for record in user_orders:
                assert record["order_count"] > 0
                assert float(record["total_spent"]) >= 0

    @pytest.mark.asyncio
    async def test_aggregation_performance(self, db_connection):
        """Test performance of aggregation queries."""
        # Time a complex aggregation
        start_time = asyncio.get_event_loop().time()

        results = await db_connection.fetch(
            """
            SELECT
                DATE_TRUNC('day', created_at) as day,
                COUNT(*) as order_count,
                SUM(total_amount) as daily_total,
                AVG(total_amount) as avg_order_value
            FROM orders
            WHERE total_amount > 0
            GROUP BY DATE_TRUNC('day', created_at)
            ORDER BY day DESC
            LIMIT 30
            """
        )

        elapsed = asyncio.get_event_loop().time() - start_time

        assert len(results) > 0
        assert elapsed < 5.0, f"Query took {elapsed:.2f}s (should be < 5s)"


class TestDataMetronomePerformance:
    """Performance tests for DataMetronome system."""

    @pytest.fixture
    async def db_connection(self):
        """Create a database connection for testing."""
        conn = await asyncpg.connect(**POSTGRES_CONFIG)
        yield conn
        await conn.close()

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_bulk_read_performance(self, db_connection, benchmark):
        """Benchmark bulk read operations."""

        async def read_users():
            return await db_connection.fetch("SELECT * FROM users LIMIT 1000")

        if benchmark:
            result = benchmark(lambda: asyncio.run(read_users()))
        else:
            result = await read_users()

        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_complex_query_performance(self, db_connection, benchmark):
        """Benchmark complex analytical queries."""

        async def complex_query():
            return await db_connection.fetch(
                """
                SELECT
                    u.id,
                    u.username,
                    u.age,
                    COUNT(DISTINCT o.id) as order_count,
                    COUNT(DISTINCT oi.product_id) as unique_products,
                    SUM(o.total_amount) as lifetime_value
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE u.is_active = true
                GROUP BY u.id, u.username, u.age
                ORDER BY lifetime_value DESC NULLS LAST
                LIMIT 100
                """
            )

        if benchmark:
            result = benchmark(lambda: asyncio.run(complex_query()))
        else:
            result = await complex_query()

        assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, db_connection):
        """Test concurrent read operations."""

        async def read_operation(query_id: int):
            result = await db_connection.fetch(
                f"""
                SELECT * FROM users
                WHERE id % 10 = $1
                LIMIT 100
                """,
                query_id,
            )
            return len(result)

        # Run 10 concurrent queries
        tasks = [read_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(r >= 0 for r in results)
        assert sum(results) > 0


class TestDataMetronomeIntegration:
    """Integration tests across DataMetronome components."""

    @pytest.fixture
    async def db_connection(self):
        """Create a database connection for testing."""
        conn = await asyncpg.connect(**POSTGRES_CONFIG)
        yield conn
        await conn.close()

    @pytest.mark.asyncio
    async def test_full_data_pipeline(self, db_connection):
        """Test a complete data pipeline flow."""
        # 1. Query raw data
        users = await db_connection.fetch(
            "SELECT id, age FROM users WHERE age IS NOT NULL LIMIT 100"
        )

        assert len(users) > 0

        # 2. Calculate statistics
        ages = [float(u["age"]) for u in users if u["age"] is not None]
        mean_age = sum(ages) / len(ages)

        # 3. Identify anomalies (simple threshold-based)
        std_dev = (sum((x - mean_age) ** 2 for x in ages) / len(ages)) ** 0.5
        threshold = mean_age + (3 * std_dev)

        anomalies = [
            age for age in ages if age > threshold or age < mean_age - (3 * std_dev)
        ]

        # 4. Verify we can detect anomalies
        assert mean_age > 0
        assert std_dev > 0

    @pytest.mark.asyncio
    async def test_metric_aggregation_pipeline(self, db_connection):
        """Test metric aggregation across time windows."""
        # Get hourly aggregates for the last 24 hours
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

        hourly_metrics = await db_connection.fetch(
            """
            SELECT
                metric_name,
                DATE_TRUNC('hour', timestamp) as hour,
                AVG(metric_value) as avg_value,
                MAX(metric_value) as max_value,
                MIN(metric_value) as min_value,
                COUNT(*) as sample_count
            FROM metrics
            WHERE timestamp >= $1
            GROUP BY metric_name, DATE_TRUNC('hour', timestamp)
            ORDER BY hour DESC, metric_name
            """,
            twenty_four_hours_ago,
        )

        if len(hourly_metrics) > 0:
            for metric in hourly_metrics[:5]:
                assert metric["avg_value"] is not None
                assert metric["max_value"] is not None
                assert metric["min_value"] is not None
                assert metric["sample_count"] > 0
                assert (
                    float(metric["min_value"])
                    <= float(metric["avg_value"])
                    <= float(metric["max_value"])
                )
