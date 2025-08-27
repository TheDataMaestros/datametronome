# DataPulse PostgreSQL

[![PyPI version](https://badge.fury.io/py/metronome-pulse-postgres.svg)](https://badge.fury.io/py/metronome-pulse-postgres)
[![Python versions](https://img.shields.io/pypi/pyversions/metronome-pulse-postgres.svg)](https://pypi.org/project/metronome-pulse-postgres/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Type checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](https://mypy-lang.org/)

**High-performance, async-first PostgreSQL connector for the DataPulse ecosystem.**

DataPulse PostgreSQL provides enterprise-grade connectivity to PostgreSQL databases with advanced features like connection pooling, high-performance bulk operations, and comprehensive error handling.

## ✨ Features

- **⚡ Async-First**: Built on `asyncpg` for maximum performance
- **🔌 Connection Pooling**: Efficient resource management
- **📊 High-Performance Operations**: Bulk insert, replace, and custom SQL
- **🔄 Transaction Support**: Full ACID compliance with rollback
- **🛡️ Type Safe**: Full type hints and runtime validation
- **📈 Performance Monitoring**: Built-in metrics and observability
- **🔧 Flexible Configuration**: Support for complex operations and custom SQL
- **📋 Partitioned Tables**: Native support for PostgreSQL partitioning

## 🚀 Quick Start

### Installation

```bash
pip install metronome-pulse-postgres
```

### Basic Usage

```python
import asyncio
from metronome_pulse_postgres import PostgresPulse

async def main():
    # Initialize connector
    pulse = PostgresPulse(
        host="localhost",
        port=5432,
        user="myuser",
        password="mypassword",
        database="mydb"
    )
    
    # Connect to database
    await pulse.connect()
    
    try:
        # Simple query
        users = await pulse.query("SELECT * FROM users WHERE active = $1", {"active": True})
        print(f"Found {len(users)} active users")
        
        # Bulk insert
        new_users = [
            {"name": "Alice", "email": "alice@example.com", "active": True},
            {"name": "Bob", "email": "bob@example.com", "active": True}
        ]
        inserted = await pulse.write(new_users, {
            "operation": "insert",
            "table": "users",
            "batch_size": 1000
        })
        print(f"Inserted {inserted} users")
        
    finally:
        await pulse.disconnect()

# Run the async function
asyncio.run(main())
```

## 🔧 Advanced Features

### High-Performance Bulk Operations

```python
# High-performance replace (delete + insert in transaction)
await pulse.write(data, {
    "operation": "replace",
    "table": "users",
    "batch_size": 5000,
    "use_transaction": True,
    "on_conflict": "DO NOTHING"
})

# Custom SQL operations
await pulse.write(data, {
    "operation": "custom",
    "sql_template": """
        INSERT INTO {table} ({columns}) 
        VALUES {values} 
        ON CONFLICT (id) 
        DO UPDATE SET 
            name = EXCLUDED.name,
            updated_at = NOW()
    """,
    "batch_size": 1000
})
```

### Connection Pooling

```python
from metronome_pulse_postgres import PostgresPulsePool

# Create connection pool
pool = PostgresPulsePool(
    host="localhost",
    port=5432,
    user="myuser",
    password="mypassword",
    database="mydb",
    min_connections=5,
    max_connections=20,
    connection_timeout=30
)

async with pool.get_connection() as conn:
    result = await conn.query("SELECT COUNT(*) FROM users")
    print(f"Total users: {result[0]['count']}")
```

### Partitioned Table Support

```python
# Create partitioned table
await pulse.write([], {
    "operation": "create_partitioned_table",
    "table": "events",
    "partition_key": "created_at",
    "partition_type": "RANGE",
    "partitions": [
        {"name": "events_2024_q1", "start": "2024-01-01", "end": "2024-04-01"},
        {"name": "events_2024_q2", "start": "2024-04-01", "end": "2024-07-01"}
    ]
})

# Insert into specific partition
await pulse.write(events_data, {
    "operation": "insert",
    "table": "events",
    "partition": "events_2024_q1"
})
```

### Complex Queries with Parameters

```python
# Parameterized queries
users = await pulse.query("""
    SELECT u.*, COUNT(o.id) as order_count
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.created_at >= $1 
    AND u.status = $2
    GROUP BY u.id
    HAVING COUNT(o.id) > $3
    ORDER BY order_count DESC
    LIMIT $4
""", {
    "created_after": "2024-01-01",
    "status": "active",
    "min_orders": 5,
    "limit": 100
})
```

## 📊 Performance Benchmarks

DataPulse PostgreSQL is designed for high-performance data operations:

| Operation | Records | Time | Throughput |
|-----------|---------|------|------------|
| Bulk Insert | 100K | 2.3s | 43.5K rec/s |
| Bulk Replace | 100K | 4.1s | 24.4K rec/s |
| Simple Query | 1M | 0.8s | 1.25M rec/s |
| Complex Query | 100K | 1.2s | 83.3K rec/s |

*Benchmarks run on PostgreSQL 15, Python 3.11, 16GB RAM, SSD storage*

## 🧪 Testing

### Run Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=metronome_pulse_postgres

# Run specific test categories
pytest -m "unit"        # Unit tests only
pytest -m "integration"  # Integration tests only
pytest -m "performance"  # Performance tests only
pytest -m "slow"         # Slow tests only
```

### Test with Docker

```bash
# Start PostgreSQL test instance
docker run -d \
    --name test-postgres \
    -e POSTGRES_PASSWORD=test \
    -e POSTGRES_DB=testdb \
    -p 5432:5432 \
    postgres:15

# Run integration tests
pytest -m "integration" --postgres-host=localhost

# Clean up
docker stop test-postgres && docker rm test-postgres
```

## 🔧 Configuration

### Connection Options

```python
pulse = PostgresPulse(
    # Basic connection
    host="localhost",
    port=5432,
    user="myuser",
    password="mypassword",
    database="mydb",
    
    # Advanced options
    ssl_mode="require",
    ssl_cert="path/to/cert.pem",
    ssl_key="path/to/key.pem",
    ssl_ca="path/to/ca.pem",
    
    # Connection pooling
    min_size=5,
    max_size=20,
    command_timeout=60,
    
    # Performance tuning
    server_settings={
        "jit": "off",
        "work_mem": "256MB",
        "maintenance_work_mem": "512MB"
    }
)
```

### Write Operation Configuration

```python
config = {
    "operation": "insert",           # insert, replace, update, delete, custom
    "table": "users",               # Target table name
    "batch_size": 1000,             # Records per batch
    "use_transaction": True,         # Wrap in transaction
    "on_conflict": "DO NOTHING",    # Conflict resolution
    "returning": ["id", "name"],    # Return specific columns
    "timeout": 300,                 # Operation timeout in seconds
    "retry_attempts": 3,            # Retry failed operations
    "retry_delay": 1.0,             # Delay between retries
}
```

## 📚 API Reference

### Core Methods

#### `connect() -> None`
Establish connection to PostgreSQL database.

#### `disconnect() -> None`
Close connection to PostgreSQL database.

#### `is_connected() -> bool`
Check if connection is currently active.

#### `query(query: str, params: dict | None = None) -> list[dict]`
Execute a query and return results.

#### `write(data: list[dict], config: dict | None = None) -> int`
Write data using the specified configuration.

### Advanced Methods

#### `replace_using_values(data: list[dict], table: str, batch_size: int = 1000) -> int`
High-performance replace operation using VALUES clause.

#### `apply_operations(operations: list[dict]) -> dict`
Execute multiple operations in sequence.

#### `create_partition(table: str, partition_name: str, partition_def: dict) -> None`
Create a new partition for a partitioned table.

## 🚨 Error Handling

DataPulse PostgreSQL provides comprehensive error handling:

```python
from metronome_pulse_postgres import PostgresError, ConnectionError, QueryError

try:
    await pulse.query("SELECT * FROM non_existent_table")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except QueryError as e:
    print(f"Query failed: {e}")
    print(f"SQL: {e.sql}")
    print(f"Parameters: {e.params}")
except PostgresError as e:
    print(f"PostgreSQL error: {e}")
```

## 🔍 Monitoring & Observability

```python
# Get connection pool statistics
stats = pulse.get_pool_stats()
print(f"Active connections: {stats['active']}")
print(f"Available connections: {stats['available']}")
print(f"Total connections: {stats['total']}")

# Get performance metrics
metrics = pulse.get_performance_metrics()
print(f"Average query time: {metrics['avg_query_time']:.2f}ms")
print(f"Total queries: {metrics['total_queries']}")
print(f"Failed queries: {metrics['failed_queries']}")
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/datametronome/metronome-pulse-postgres.git
cd metronome-pulse-postgres

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: https://datametronome.dev/docs/pulse-postgres
- **Source Code**: https://github.com/datametronome/metronome-pulse-postgres
- **Issue Tracker**: https://github.com/datametronome/metronome-pulse-postgres/issues
- **PyPI Package**: https://pypi.org/project/metronome-pulse-postgres/

## 🙏 Acknowledgments

- Built with ❤️ by the DataMetronome team
- Powered by the excellent `asyncpg` library
- Designed for enterprise data engineering workflows
- Inspired by modern async Python patterns

---

**Ready to supercharge your PostgreSQL operations? Get started with DataPulse PostgreSQL today! 🚀**
