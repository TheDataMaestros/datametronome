"""
Retail demo data generator.

Creates a SQLite database with ~60 days of history and injects anomalies for today.
"""

from datetime import datetime, timedelta
import random
import sqlite3

import numpy as np


def create_retail_db(db_path="retail.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create Tables
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            country TEXT,
            created_at TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            status TEXT,
            created_at TIMESTAMP
        )
        """
    )

    # 1. Generate History (Last 60 Days)
    # Goal: Predictable pattern for Forecasting (e.g. weekly seasonality + growth)

    start_date = datetime.now() - timedelta(days=60)

    users = []
    orders = []

    print("Generating 60 days of historical data...")

    for day in range(60):
        current_date = start_date + timedelta(days=day)
        is_weekend = current_date.weekday() >= 5

        # User Growth: ~10 new users per day, more on weekends
        new_user_count = random.randint(15, 25) if is_weekend else random.randint(8, 12)

        for _ in range(new_user_count):
            users.append(
                (
                    None,
                    f"User_{len(users)}",
                    f"user{len(users)}@example.com" if random.random() > 0.05 else None,
                    random.choice(["US", "UK", "CA", "DE", "FR"]),
                    current_date.isoformat(),
                )
            )

        # Order Volume: Seasonality
        # Base: 50, Weekend Multiplier: 1.5x, Growth: +0.5 per day
        base_orders = 50 + (day * 0.5) 
        if is_weekend:
            daily_orders_count = int(base_orders * 1.5)
        else:
            daily_orders_count = int(base_orders)

        # Add some random noise
        daily_orders_count += random.randint(-5, 5)

        # Order Amounts: Normal distribution around $100
        # For drift detection later, we keep this stable for now
        for _ in range(daily_orders_count):
            amount = max(10.0, np.random.normal(100, 20))
            orders.append(
                (
                    None,
                    random.randint(1, len(users)) if users else 1,
                    amount,
                    random.choice(["completed", "pending", "shipped"]),
                    (current_date + timedelta(hours=random.randint(8, 20))).isoformat(),
                )
            )

    # 2. Insert Anomalies (Today)
    print("Injecting anomalies for 'Today'...")
    today = datetime.now()

    # A. Forecast Anomaly: Drop in order volume (e.g. system outage)
    # Expected: ~80 (base 50 + 30 growth). Actual: 10
    for _ in range(10):
        orders.append((None, random.randint(1, len(users)), 100.0, "completed", today.isoformat()))

    # B. Drift Anomaly: Spike in order values (e.g. pricing bug)
    # Instead of mean $100, mean $500
    for _ in range(50):
        amount = max(10.0, np.random.normal(500, 50))  # HUGE drift
        orders.append((None, random.randint(1, len(users)), amount, "completed", today.isoformat()))

    # Bulk Insert
    print(f"Inserting {len(users)} users and {len(orders)} orders...")
    cur.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", users)
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print(f"Database created at {db_path}")

if __name__ == "__main__":
    create_retail_db()
