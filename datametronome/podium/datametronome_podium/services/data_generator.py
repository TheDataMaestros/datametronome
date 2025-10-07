"""
Data Generation Service.

This module provides functions to generate realistic sample data for various
scenarios, such as e-commerce (products, orders) and web analytics (clickstream).
It uses the Faker library to create believable data.
"""

import uuid
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

def generate_products_data(count: int = 100) -> list[dict]:
    """Generate a list of sample products."""
    products = []
    for _ in range(count):
        products.append({
            "product_id": str(uuid.uuid4()),
            "name": fake.ecommerce_name(),
            "category": fake.ecommerce_category(),
            "price": round(random.uniform(5.0, 500.0), 2),
            "created_at": fake.date_time_this_year().isoformat()
        })
    return products

def generate_orders_data(products: list[dict], count: int = 500) -> list[dict]:
    """Generate a list of sample orders using a given list of products."""
    if not products:
        return []
    
    orders = []
    for _ in range(count):
        product = random.choice(products)
        quantity = random.randint(1, 5)
        orders.append({
            "order_id": str(uuid.uuid4()),
            "product_id": product["product_id"],
            "customer_email": fake.email(),
            "quantity": quantity,
            "total_price": round(product["price"] * quantity, 2),
            "order_date": fake.date_time_between(start_date="-1y", end_date="now").isoformat(),
            "status": random.choice(["completed", "shipped", "pending", "cancelled"])
        })
    return orders

def generate_clickstream_data(count: int = 1000) -> list[dict]:
    """Generate a list of sample clickstream events."""
    events = []
    for _ in range(count):
        events.append({
            "event_id": str(uuid.uuid4()),
            "user_id": fake.uuid4(),
            "url": fake.uri(),
            "event_type": random.choice(["page_view", "click", "add_to_cart", "purchase"]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ip_address": fake.ipv4()
        })
    return events
