#!/usr/bin/env python3
"""
Dynamic DataPulse Usage Examples

This file demonstrates the dynamic capabilities of all DataPulse connectors,
showing how to use the flexible write() and query() methods with different
configuration types.
"""

import asyncio
import json

# Example data
SAMPLE_USERS = [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25},
    {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35},
]

SAMPLE_EVENTS = [
    {"id": 1, "user_id": 1, "event_type": "login", "timestamp": "2025-01-01 10:00:00"},
    {"id": 2, "user_id": 2, "event_type": "purchase", "timestamp": "2025-01-01 11:00:00"},
    {"id": 3, "user_id": 1, "event_type": "logout", "timestamp": "2025-01-01 12:00:00"},
]


async def demonstrate_dynamic_write(pulse) -> None:
    """Demonstrate dynamic write capabilities."""
    print(f"\n=== Dynamic Write Examples for {pulse.__class__.__name__} ===")
    
    # 1. Simple insert (traditional way)
    print("\n1. Simple Insert:")
    await pulse.write(SAMPLE_USERS, "users")
    print("   ✓ Inserted users using simple list")
    
    # 2. Replace operation (upsert)
    print("\n2. Replace Operation (Upsert):")
    updated_users = [
        {"id": 1, "name": "Alice Updated", "email": "alice.new@example.com", "age": 31},
        {"id": 4, "name": "David", "email": "david@example.com", "age": 28},
    ]
    
    await pulse.write(
        updated_users, 
        "users",
        config={
            "type": "replace",
            "key_columns": ["id"],
            "chunk_size": 1000,
            "defer_constraints": True,
            "lock_timeout_ms": 5000,
            "statement_timeout_ms": 30000,
            "synchronous_commit_off": True
        }
    )
    print("   ✓ Replaced users using config parameter")
    
    # 3. Mixed operations
    print("\n3. Mixed Operations:")
    await pulse.write(
        [],  # No data needed for operations
        "users",
        config={
            "type": "operations",
            "operations": [
                {"type": "delete", "sql": "DELETE FROM events WHERE user_id = 999"},
                {"type": "insert", "table": "events", "rows": SAMPLE_EVENTS},
                {"type": "update", "sql": "UPDATE users SET last_login = NOW() WHERE id = 1"},
                {"type": "create_table", "sql": "CREATE TABLE IF NOT EXISTS user_sessions (id SERIAL, user_id INTEGER)"},
            ],
            "insert_chunk_size": 5000
        }
    )
    print("   ✓ Executed mixed operations using config parameter")


async def demonstrate_dynamic_query(pulse) -> None:
    """Demonstrate dynamic query capabilities."""
    print(f"\n=== Dynamic Query Examples for {pulse.__class__.__name__} ===")
    
    # 1. Simple SQL query (traditional way)
    print("\n1. Simple SQL Query:")
    results = await pulse.query("SELECT COUNT(*) as user_count FROM users")
    print(f"   ✓ Query result: {results}")
    
    # 2. Parameterized query
    print("\n2. Parameterized Query:")
    if hasattr(pulse, 'query_with_params'):
        # For asyncpg (uses $1, $2, etc.)
        if 'asyncpg' in pulse.__class__.__name__.lower():
            results = await pulse.query({
                "type": "parameterized",
                "sql": "SELECT * FROM users WHERE age > $1 AND name LIKE $2",
                "params": [25, "A%"]
            })
        # For psycopg3 (uses %s)
        elif 'psycopg' in pulse.__class__.__name__.lower():
            results = await pulse.query({
                "type": "parameterized",
                "sql": "SELECT * FROM users WHERE age > %s AND name LIKE %s",
                "params": [25, "A%"]
            })
        # For SQLAlchemy (uses :name)
        else:
            results = await pulse.query({
                "type": "parameterized",
                "sql": "SELECT * FROM users WHERE age > :age AND name LIKE :name",
                "params": {"age": 25, "name": "A%"}
            })
        print(f"   ✓ Parameterized query result: {len(results)} users found")
    
    # 3. Table info query
    print("\n3. Table Info Query:")
    try:
        table_info = await pulse.query({
            "type": "table_info",
            "table_name": "users"
        })
        print(f"   ✓ Table info: {len(table_info)} columns")
    except Exception as e:
        print(f"   ⚠ Table info not supported: {e}")
    
    # 4. Custom query with options
    print("\n4. Custom Query with Options:")
    results = await pulse.query({
        "type": "custom",
        "sql": "SELECT name, COUNT(*) as event_count FROM users u JOIN events e ON u.id = e.user_id GROUP BY u.id, u.name",
        "timeout_ms": 10000
    })
    print(f"   ✓ Custom query result: {len(results)} user event counts")


async def demonstrate_advanced_features(pulse) -> None:
    """Demonstrate advanced features like chunked operations."""
    print(f"\n=== Advanced Features for {pulse.__class__.__name__} ===")
    
    # Generate large dataset for chunking demo
    large_dataset = []
    for i in range(10000):
        large_dataset.append({
            "id": i + 1000,
            "name": f"User{i}",
            "email": f"user{i}@example.com",
            "age": 20 + (i % 50)
        })
    
    print(f"\n1. Large Dataset Chunked Replace ({len(large_dataset)} records):")
    try:
        await pulse.write(
            large_dataset,
            "users",
            config={
                "type": "replace",
                "key_columns": ["id"],
                "chunk_size": 1000,  # Process in 1000-record chunks
                "defer_constraints": True,
                "lock_timeout_ms": 10000,
                "statement_timeout_ms": 60000,
                "synchronous_commit_off": True
            }
        )
        print("   ✓ Large dataset processed in chunks")
    except Exception as e:
        print(f"   ⚠ Chunked replace failed: {e}")
    
    # Test performance tuning options
    print("\n2. Performance Tuning Options:")
    try:
        await pulse.write(
            SAMPLE_USERS[:2],
            "users",
            config={
                "type": "replace",
                "key_columns": ["id"],
                "defer_constraints": True,
                "lock_timeout_ms": 5000,
                "statement_timeout_ms": 30000,
                "synchronous_commit_off": True
            }
        )
        print("   ✓ Performance tuning options applied")
    except Exception as e:
        print(f"   ⚠ Performance tuning failed: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 DataPulse Dynamic Capabilities Demonstration")
    print("=" * 60)
    
    # Note: In a real scenario, you would import and instantiate actual connectors
    # For demonstration, we'll show the interface patterns
    
    print("\n📝 Interface Patterns:")
    print("""
    # Write Method - Multiple Ways to Use:
    
    1. Simple Insert:
       await pulse.write([{"id": 1, "name": "Alice"}], "users")
    
    2. Replace Operation (Upsert):
       await pulse.write(
           [{"id": 1, "name": "Alice Updated"}], 
           "users",
           config={
               "type": "replace",
               "key_columns": ["id"],
               "chunk_size": 5000,
               "defer_constraints": True
           }
       )
    
    3. Mixed Operations:
       await pulse.write(
           [],  # No data needed for operations
           "users",
           config={
               "type": "operations",
               "operations": [
                   {"type": "delete", "sql": "DELETE FROM users WHERE id < 0"},
                   {"type": "insert", "table": "users", "rows": [{"id": 1, "name": "Alice"}]}
               ]
           }
       )
    
    # Query Method - Multiple Ways to Use:
    
    1. Simple SQL:
       results = await pulse.query("SELECT * FROM users")
    
    2. Parameterized Query:
       results = await pulse.query({
           "type": "parameterized",
           "sql": "SELECT * FROM users WHERE age > $1",
           "params": [18]
       })
    
    3. Table Info:
       results = await pulse.query({
           "type": "table_info",
           "table_name": "users"
       })
    
    4. Custom Query with Options:
       results = await pulse.query({
           "type": "custom",
           "sql": "SELECT COUNT(*) FROM events",
           "timeout_ms": 5000
       })
    """)
    
    print("\n✨ Key Benefits:")
    print("   • Clean API - data and configuration are clearly separated")
    print("   • Backward compatible - existing code continues to work unchanged")
    print("   • Explicit and readable - obvious when using advanced features")
    print("   • Flexible configuration - choose the right approach for each use case")
    print("   • Performance tuning - control timeouts, constraints, and chunking")
    print("   • Mixed operations - combine different SQL operations in one transaction")
    
    print("\n🎯 Use Cases:")
    print("   • Simple inserts: Use data parameter only")
    print("   • Upserts: Add config with type='replace'")
    print("   • Large datasets: Use config with chunk_size")
    print("   • Complex workflows: Use config with type='operations'")
    print("   • Performance critical: Use config with tuning options")
    
    print("\n🏁 Demonstration Complete!")


if __name__ == "__main__":
    asyncio.run(main())
