"""
Data Generation Service.

This module provides functions to generate realistic sample data for various
scenarios, such as e-commerce (products, orders) and web analytics (clickstream).
It uses the Faker library to create believable data.
"""

import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

fake = Faker()


def generate_users_data(count: int = 100) -> list[dict]:
    """Generate a list of sample users."""
    users = []
    for _ in range(count):
        users.append(
            {
                "id": str(uuid.uuid4()),
                "name": fake.name(),
                "email": fake.email(),
                "age": random.randint(18, 80),
                "created_at": fake.date_time_between(
                    start_date="-1y", end_date="now"
                ).isoformat()
                + "Z",
                "updated_at": fake.date_time_between(
                    start_date="-1y", end_date="now"
                ).isoformat()
                + "Z",
            }
        )
    return users


def generate_products_data(count: int = 100) -> list[dict]:
    """Generate a list of sample products."""
    products = []
    categories = [
        "Electronics",
        "Clothing",
        "Books",
        "Home & Garden",
        "Sports",
        "Toys",
        "Food & Beverage",
    ]
    product_prefixes = [
        "Premium",
        "Deluxe",
        "Standard",
        "Basic",
        "Pro",
        "Ultra",
        "Classic",
    ]
    product_types = ["Widget", "Gadget", "Item", "Product", "Device", "Tool", "Kit"]

    for _ in range(count):
        products.append(
            {
                "id": str(uuid.uuid4()),
                "name": f"{random.choice(product_prefixes)} {random.choice(product_types)} {fake.word().title()}",
                "description": fake.text(max_nb_chars=200),
                "price": round(random.uniform(5.0, 500.0), 2),
                "category": random.choice(categories),
                "in_stock": random.choice([True, False]),
                "created_at": fake.date_time_between(
                    start_date="-1y", end_date="now"
                ).isoformat()
                + "Z",
            }
        )
    return products


def generate_orders_data(products: list[dict], count: int = 500) -> list[dict]:
    """Generate a list of sample orders using a given list of products."""
    if not products:
        return []

    orders = []
    for _ in range(count):
        product = random.choice(products)
        quantity = random.randint(1, 5)
        orders.append(
            {
                "id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),  # Generate random user ID
                "product_id": product["id"],
                "quantity": quantity,
                "total_amount": round(product["price"] * quantity, 2),
                "order_date": fake.date_time_between(
                    start_date="-1y", end_date="now"
                ).isoformat()
                + "Z",
                "status": random.choice(
                    ["completed", "shipped", "pending", "cancelled"]
                ),
            }
        )
    return orders


def generate_clickstream_data(count: int = 1000) -> list[dict]:
    """Generate a list of sample clickstream events."""
    events = []
    for _ in range(count):
        events.append(
            {
                "id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "page_url": fake.uri(),
                "click_timestamp": fake.date_time_between(
                    start_date="-1y", end_date="now"
                ).isoformat()
                + "Z",
                "session_id": str(uuid.uuid4()),
                "user_agent": fake.user_agent(),
            }
        )
    return events
