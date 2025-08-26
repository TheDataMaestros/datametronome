# metronome-pulse-postgres-sqlalchemy

Flexible PostgreSQL DataPulse connector using SQLAlchemy with full ORM support.

## 🚀 **Standalone Usage**

This package provides a flexible, ORM-capable PostgreSQL connector that can be used independently of the DataMetronome project. Built on SQLAlchemy for maximum flexibility and ORM features.

### **Installation**

```bash
pip install metronome-pulse-postgres-sqlalchemy
```

### **Quick Start**

```python
import asyncio
from metronome_pulse_postgres_sqlalchemy import PostgresSQLAlchemyPulse

async def main():
    # Configure your PostgreSQL connection
    credentials = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "your_password",
        "database": "your_database"
    }
    
    # Optional engine configuration
    engine_config = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "echo": False
    }
    
    # Use as async context manager (recommended)
    async with PostgresSQLAlchemyPulse(credentials, engine_config) as pulse:
        # Query data with SQL string
        results = await pulse.query("SELECT * FROM users WHERE active = true")
        print(f"Found {len(results)} active users")
        
        # Query with structured configuration
        query_config = {
            "sql": "SELECT * FROM users WHERE age > :min_age AND city = :city",
            "params": {"min_age": 18, "city": "New York"}
        }
        results = await pulse.query(query_config)
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
    pulse = PostgresSQLAlchemyPulse(credentials)
    
    try:
        await pulse.connect()
        
        # Your operations here
        results = await pulse.query("SELECT COUNT(*) FROM users")
        print(f"Total users: {results[0]['count']}")
        
    finally:
        await pulse.close()
```

## 📋 **Features**

- **Full SQLAlchemy Support**: Access to all SQLAlchemy features and ORM capabilities
- **Flexible Query Interface**: Support for both SQL strings and structured query configs
- **Connection Pooling**: Configurable pool with automatic management
- **Async-First**: Full async/await support with SQLAlchemy async engine
- **Type Safety**: Modern Python type hints
- **Table Metadata**: Built-in table inspection capabilities
- **Transaction Support**: Full transaction management

## 🔧 **Configuration Options**

### **Connection Parameters**
- `host`: Database host (default: localhost)
- `port`: Database port (default: 5432)
- `user`: Database username
- `password`: Database password
- `database`: Database name

### **Engine Configuration**
- `pool_size`: Pool size (default: 10)
- `max_overflow`: Maximum overflow connections (default: 20)
- `pool_pre_ping`: Pre-ping connections (default: True)
- `pool_recycle`: Connection recycle time (default: 3600)
- `echo`: SQL logging (default: False)

## 📖 **API Reference**

### **Core Methods**
- `connect()`: Initialize SQLAlchemy engine
- `close()`: Close engine and release resources
- `query(query_config)`: Execute query (supports string or dict)
- `write(data, destination)`: Write data to table
- `execute(query, params)`: Execute non-query SQL
- `execute_many(query, params_list)`: Execute batch operations

### **Utility Methods**
- `query_with_params(query, params)`: Parameterized queries
- `get_table_info(table_name)`: Get detailed table metadata
- `is_connected`: Check connection status
- `engine`: Access to SQLAlchemy engine
- `session_maker`: Access to session maker

## 🔗 **Integration with DataMetronome**

While this package is designed for standalone use, it's also a DataPulse connector for the DataMetronome ecosystem. It implements the standard DataPulse interfaces for consistent behavior.

## 📚 **Documentation**

- [API Reference](https://datametronome.dev/docs/pulse-postgres-sqlalchemy)
- [Contributing Guide](https://github.com/datametronome/metronome-pulse-postgres-sqlalchemy/blob/main/CONTRIBUTING.md)
- [Examples](https://github.com/datametronome/metronome-pulse-postgres-sqlalchemy/tree/main/examples)

## 📄 **License**

MIT License - see [LICENSE](LICENSE) file for details.




