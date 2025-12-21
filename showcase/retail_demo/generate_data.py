"""
Retail demo data generator.

Creates a SQLite database with ~60 days of history and injects anomalies for today.
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def create_retail_db(db_path="retail.db"):
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()

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

    # Use midnight boundaries so `date(created_at)` groupings are stable.
    # (If we used `datetime.now()` as-is, adding hours can spill into the next day.)
    start_date = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=60)

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

        # Order Volume: Seasonality with minimal growth for stable forecasting
        # Base: 50, Weekend Multiplier: 1.5x, Very gradual growth: +0.1 per day
        # Reduced growth to prevent forecast check from flagging everything as outlier
        base_orders = 50 + (day * 0.1)  # Much slower growth
        if is_weekend:
            daily_orders_count = int(base_orders * 1.5)
        else:
            daily_orders_count = int(base_orders)

        # Add some random noise (but less aggressive)
        daily_orders_count += random.randint(-3, 3)

        # Order Amounts: Very stable baseline for drift detection
        # Baseline: Consistent ~$100 mean, ~$20 std across all historical days
        # This creates a clear, predictable pattern that makes drift obvious
        for _ in range(daily_orders_count):
            # Very stable baseline: mean exactly $100, std ~$20
            # Use truncated normal to prevent extreme outliers (cap at 3σ)
            amount = random.gauss(100, 20)
            # Cap at reasonable bounds: mean ± 3σ = $100 ± $60 = $40 to $160
            amount = max(40.0, min(160.0, amount))
            orders.append(
                (
                    None,
                    random.randint(1, len(users)) if users else 1,
                    amount,
                    random.choice(["completed", "pending", "shipped"]),
                    (current_date + timedelta(hours=random.randint(8, 20))).isoformat(),
                )
            )

    # 2. Insert Data Drift (Last 5 Days - showing gradual, realistic distribution shift)
    print(
        "Injecting data drift for last 5 days (gradual, realistic distribution shift)..."
    )
    now = datetime.now()

    # Data drift scenario: Distribution gradually shifts over 5 days
    # More realistic: smoother transition, less abrupt changes
    # This shows TRUE drift (sustained change) vs anomaly (single outlier)
    drift_days = [
        (now - timedelta(days=4), 101, 20),  # Day -4: Very slight shift (1.5% increase)
        (now - timedelta(days=3), 102.5, 20.5),  # Day -3: Slight shift (3% increase)
        (now - timedelta(days=2), 105, 21),  # Day -2: Moderate shift (5.5% increase)
        (
            now - timedelta(days=1),
            108,
            21.5,
        ),  # Day -1: Noticeable shift (8.5% increase)
        (now, 111, 22),  # Today: Significant shift (11.5% increase) - more realistic
    ]

    for drift_date, drift_mean, drift_std in drift_days:
        drift_date = drift_date.replace(hour=12, minute=0, second=0, microsecond=0)

        # Keep volume consistent for drift detection (need enough samples)
        daily_orders = random.randint(18, 25)

        for _ in range(daily_orders):
            # Gradual drift: distribution shifts and stays shifted
            # Use truncated normal to prevent extreme outliers (cap at 3σ)
            amount = random.gauss(drift_mean, drift_std)
            # Cap at reasonable bounds: mean ± 3σ to prevent spikes
            min_bound = max(40.0, drift_mean - (3 * drift_std))
            max_bound = min(200.0, drift_mean + (3 * drift_std))
            amount = max(min_bound, min(max_bound, amount))
            orders.append(
                (
                    None,
                    random.randint(1, len(users)),
                    amount,
                    "completed",
                    drift_date.isoformat(),
                )
            )

    # Bulk Insert
    print(f"Inserting {len(users)} users and {len(orders)} orders...")
    cur.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", users)
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print(f"Database created at {db_path}")


if __name__ == "__main__":
    create_retail_db()
