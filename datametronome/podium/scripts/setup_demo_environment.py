#!/usr/bin/env python3
"""
Demo Environment Setup Script
Creates sample data and configurations for demonstration purposes.
"""

import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def create_demo_sqlite_database():
    """Create a demo SQLite database with sample data."""
    db_path = "/tmp/demo.db"

    print(f"🗄️ Creating demo SQLite database at {db_path}")

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create users table
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            name TEXT NOT NULL,
            age INTEGER,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create orders table
    cursor.execute(
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_amount DECIMAL(10,2),
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """
    )

    # Create products table
    cursor.execute(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Insert sample users
    users_data: list[tuple[str | None, str, int, str]] = [
        ("john.doe@example.com", "John Doe", 25, "active"),
        ("jane.smith@example.com", "Jane Smith", 30, "active"),
        ("bob.wilson@example.com", "Bob Wilson", 35, "active"),
        ("alice.brown@example.com", "Alice Brown", 28, "active"),
        ("charlie.davis@example.com", "Charlie Davis", 42, "active"),
        ("diana.miller@example.com", "Diana Miller", 33, "active"),
        ("eve.jones@example.com", "Eve Jones", 29, "active"),
        ("frank.garcia@example.com", "Frank Garcia", 45, "active"),
        ("grace.lee@example.com", "Grace Lee", 31, "active"),
        ("henry.taylor@example.com", "Henry Taylor", 38, "active"),
    ]

    # Add some users with NULL emails to test validation
    users_data.append((None, "Test User 1", 25, "active"))
    users_data.append((None, "Test User 2", 30, "active"))

    cursor.executemany(
        "INSERT INTO users (email, name, age, status) VALUES (?, ?, ?, ?)", users_data
    )

    # Insert sample products
    products_data = [
        ("Laptop", 999.99, 50),
        ("Mouse", 29.99, 100),
        ("Keyboard", 79.99, 75),
        ("Monitor", 299.99, 30),
        ("Headphones", 149.99, 60),
        ("Tablet", 399.99, 40),
        ("Phone", 699.99, 25),
        ("Charger", 19.99, 200),
        ("Case", 39.99, 150),
        ("Screen Protector", 9.99, 300),
    ]

    cursor.executemany(
        "INSERT INTO products (name, price, stock_quantity) VALUES (?, ?, ?)",
        products_data,
    )

    # Insert sample orders
    orders_data = []
    for i in range(50):
        user_id = random.randint(1, 12)  # Include users with NULL emails
        total_amount = round(random.uniform(10.00, 500.00), 2)
        created_at = datetime.now() - timedelta(days=random.randint(0, 30))

        orders_data.append(
            (
                user_id,
                total_amount,
                random.choice(["pending", "completed", "cancelled"]),
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

    cursor.executemany(
        "INSERT INTO orders (user_id, total_amount, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        orders_data,
    )

    conn.commit()
    conn.close()

    print(f"✅ Created demo database with:")
    print(f"   - 12 users (2 with NULL emails for testing)")
    print(f"   - 10 products")
    print(f"   - 50 orders")

    return db_path


def create_demo_environment_file():
    """Create a demo environment file with sample configuration."""
    env_content = """# Demo Environment Configuration
# Copy these to your actual environment or use as-is for demo

# Demo Database Configuration
DEMO_HOST=localhost
DEMO_PORT=5432
DEMO_DB=nuxt_demo
DEMO_USER=demo
DEMO_PASSWORD=demo123

# Production Demo Configuration (for e-commerce example)
PROD_DB_HOST=localhost
PROD_DB_PORT=5432
PROD_DB_NAME=ecommerce_prod
PROD_DB_USER=monitor_user
PROD_DB_PASSWORD=prod_password_123

ANALYTICS_DB_HOST=analytics-db.company.com
ANALYTICS_DB_USER=analytics_user
ANALYTICS_DB_PASSWORD=analytics_password_123

REDIS_HOST=redis.company.com
REDIS_PASSWORD=redis_password_123

MONGO_USER=mongo_user
MONGO_PASSWORD=mongo_password_123

# SQLite Demo (no configuration needed)
# Uses /tmp/demo.db (created by setup script)
"""

    env_file = Path(__file__).parent.parent / "examples" / "demo.env"
    env_file.write_text(env_content)

    print(f"✅ Created demo environment file: {env_file}")

    return str(env_file)


def create_sample_check_results():
    """Create sample check results for demonstration."""
    sample_results = [
        {
            "clef_id": "clef-users-email-check",
            "stave_id": "stave-demo-sqlite",
            "status": "warn",
            "observed_value": 0.167,  # 16.7% NULL emails
            "message": "16.7% of users have NULL email addresses",
            "metadata": {"total_users": 12, "null_emails": 2, "threshold": "> 10%"},
            "executed_at": datetime.now().isoformat(),
        },
        {
            "clef_id": "clef-orders-count-check",
            "stave_id": "stave-demo-sqlite",
            "status": "pass",
            "observed_value": 50,
            "message": "Order count is within expected range",
            "metadata": {
                "total_orders": 50,
                "min_threshold": 10,
                "max_threshold": 1000,
            },
            "executed_at": datetime.now().isoformat(),
        },
        {
            "clef_id": "clef-data-freshness-check",
            "stave_id": "stave-demo-sqlite",
            "status": "pass",
            "observed_value": 0.5,  # 0.5 hours ago
            "message": "Data is fresh, last updated 30 minutes ago",
            "metadata": {
                "last_update": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "max_age": "2 hours",
            },
            "executed_at": datetime.now().isoformat(),
        },
    ]

    results_file = (
        Path(__file__).parent.parent / "examples" / "sample_check_results.json"
    )
    with open(results_file, "w") as f:
        json.dump(sample_results, f, indent=2)

    print(f"✅ Created sample check results: {results_file}")

    return str(results_file)


def main():
    """Main setup function."""
    print("🎵 DataMetronome Demo Environment Setup")
    print("=" * 45)

    try:
        # Create demo SQLite database
        db_path = create_demo_sqlite_database()

        # Create demo environment file
        env_file = create_demo_environment_file()

        # Create sample check results
        results_file = create_sample_check_results()

        print(f"\n🎉 Demo Environment Setup Complete!")
        print("=" * 35)
        print(f"📊 Demo SQLite Database: {db_path}")
        print(f"⚙️  Demo Environment File: {env_file}")
        print(f"📈 Sample Check Results: {results_file}")

        print(f"\n🚀 Next Steps:")
        print(f"  1. Start the UI (cd ui-nuxt && npm run dev)")
        print(f"  2. Load a demo configuration:")
        print(f"     python3 scripts/load_demo_configs.py")
        print(f"  3. Import configurations into your database:")
        print(
            f"     python3 -m datametronome_podium.scripts.import_staves examples/demo-simple-monitoring.yaml"
        )
        print(f"  4. View the configurations in the UI!")

        print(f"\n💡 Demo Configurations Available:")
        print(f"  - demo-simple-monitoring.yaml (Basic checks)")
        print(f"  - demo-clickstream.yaml (Clickstream monitoring)")
        print(f"  - demo-complete.yaml (Full e-commerce setup)")

    except Exception as e:
        print(f"❌ Error setting up demo environment: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
