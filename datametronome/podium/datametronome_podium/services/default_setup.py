"""
Service to set up default staves and clefs on application startup.
"""

import logging
from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import create_stave, create_clef, serialize_stave, serialize_clef
import random

logger = logging.getLogger(__name__)

async def create_default_staves_and_clefs():
    """
    Create a set of default staves and clefs if they don't already exist.
    This is useful for demos and getting started quickly.
    """
    db = await get_db()

    # Check if default staves already exist to prevent duplicates
    existing_staves = await db.query({"sql": "SELECT * FROM staves WHERE name LIKE '%(Default)%'", "params": []})
    if existing_staves:
        logger.info("Default staves already exist. Skipping creation.")
        return

    logger.info("Creating default staves and clefs...")

    # 1. SQLite Stave (for the app's own backend)
    sqlite_stave = create_stave(
        name="Podium Backend DB (Default)",
        data_source_type="sqlite",
        connection_config={"database_path": "datametronome.db"},
        description="The main SQLite database for the Podium application itself."
    )
    await db.write([serialize_stave(sqlite_stave)], "staves")

    # Clefs for SQLite Stave
    clef1 = create_clef(
        stave_id=sqlite_stave.id,
        name="Check for new users",
        check_type="row_count",
        config={"table": "users"},
        schedule="*/5 * * * *"  # Every 5 minutes
    )
    clef2 = create_clef(
        stave_id=sqlite_stave.id,
        name="Hourly check on clefs table",
        check_type="row_count",
        config={"table": "clefs"},
        schedule="0 * * * *"  # Every hour
    )
    await db.write([serialize_clef(c) for c in [clef1, clef2]], "clefs")


    # 2. PostgreSQL Stave (for e-commerce data)
    pg_stave = create_stave(
        name="E-commerce Postgres DB (Default)",
        data_source_type="postgres",
        connection_config={
            "host": "localhost",
            "port": 5432,
            "database": "ecommerce",
            "user": "user",
            "password": "password"
        },
        description="A sample PostgreSQL database for e-commerce data (orders, products)."
    )
    await db.write([serialize_stave(pg_stave)], "staves")

    # 3. MySQL Stave (for sales data)
    mysql_stave = create_stave(
        name="Sales MySQL DB (Default)",
        data_source_type="mysql",
        connection_config={
            "host": "localhost",
            "port": 3306,
            "database": "sales",
            "user": "user",
            "password": "password"
        },
        description="A sample MySQL database for sales tracking."
    )
    await db.write([serialize_stave(mysql_stave)], "staves")

    # 4. Clicks Stave (for streaming data)
    clicks_stave = create_stave(
        name="Clickstream Data (Default)",
        data_source_type="sqlite",
        connection_config={"database_path": "clicks.db"},
        description="A database to store simulated streaming clickstream data."
    )
    await db.write([serialize_stave(clicks_stave)], "staves")

    # Ensure the database and table for clicks exist
    try:
        from datametronome_podium.pulse.sqlite import DataPulseSQLite
        clicks_db = DataPulseSQLite(database_path="clicks.db")
        await clicks_db.connect()
        await clicks_db.execute(
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
        await clicks_db.disconnect()
        logger.info("Ensured clickstream database and table exist.")
    except Exception as e:
        logger.error(f"Failed to create clickstream database/table: {e}")


    logger.info("Finished creating default staves and clefs.")


async def generate_streaming_data_job():
    """A background job that generates and inserts clickstream data."""
    logger.info("Running streaming data generation job...")
    try:
        from .data_generator import generate_clickstream_data
        from datametronome_podium.pulse.sqlite import DataPulseSQLite

        # This assumes the clicks.db is in the root directory.
        clicks_db = DataPulseSQLite(database_path="clicks.db")
        await clicks_db.connect()
        
        # Ensure the table exists
        await clicks_db.execute(
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
        await clicks_db.write(data, "clicks")
        await clicks_db.disconnect()
        logger.info(f"Generated and inserted {len(data)} clickstream events.")
    except Exception as e:
        logger.error(f"Error in streaming data generation job: {e}")
