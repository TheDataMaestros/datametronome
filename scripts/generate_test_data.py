#!/usr/bin/env python3
"""
Generate test data for DataMetronome integration tests.

This script creates comprehensive test data for PostgreSQL database testing,
including tables for users, orders, products, and metrics that can be used
for anomaly detection testing.
"""

import asyncio
import os
import random
import sys
from datetime import datetime, timedelta
from typing import Any

try:
    import asyncpg
except ImportError:
    print("Error: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)


async def create_connection() -> asyncpg.Connection:
    """Create a connection to the test PostgreSQL database."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    database = os.getenv("POSTGRES_DB", "testdb")
    user = os.getenv("POSTGRES_USER", "testuser")
    password = os.getenv("POSTGRES_PASSWORD", "testpass")

    print(f"Connecting to PostgreSQL at {host}:{port}/{database}...")
    
    conn = await asyncpg.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )
    
    print("✅ Connected to PostgreSQL")
    return conn


async def create_schema(conn: asyncpg.Connection) -> None:
    """Create the test database schema."""
    print("\n📋 Creating test schema...")
    
    # Drop existing tables
    await conn.execute("DROP TABLE IF EXISTS metrics CASCADE")
    await conn.execute("DROP TABLE IF EXISTS order_items CASCADE")
    await conn.execute("DROP TABLE IF EXISTS orders CASCADE")
    await conn.execute("DROP TABLE IF EXISTS products CASCADE")
    await conn.execute("DROP TABLE IF EXISTS users CASCADE")
    
    # Create users table
    await conn.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            age INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT true
        )
    """)
    
    # Create products table
    await conn.execute("""
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            category VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create orders table
    await conn.execute("""
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            total_amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create order_items table
    await conn.execute("""
        CREATE TABLE order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(id),
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL
        )
    """)
    
    # Create metrics table for anomaly detection
    await conn.execute("""
        CREATE TABLE metrics (
            id SERIAL PRIMARY KEY,
            metric_name VARCHAR(100) NOT NULL,
            metric_value DECIMAL(15, 4),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source VARCHAR(100),
            tags JSONB
        )
    """)
    
    print("✅ Schema created successfully")


async def generate_users(conn: asyncpg.Connection, count: int = 1000) -> list[int]:
    """Generate random user data."""
    print(f"\n👥 Generating {count} users...")
    
    user_ids: list[int] = []
    
    # Generate normal users
    for i in range(count):
        age = random.randint(18, 80) if random.random() > 0.05 else None  # 5% null ages
        
        # Insert some anomalies: very young or very old users
        if random.random() < 0.02:  # 2% anomalies
            age = random.choice([5, 150, -10, 999])
        
        user_id = await conn.fetchval("""
            INSERT INTO users (username, email, age, is_active)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, f"user_{i}", f"user{i}@example.com", age, random.choice([True, True, True, False]))
        
        user_ids.append(user_id)
    
    print(f"✅ Created {len(user_ids)} users")
    return user_ids


async def generate_products(conn: asyncpg.Connection, count: int = 200) -> list[int]:
    """Generate random product data."""
    print(f"\n📦 Generating {count} products...")
    
    categories = ["Electronics", "Clothing", "Books", "Food", "Toys", "Sports", "Home"]
    product_ids: list[int] = []
    
    for i in range(count):
        category = random.choice(categories)
        price = round(random.uniform(5.0, 500.0), 2)
        
        # Insert some anomalies: negative prices, extreme prices
        if random.random() < 0.02:  # 2% anomalies
            price = random.choice([-10.0, 0.0, 99999.99])
        
        stock = random.randint(0, 1000)
        
        product_id = await conn.fetchval("""
            INSERT INTO products (name, price, stock_quantity, category)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, f"Product {i} - {category}", price, stock, category)
        
        product_ids.append(product_id)
    
    print(f"✅ Created {len(product_ids)} products")
    return product_ids


async def generate_orders(
    conn: asyncpg.Connection, 
    user_ids: list[int], 
    product_ids: list[int], 
    count: int = 500
) -> list[int]:
    """Generate random order data."""
    print(f"\n🛒 Generating {count} orders...")
    
    order_ids: list[int] = []
    statuses = ["pending", "completed", "shipped", "cancelled"]
    
    # Generate orders over the past 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    for i in range(count):
        user_id = random.choice(user_ids)
        total_amount = round(random.uniform(10.0, 1000.0), 2)
        status = random.choice(statuses)
        
        # Insert some anomalies: negative amounts, extreme amounts
        if random.random() < 0.02:  # 2% anomalies
            total_amount = random.choice([-100.0, 0.0, 999999.99])
        
        # Random timestamp within the past 90 days
        random_days = random.uniform(0, 90)
        created_at = end_date - timedelta(days=random_days)
        
        order_id = await conn.fetchval("""
            INSERT INTO orders (user_id, total_amount, status, created_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, user_id, total_amount, status, created_at)
        
        order_ids.append(order_id)
        
        # Generate order items
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            product_id = random.choice(product_ids)
            quantity = random.randint(1, 10)
            price = round(random.uniform(5.0, 200.0), 2)
            
            await conn.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES ($1, $2, $3, $4)
            """, order_id, product_id, quantity, price)
    
    print(f"✅ Created {len(order_ids)} orders with items")
    return order_ids


async def generate_metrics(conn: asyncpg.Connection, count: int = 5000) -> None:
    """Generate time-series metrics for anomaly detection."""
    print(f"\n📊 Generating {count} metrics...")
    
    metric_names = [
        "cpu_usage",
        "memory_usage",
        "disk_io",
        "network_latency",
        "request_count",
        "error_rate",
        "response_time"
    ]
    
    sources = ["server-1", "server-2", "server-3", "api-gateway", "database"]
    
    # Generate metrics over the past 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    for i in range(count):
        metric_name = random.choice(metric_names)
        source = random.choice(sources)
        
        # Generate normal values based on metric type
        if "usage" in metric_name or "rate" in metric_name:
            value = random.uniform(10.0, 90.0)  # Percentage
        elif "latency" in metric_name or "time" in metric_name:
            value = random.uniform(50.0, 500.0)  # Milliseconds
        else:
            value = random.uniform(100.0, 10000.0)  # Counts
        
        # Insert anomalies: spike values
        if random.random() < 0.03:  # 3% anomalies
            value *= random.uniform(5.0, 20.0)
        
        # Random timestamp
        random_seconds = random.uniform(0, 30 * 24 * 60 * 60)
        timestamp = end_date - timedelta(seconds=random_seconds)
        
        tags = {
            "environment": random.choice(["production", "staging", "development"]),
            "region": random.choice(["us-east", "us-west", "eu-central"]),
            "version": f"v{random.randint(1, 3)}.{random.randint(0, 9)}"
        }
        
        await conn.execute("""
            INSERT INTO metrics (metric_name, metric_value, timestamp, source, tags)
            VALUES ($1, $2, $3, $4, $5)
        """, metric_name, round(value, 4), timestamp, source, tags)
    
    print(f"✅ Created {count} metrics")


async def create_indexes(conn: asyncpg.Connection) -> None:
    """Create indexes for better query performance."""
    print("\n🔍 Creating indexes...")
    
    await conn.execute("CREATE INDEX idx_users_email ON users(email)")
    await conn.execute("CREATE INDEX idx_users_created_at ON users(created_at)")
    await conn.execute("CREATE INDEX idx_orders_user_id ON orders(user_id)")
    await conn.execute("CREATE INDEX idx_orders_created_at ON orders(created_at)")
    await conn.execute("CREATE INDEX idx_metrics_timestamp ON metrics(timestamp)")
    await conn.execute("CREATE INDEX idx_metrics_name ON metrics(metric_name)")
    await conn.execute("CREATE INDEX idx_metrics_source ON metrics(source)")
    
    print("✅ Indexes created")


async def print_summary(conn: asyncpg.Connection) -> None:
    """Print a summary of generated data."""
    print("\n" + "="*60)
    print("📈 Test Data Generation Summary")
    print("="*60)
    
    user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    product_count = await conn.fetchval("SELECT COUNT(*) FROM products")
    order_count = await conn.fetchval("SELECT COUNT(*) FROM orders")
    metric_count = await conn.fetchval("SELECT COUNT(*) FROM metrics")
    
    print(f"Users:         {user_count:,}")
    print(f"Products:      {product_count:,}")
    print(f"Orders:        {order_count:,}")
    print(f"Metrics:       {metric_count:,}")
    
    # Count potential anomalies
    anomaly_ages = await conn.fetchval(
        "SELECT COUNT(*) FROM users WHERE age < 10 OR age > 120"
    )
    anomaly_prices = await conn.fetchval(
        "SELECT COUNT(*) FROM products WHERE price <= 0 OR price > 50000"
    )
    anomaly_orders = await conn.fetchval(
        "SELECT COUNT(*) FROM orders WHERE total_amount <= 0 OR total_amount > 50000"
    )
    
    print(f"\n🚨 Injected Anomalies:")
    print(f"  Unusual ages:    {anomaly_ages}")
    print(f"  Unusual prices:  {anomaly_prices}")
    print(f"  Unusual orders:  {anomaly_orders}")
    print("="*60)


async def main() -> None:
    """Main function to generate all test data."""
    print("🎵 DataMetronome Test Data Generator")
    print("="*60)
    
    conn = None
    try:
        conn = await create_connection()
        
        await create_schema(conn)
        user_ids = await generate_users(conn, count=1000)
        product_ids = await generate_products(conn, count=200)
        await generate_orders(conn, user_ids, product_ids, count=500)
        await generate_metrics(conn, count=5000)
        await create_indexes(conn)
        
        await print_summary(conn)
        
        print("\n✅ Test data generation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error generating test data: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

