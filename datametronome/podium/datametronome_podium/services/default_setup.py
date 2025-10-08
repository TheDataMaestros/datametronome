"""
Service to set up default DEMO staves on application startup.
"""

import logging
from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import create_stave, serialize_stave
import random

logger = logging.getLogger(__name__)

async def create_default_staves_and_clefs():
    """
    Create DEMO staves for demonstration purposes.
    All DEMO staves use demo.db SQLite database.
    """
    db = await get_db()

    # Check if DEMO staves already exist to prevent duplicates
    existing_demo_staves = await db.query({"sql": "SELECT * FROM staves WHERE name LIKE 'DEMO-%'", "params": []})
    if existing_demo_staves:
        logger.info("DEMO staves already exist. Skipping creation.")
        return

    logger.info("Creating DEMO staves...")

    # DEMO-Clickstream: For clickstream data
    demo_clickstream = create_stave(
        name="DEMO-Clickstream",
        data_source_type="sqlite",
        connection_config={"database_path": "demo.db"},
        description="Demo stave for clickstream data (clicks table only)"
    )
    await db.write([serialize_stave(demo_clickstream)], "staves")

    # Ensure the clicks table exists in demo.db
    try:
        from metronome_pulse_sqlite import SQLitePulse
        demo_db = SQLitePulse("demo.db")
        await demo_db.connect()
        await demo_db.execute(
            """
            CREATE TABLE IF NOT EXISTS clicks (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                page_url TEXT,
                click_timestamp TEXT,
                session_id TEXT,
                user_agent TEXT
            )
            """,
            params=[]
        )
        await demo_db.disconnect()
        logger.info("✅ Created DEMO-Clickstream stave with clicks table in demo.db")
    except Exception as e:
        logger.error(f"Failed to create clicks table in demo.db: {e}")

    logger.info("Finished creating DEMO staves.")


async def generate_streaming_data_job():
    """A background job that generates and inserts clickstream data into demo.db."""
    logger.info("Running streaming clickstream data generation job...")
    try:
        from .data_generator import generate_clickstream_data
        from metronome_pulse_sqlite import SQLitePulse

        # Use demo.db for clickstream data
        demo_db = SQLitePulse("demo.db")
        await demo_db.connect()
        
        # Ensure the table exists
        await demo_db.execute(
            """
            CREATE TABLE IF NOT EXISTS clicks (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                page_url TEXT,
                click_timestamp TEXT,
                session_id TEXT,
                user_agent TEXT
            )
            """,
            params=[]
        )

        data = generate_clickstream_data(count=random.randint(5, 20))
        await demo_db.write(data, "clicks")
        await demo_db.disconnect()
        logger.info(f"✅ Generated and inserted {len(data)} clickstream events into demo.db")
    except Exception as e:
        logger.error(f"Error in streaming data generation job: {e}")
