"""
Integration tests for DataMetronome Podium that require a real database.
These tests focus on database operations, partitioning, and real data scenarios.
"""

import pytest
import asyncio
import asyncpg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDatabasePartitioningIntegration:
    """Integration tests for database partitioning functionality."""
    
    @pytest.fixture
    async def partitioned_database(self):
        """Setup a test database with partitioned tables."""
        # Database connection parameters
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5433)),  # Use test port
            'database': os.getenv('POSTGRES_DB', 'testdb'),
            'user': os.getenv('POSTGRES_USER', 'testuser'),
            'password': os.getenv('POSTGRES_PASSWORD', 'testpass'),
        }
        
        # Connect to database
        conn = await asyncpg.connect(**db_config)
        
        # Create partitioned tables
        await self._setup_partitioned_tables(conn)
        
        yield conn
        
        # Cleanup
        await self._cleanup_partitioned_tables(conn)
        await conn.close()
    
    async def _setup_partitioned_tables(self, conn):
        """Setup partitioned tables for testing."""
        # Create partitioned table by date (daily partitions)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS partitioned_events (
                id SERIAL,
                event_type VARCHAR(50) NOT NULL,
                event_data JSONB,
                created_at TIMESTAMP NOT NULL,
                user_id INTEGER,
                metadata JSONB
            ) PARTITION BY RANGE (created_at)
        """)
        
        # Create daily partitions for the last 30 days
        base_date = datetime.now() - timedelta(days=30)
        for i in range(30):
            partition_date = base_date + timedelta(days=i)
            partition_name = f"partitioned_events_{partition_date.strftime('%Y%m%d')}"
            start_date = partition_date
            end_date = partition_date + timedelta(days=1)
            
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} 
                PARTITION OF partitioned_events
                FOR VALUES FROM ('{start_date.isoformat()}') 
                TO ('{end_date.isoformat()}')
            """)
        
        # Create partitioned table by user_id (hash partitions)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS partitioned_users (
                id SERIAL,
                username VARCHAR(50) NOT NULL,
                email VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_type VARCHAR(20),
                profile_data JSONB
            ) PARTITION BY HASH (id)
        """)
        
        # Create hash partitions
        for i in range(4):  # 4 hash partitions
            partition_name = f"partitioned_users_hash_{i}"
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} 
                PARTITION OF partitioned_users
                FOR VALUES WITH (modulus 4, remainder {i})
            """)
        
        # Create partitioned table by month (monthly partitions)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS partitioned_metrics (
                id SERIAL,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DECIMAL(15,4) NOT NULL,
                recorded_at TIMESTAMP NOT NULL,
                source VARCHAR(100),
                tags JSONB
            ) PARTITION BY RANGE (recorded_at)
        """)
        
        # Create monthly partitions for the last 12 months
        base_month = datetime.now().replace(day=1) - timedelta(days=365)
        for i in range(12):
            partition_date = base_month + timedelta(days=i*30)
            partition_name = f"partitioned_metrics_{partition_date.strftime('%Y%m')}"
            start_date = partition_date
            end_date = partition_date + timedelta(days=30)
            
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} 
                PARTITION OF partitioned_metrics
                FOR VALUES FROM ('{start_date.isoformat()}') 
                TO ('{end_date.isoformat()}')
            """)
        
        # Create indexes on partitioned tables
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_partitioned_events_created_at ON partitioned_events(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_partitioned_events_user_id ON partitioned_events(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_partitioned_users_username ON partitioned_users(username)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_partitioned_metrics_recorded_at ON partitioned_metrics(recorded_at)")
    
    async def _cleanup_partitioned_tables(self, conn):
        """Clean up partitioned tables."""
        # Drop partitioned tables (this will drop all partitions)
        await conn.execute("DROP TABLE IF EXISTS partitioned_events CASCADE")
        await conn.execute("DROP TABLE IF EXISTS partitioned_users CASCADE")
        await conn.execute("DROP TABLE IF EXISTS partitioned_metrics CASCADE")
    
    @pytest.mark.asyncio
    async def test_daily_partition_insertion(self, partitioned_database):
        """Test inserting data into daily partitions."""
        logger.info("Testing daily partition insertion...")
        
        # Insert data across different days
        test_data = []
        base_date = datetime.now() - timedelta(days=15)
        
        for i in range(100):
            event_date = base_date + timedelta(days=i % 15)
            test_data.append((
                f"event_type_{i % 5}",
                json.dumps({"event_id": i, "data": f"test_data_{i}"}),
                event_date,
                i % 100,
                json.dumps({"source": "test", "version": "1.0"})
            ))
        
        # Insert data
        await partitioned_database.executemany("""
            INSERT INTO partitioned_events (event_type, event_data, created_at, user_id, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, test_data)
        
        # Verify data was inserted into correct partitions
        for i in range(15):
            check_date = base_date + timedelta(days=i)
            partition_name = f"partitioned_events_{check_date.strftime('%Y%m%d')}"
            
            # Check if partition exists and has data
            partition_exists = await partitioned_database.fetchval(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = '{partition_name}'
                )
            """)
            assert partition_exists is True
            
            # Count rows in partition
            row_count = await partitioned_database.fetchval(f"""
                SELECT COUNT(*) FROM {partition_name}
            """)
            assert row_count >= 0
        
        logger.info("Daily partition insertion test completed successfully!")
    
    @pytest.mark.asyncio
    async def test_hash_partition_distribution(self, partitioned_database):
        """Test hash partition distribution and data retrieval."""
        logger.info("Testing hash partition distribution...")
        
        # Insert users across hash partitions
        test_users = []
        for i in range(100):
            test_users.append((
                f"user_{i:03d}",
                f"user_{i:03d}@example.com",
                datetime.now() - timedelta(days=i),
                f"type_{i % 3}",
                json.dumps({"profile_id": i, "preferences": {"theme": "dark"}})
            ))
        
        await partitioned_database.executemany("""
            INSERT INTO partitioned_users (username, email, created_at, user_type, profile_data)
            VALUES ($1, $2, $3, $4, $5)
        """, test_users)
        
        # Check distribution across hash partitions
        partition_counts = {}
        for i in range(4):
            partition_name = f"partitioned_users_hash_{i}"
            count = await partitioned_database.fetchval(f"SELECT COUNT(*) FROM {partition_name}")
            partition_counts[f"hash_{i}"] = count
            logger.info(f"Partition {partition_name}: {count} rows")
        
        # Verify data is distributed (should not be empty)
        total_rows = sum(partition_counts.values())
        assert total_rows == 100
        
        # Each partition should have some data (hash distribution)
        for count in partition_counts.values():
            assert count > 0
        
        # Test cross-partition queries
        all_users = await partitioned_database.fetch("""
            SELECT username, email FROM partitioned_users 
            WHERE user_type = 'type_0' 
            ORDER BY username
        """)
        
        assert len(all_users) > 0
        assert all_users[0]['username'].startswith('user_')
        
        logger.info("Hash partition distribution test completed successfully!")
    
    @pytest.mark.asyncio
    async def test_monthly_partition_operations(self, partitioned_database):
        """Test monthly partition operations and maintenance."""
        logger.info("Testing monthly partition operations...")
        
        # Insert metrics data across months
        test_metrics = []
        base_month = datetime.now().replace(day=1) - timedelta(days=180)
        
        for i in range(1000):
            metric_date = base_month + timedelta(days=i % 180)
            test_metrics.append((
                f"metric_{i % 10}",
                round(np.random.uniform(10, 1000), 4),
                metric_date,
                f"source_{i % 5}",
                json.dumps({"tags": {"environment": "test", "version": "1.0"}})
            ))
        
        await partitioned_database.executemany("""
            INSERT INTO partitioned_metrics (metric_name, metric_value, recorded_at, source, tags)
            VALUES ($1, $2, $3, $4, $5)
        """, test_metrics)
        
        # Test partition pruning in queries
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        # This query should only scan relevant partitions
        recent_metrics = await partitioned_database.fetch("""
            SELECT metric_name, AVG(metric_value) as avg_value, COUNT(*) as count
            FROM partitioned_metrics 
            WHERE recorded_at >= $1 AND recorded_at < $2
            GROUP BY metric_name
            ORDER BY metric_name
        """, start_date, end_date)
        
        assert len(recent_metrics) > 0
        
        # Test partition maintenance operations
        # 1. Check partition sizes
        partition_sizes = await partitioned_database.fetch("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE tablename LIKE 'partitioned_metrics_%'
            ORDER BY tablename
        """)
        
        assert len(partition_sizes) > 0
        
        # 2. Test partition statistics
        partition_stats = await partitioned_database.fetch("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes
            FROM pg_stat_user_tables 
            WHERE tablename LIKE 'partitioned_metrics_%'
            ORDER BY tablename
        """)
        
        assert len(partition_stats) > 0
        
        logger.info("Monthly partition operations test completed successfully!")
    
    @pytest.mark.asyncio
    async def test_partition_performance_queries(self, partitioned_database):
        """Test query performance with partitioned tables."""
        logger.info("Testing partition performance queries...")
        
        # Insert large amount of data for performance testing
        large_dataset = []
        base_date = datetime.now() - timedelta(days=90)
        
        for i in range(10000):
            event_date = base_date + timedelta(hours=i % (90 * 24))
            large_dataset.append((
                f"event_type_{i % 10}",
                json.dumps({"event_id": i, "data": f"large_dataset_{i}"}),
                event_date,
                i % 1000,
                json.dumps({"batch": i // 1000, "source": "performance_test"})
            ))
        
        # Insert in batches for better performance
        batch_size = 1000
        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i:i + batch_size]
            await partitioned_database.executemany("""
                INSERT INTO partitioned_events (event_type, event_data, created_at, user_id, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, batch)
        
        # Test query performance with partition pruning
        import time
        
        # Query 1: Date range query (should use partition pruning)
        start_time = time.time()
        recent_events = await partitioned_database.fetch("""
            SELECT COUNT(*) as count, event_type
            FROM partitioned_events 
            WHERE created_at >= $1 AND created_at < $2
            GROUP BY event_type
            ORDER BY count DESC
        """, datetime.now() - timedelta(days=7), datetime.now())
        
        query1_time = time.time() - start_time
        logger.info(f"Date range query completed in {query1_time:.4f} seconds")
        assert len(recent_events) > 0
        
        # Query 2: Cross-partition aggregation
        start_time = time.time()
        user_activity = await partitioned_database.fetch("""
            SELECT 
                user_id,
                COUNT(*) as event_count,
                COUNT(DISTINCT event_type) as event_types,
                MIN(created_at) as first_event,
                MAX(created_at) as last_event
            FROM partitioned_events 
            WHERE user_id < 100
            GROUP BY user_id
            ORDER BY event_count DESC
            LIMIT 20
        """)
        
        query2_time = time.time() - start_time
        logger.info(f"Cross-partition aggregation completed in {query2_time:.4f} seconds")
        assert len(user_activity) > 0
        
        # Query 3: Complex join with partitioned table
        start_time = time.time()
        user_metrics = await partitioned_database.fetch("""
            WITH user_events AS (
                SELECT 
                    user_id,
                    COUNT(*) as total_events,
                    COUNT(DISTINCT event_type) as unique_event_types
                FROM partitioned_events 
                WHERE created_at >= $1
                GROUP BY user_id
            )
            SELECT 
                ue.user_id,
                ue.total_events,
                ue.unique_event_types,
                pu.username,
                pu.user_type
            FROM user_events ue
            JOIN partitioned_users pu ON ue.user_id = pu.id
            WHERE ue.total_events > 10
            ORDER BY ue.total_events DESC
            LIMIT 10
        """, datetime.now() - timedelta(days=30))
        
        query3_time = time.time() - start_time
        logger.info(f"Complex join query completed in {query3_time:.4f} seconds")
        
        # Performance assertions
        assert query1_time < 1.0  # Date range should be fast with partition pruning
        assert query2_time < 2.0  # Cross-partition aggregation should be reasonable
        assert query3_time < 3.0  # Complex join should complete within reasonable time
        
        logger.info("Partition performance queries test completed successfully!")
    
    @pytest.mark.asyncio
    async def test_partition_maintenance_operations(self, partitioned_database):
        """Test partition maintenance and administrative operations."""
        logger.info("Testing partition maintenance operations...")
        
        # Test partition information queries
        partition_info = await partitioned_database.fetch("""
            SELECT 
                schemaname,
                tablename,
                tableowner,
                tablespace,
                hasindexes,
                hasrules,
                hastriggers
            FROM pg_tables 
            WHERE tablename LIKE 'partitioned_events_%'
            ORDER BY tablename
        """)
        
        assert len(partition_info) > 0
        
        # Test partition size analysis
        partition_sizes = await partitioned_database.fetch("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
            FROM pg_tables 
            WHERE tablename LIKE 'partitioned_metrics_%'
            ORDER BY tablename
        """)
        
        assert len(partition_sizes) > 0
        
        # Test partition statistics
        partition_stats = await partitioned_database.fetch("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                last_vacuum,
                last_autovacuum
            FROM pg_stat_user_tables 
            WHERE tablename LIKE 'partitioned_users_%'
            ORDER BY tablename
        """)
        
        assert len(partition_stats) > 0
        
        # Test partition cleanup (delete old data)
        old_date = datetime.now() - timedelta(days=60)
        deleted_count = await partitioned_database.execute("""
            DELETE FROM partitioned_events 
            WHERE created_at < $1
        """, old_date)
        
        logger.info(f"Deleted {deleted_count} old records")
        
        # Test partition vacuum
        for partition_name in ['partitioned_events', 'partitioned_users', 'partitioned_metrics']:
            await partitioned_database.execute(f"VACUUM ANALYZE {partition_name}")
        
        logger.info("Partition maintenance operations test completed successfully!")


class TestDatabaseOperationsIntegration:
    """Integration tests for database operations with real data."""
    
    @pytest.fixture
    async def operational_database(self):
        """Setup a test database for operational testing."""
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5433)),
            'database': os.getenv('POSTGRES_DB', 'testdb'),
            'user': os.getenv('POSTGRES_USER', 'testuser'),
            'password': os.getenv('POSTGRES_PASSWORD', 'testpass'),
        }
        
        conn = await asyncpg.connect(**db_config)
        
        # Create operational tables
        await self._setup_operational_tables(conn)
        
        yield conn
        
        # Cleanup
        await self._cleanup_operational_tables(conn)
        await conn.close()
    
    async def _setup_operational_tables(self, conn):
        """Setup tables for operational testing."""
        # Create tables with constraints and triggers
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS operational_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                CONSTRAINT chk_username_length CHECK (length(username) >= 3),
                CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS operational_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES operational_users(id) ON DELETE CASCADE,
                order_number VARCHAR(20) UNIQUE NOT NULL,
                order_amount DECIMAL(10,2) NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                CONSTRAINT chk_order_amount CHECK (order_amount > 0),
                CONSTRAINT chk_order_status CHECK (status IN ('pending', 'processing', 'completed', 'cancelled'))
            )
        """)
        
        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_operational_users_email ON operational_users(email)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_operational_orders_user_id ON operational_orders(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_operational_orders_status ON operational_orders(status)")
        
        # Create update trigger
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        await conn.execute("""
            CREATE TRIGGER update_operational_users_updated_at 
                BEFORE UPDATE ON operational_users 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
    
    async def _cleanup_operational_tables(self, conn):
        """Clean up operational tables."""
        await conn.execute("DROP TABLE IF EXISTS operational_orders CASCADE")
        await conn.execute("DROP TABLE IF EXISTS operational_users CASCADE")
        await conn.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
    
    @pytest.mark.asyncio
    async def test_crud_operations(self, operational_database):
        """Test Create, Read, Update, Delete operations."""
        logger.info("Testing CRUD operations...")
        
        # Create users
        user_data = [
            ("user1", "user1@example.com"),
            ("user2", "user2@example.com"),
            ("user3", "user3@example.com")
        ]
        
        user_ids = []
        for username, email in user_data:
            user_id = await operational_database.fetchval("""
                INSERT INTO operational_users (username, email) 
                VALUES ($1, $2) RETURNING id
            """, username, email)
            user_ids.append(user_id)
        
        assert len(user_ids) == 3
        
        # Read users
        users = await operational_database.fetch("""
            SELECT id, username, email, created_at, updated_at, is_active 
            FROM operational_users 
            ORDER BY username
        """)
        
        assert len(users) == 3
        assert users[0]['username'] == 'user1'
        assert users[0]['is_active'] is True
        
        # Update user
        await operational_database.execute("""
            UPDATE operational_users 
            SET email = 'updated@example.com', is_active = FALSE 
            WHERE username = 'user1'
        """)
        
        updated_user = await operational_database.fetchrow("""
            SELECT * FROM operational_users WHERE username = 'user1'
        """)
        
        assert updated_user['email'] == 'updated@example.com'
        assert updated_user['is_active'] is False
        assert updated_user['updated_at'] > updated_user['created_at']
        
        # Delete user
        await operational_database.execute("""
            DELETE FROM operational_users WHERE username = 'user2'
        """)
        
        remaining_users = await operational_database.fetch("""
            SELECT username FROM operational_users ORDER BY username
        """)
        
        assert len(remaining_users) == 2
        usernames = [user['username'] for user in remaining_users]
        assert 'user1' in usernames
        assert 'user3' in usernames
        assert 'user2' not in usernames
        
        logger.info("CRUD operations test completed successfully!")
    
    @pytest.mark.asyncio
    async def test_transaction_operations(self, operational_database):
        """Test database transaction operations."""
        logger.info("Testing transaction operations...")
        
        # Test successful transaction
        async with operational_database.transaction():
            # Insert user
            user_id = await operational_database.fetchval("""
                INSERT INTO operational_users (username, email) 
                VALUES ($1, $2) RETURNING id
            """, "transaction_user", "transaction@example.com")
            
            # Insert order
            order_id = await operational_database.fetchval("""
                INSERT INTO operational_orders (user_id, order_number, order_amount) 
                VALUES ($1, $2, $3) RETURNING id
            """, user_id, "ORD-001", 100.00)
            
            # Verify both were created
            user_exists = await operational_database.fetchval("""
                SELECT EXISTS(SELECT 1 FROM operational_users WHERE id = $1)
            """, user_id)
            
            order_exists = await operational_database.fetchval("""
                SELECT EXISTS(SELECT 1 FROM operational_orders WHERE id = $1)
            """, order_id)
            
            assert user_exists is True
            assert order_exists is True
        
        # Test failed transaction (rollback)
        try:
            async with operational_database.transaction():
                # Insert user
                user_id = await operational_database.fetchval("""
                    INSERT INTO operational_users (username, email) 
                    VALUES ($1, $2) RETURNING id
                """, "rollback_user", "rollback@example.com")
                
                # This will fail due to constraint violation
                await operational_database.execute("""
                    INSERT INTO operational_orders (user_id, order_number, order_amount) 
                    VALUES ($1, $2, $3)
                """, user_id, "ORD-002", -50.00)  # Negative amount violates constraint
                
        except Exception:
            # Transaction should have rolled back
            pass
        
        # Verify user was not created (rollback worked)
        user_exists = await operational_database.fetchval("""
            SELECT EXISTS(SELECT 1 FROM operational_users WHERE username = 'rollback_user')
        """)
        
        assert user_exists is False
        
        logger.info("Transaction operations test completed successfully!")
    
    @pytest.mark.asyncio
    async def test_constraint_violations(self, operational_database):
        """Test database constraint violations and error handling."""
        logger.info("Testing constraint violations...")
        
        # Test unique constraint violation
        await operational_database.execute("""
            INSERT INTO operational_users (username, email) 
            VALUES ($1, $2)
        """, "constraint_user", "constraint@example.com")
        
        # Try to insert duplicate username
        with pytest.raises(asyncpg.UniqueViolationError):
            await operational_database.execute("""
                INSERT INTO operational_users (username, email) 
                VALUES ($1, $2)
            """, "constraint_user", "different@example.com")
        
        # Try to insert duplicate email
        with pytest.raises(asyncpg.UniqueViolationError):
            await operational_database.execute("""
                INSERT INTO operational_users (username, email) 
                VALUES ($1, $2)
            """, "different_user", "constraint@example.com")
        
        # Test check constraint violation
        with pytest.raises(asyncpg.CheckViolationError):
            await operational_database.execute("""
                INSERT INTO operational_users (username, email) 
                VALUES ($1, $2)
            """, "ab", "short@example.com")  # Username too short
        
        # Test email format constraint
        with pytest.raises(asyncpg.CheckViolationError):
            await operational_database.execute("""
                INSERT INTO operational_users (username, email) 
                VALUES ($1, $2)
            """, "invalid_email", "invalid-email")  # Invalid email format
        
        # Test foreign key constraint
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await operational_database.execute("""
                INSERT INTO operational_orders (user_id, order_number, order_amount) 
                VALUES ($1, $2, $3)
            """, 99999, "ORD-003", 100.00)  # Non-existent user_id
        
        logger.info("Constraint violations test completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__])
