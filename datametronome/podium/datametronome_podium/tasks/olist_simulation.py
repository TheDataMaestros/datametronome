"""Olist e-commerce data simulation task.

Generates synthetic orders, items, and payments to simulate a live
e-commerce pipeline feeding the Olist dataset. Each run inserts a small
batch of new records so the intelligence pipeline can detect real trends
instead of a static snapshot.
"""
import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

from datametronome_podium.core.celery_app import celery_app
from datametronome_podium.core.config import settings

logger = logging.getLogger(__name__)

_S = "olist"  # schema name


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="datametronome.olist_simulate_ingestion",
    acks_late=True,
    max_retries=1,
)
def olist_simulate_ingestion(batch_size: int = 30) -> dict:
    """Insert synthetic Olist orders to simulate live e-commerce data flow.

    Picks random existing customers, products, and sellers from the DB,
    then inserts `batch_size` new orders with today's timestamps along
    with order_items and order_payments.
    """
    try:
        return _run_async(_simulate_async(batch_size))
    except Exception as exc:
        logger.error("Olist simulation failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


@celery_app.task(
    name="datametronome.run_daily_intelligence_all_staves",
    acks_late=True,
    max_retries=0,
)
def run_daily_intelligence_all_staves() -> dict:
    """Dispatch run_daily_intelligence for every active stave."""
    try:
        return _run_async(_dispatch_daily_async())
    except Exception as exc:
        logger.error("Daily intelligence dispatch failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


async def _dispatch_daily_async() -> dict:
    from datametronome_podium.core.worker_db import worker_db_session
    from datametronome_podium.tasks.intelligence_tasks import run_daily_intelligence

    async with worker_db_session(settings.database_url) as (_, executor):
        staves = await executor.query(
            "SELECT id FROM staves WHERE is_active = TRUE", []
        )

    dispatched = []
    for row in staves or []:
        stave_id = row["id"]
        run_daily_intelligence.delay(stave_id)
        dispatched.append(stave_id)
        logger.info("Dispatched daily intelligence for stave %s", stave_id)

    return {"status": "dispatched", "staves": dispatched}


async def _simulate_async(batch_size: int) -> dict:
    from datametronome_podium.core.worker_db import worker_db_session

    async with worker_db_session(settings.database_url) as (_, executor):
        # Sample existing FK references
        customers = await executor.query(
            f'SELECT customer_id FROM "{_S}".customers ORDER BY RANDOM() LIMIT 200', []
        )
        products = await executor.query(
            f'SELECT product_id FROM "{_S}".products ORDER BY RANDOM() LIMIT 100', []
        )
        sellers = await executor.query(
            f'SELECT seller_id FROM "{_S}".sellers ORDER BY RANDOM() LIMIT 50', []
        )

        if not customers or not products or not sellers:
            logger.warning("Olist simulation: missing FK data, skipping")
            return {"status": "skipped", "reason": "no_reference_data"}

        customer_ids = [r["customer_id"] for r in customers]
        product_ids = [r["product_id"] for r in products]
        seller_ids = [r["seller_id"] for r in sellers]

        now = datetime.now(timezone.utc)
        inserted_orders = 0

        for _ in range(batch_size):
            order_id = uuid.uuid4().hex
            customer_id = random.choice(customer_ids)
            purchase_ts = now - timedelta(minutes=random.randint(0, 120))
            approved_ts = purchase_ts + timedelta(minutes=random.randint(5, 30))
            estimated_delivery = purchase_ts + timedelta(days=random.randint(5, 15))

            # Insert order
            await executor.execute(
                f'INSERT INTO "{_S}".orders '
                "(order_id, customer_id, order_status, "
                "order_purchase_timestamp, order_approved_at, "
                "order_estimated_delivery_date) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (order_id) DO NOTHING",
                [
                    order_id,
                    customer_id,
                    "processing",
                    purchase_ts.replace(tzinfo=None),
                    approved_ts.replace(tzinfo=None),
                    estimated_delivery.replace(tzinfo=None),
                ],
            )

            # Insert 1–3 order items
            num_items = random.randint(1, 3)
            for item_idx in range(1, num_items + 1):
                product_id = random.choice(product_ids)
                seller_id = random.choice(seller_ids)
                price = round(random.uniform(20.0, 500.0), 2)
                freight = round(random.uniform(5.0, 40.0), 2)
                shipping_limit = purchase_ts + timedelta(days=3)

                await executor.execute(
                    f'INSERT INTO "{_S}".order_items '
                    "(order_id, order_item_id, product_id, seller_id, "
                    "shipping_limit_date, price, freight_value) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT DO NOTHING",
                    [
                        order_id,
                        item_idx,
                        product_id,
                        seller_id,
                        shipping_limit.replace(tzinfo=None),
                        price,
                        freight,
                    ],
                )

            # Insert payment
            payment_value = round(random.uniform(30.0, 600.0), 2)
            payment_type = random.choice(
                ["credit_card", "boleto", "voucher", "debit_card"]
            )
            await executor.execute(
                f'INSERT INTO "{_S}".order_payments '
                "(order_id, payment_sequential, payment_type, "
                "payment_installments, payment_value) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING",
                [order_id, 1, payment_type, random.randint(1, 12), payment_value],
            )

            inserted_orders += 1

    logger.info("Olist simulation: inserted %d synthetic orders", inserted_orders)
    return {
        "status": "completed",
        "inserted_orders": inserted_orders,
        "timestamp": now.isoformat(),
    }
