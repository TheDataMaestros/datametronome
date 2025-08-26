# metronome-pulse-postgres-psycopg3

Modern PostgreSQL DataPulse connector using psycopg3 with async support.

## 🚀 **Standalone Usage**

This package provides a modern, async-first PostgreSQL connector that can be used independently of the DataMetronome project. Built on psycopg3 for maximum compatibility and performance.

### **Installation**

```bash
pip install metronome-pulse-postgres-psycopg3
```

### **Quick Start**

```python
import asyncio
from metronome_pulse_postgres_psycopg3 import PostgresPsycopg3Pulse

async def main():
    # Configure your PostgreSQL connection
    credentials = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "your_password",
        "database": "your_database"
    }
    
    # Optional pool configuration
    pool_config = {
        "min_size": 5,
        "max_size": 20,
        "timeout": 30,
        "check": True
    }
    
    # Use as async context manager (recommended)
    async with PostgresPsycopg3Pulse(credentials, pool_config) as pulse:
        # Query data
        results = await pulse.query("SELECT * FROM users WHERE active = true")
        print(f"Found {len(results)} active users")
        
        # Parameterized query
        results = await pulse.query_with_params(
            "SELECT * FROM users WHERE age > %s AND city = %s",
            {"age": 18, "city": "New York"}
        )
        print(f"Found {len(results)} users in New York over 18")
        
        # Write data
        new_users = [
            {"name": "Alice", "email": "alice@example.com", "age": 25},
            {"name": "Bob", "email": "bob@example.com", "age": 30}
        ]
        await pulse.write(new_users, "users")
        print("Added new users")
        
        # Get table information
        table_info = await pulse.get_table_info("users")
        print(f"Table structure: {table_info}")

# Run the example
asyncio.run(main())
```

### **Manual Lifecycle Management**

```python
async def manual_example():
    pulse = PostgresPsycopg3Pulse(credentials)
    
    try:
        await pulse.connect()
        
        # Your operations here
        results = await pulse.query("SELECT COUNT(*) FROM users")
        print(f"Total users: {results[0]['count']}")
        
    finally:
        await pulse.close()
```

## 📋 **Features**

- **Modern psycopg3**: Latest PostgreSQL driver with async support
- **Connection Pooling**: Configurable pool with automatic management
- **Async-First**: Full async/await support
- **Type Safety**: Modern Python type hints
- **Flexible Queries**: Support for parameterized queries
- **Bulk Operations**: Efficient batch inserts and updates
- **Table Metadata**: Built-in table inspection capabilities

## 🔧 **Configuration Options**

### **Connection Parameters**
- `host`: Database host (default: localhost)
- `port`: Database port (default: 5432)
- `user`: Database username
- `password`: Database password
- `database`: Database name

### **Pool Configuration**
- `min_size`: Minimum pool size (default: 1)
- `max_size`: Maximum pool size (default: 10)
- `timeout`: Connection timeout in seconds (default: 30)
- `check`: Validate connections (default: True)

## 📖 **API Reference**

### **Core Methods**
- `connect()`: Initialize connection pool
- `close()`: Close connection pool
- `query(query_config)`: Execute SQL query
- `write(data, destination)`: Write data to table
- `execute(query, params)`: Execute non-query SQL
- `execute_many(query, params_list)`: Execute batch operations

### **Utility Methods**
- `query_with_params(query, params)`: Parameterized queries
- `get_table_info(table_name)`: Get table metadata
- `is_connected`: Check connection status
- `pool_size`: Get current pool size

## 🔗 **Integration with DataMetronome**

While this package is designed for standalone use, it's also a DataPulse connector for the DataMetronome ecosystem. It implements the standard DataPulse interfaces for consistent behavior.

## 📚 **Documentation**

- [API Reference](https://datametronome.dev/docs/pulse-postgres-psycopg3)
- [Contributing Guide](https://github.com/datametronome/metronome-pulse-postgres-psycopg3/blob/main/CONTRIBUTING.md)
- [Examples](https://github.com/datametronome/metronome-pulse-postgres-psycopg3/tree/main/examples)

## 📄 **License**

MIT License - see [LICENSE](LICENSE) file for details.




