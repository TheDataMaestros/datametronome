"""
Service to set up default DEMO staves on application startup.
"""

import logging
import random

from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import (
    create_clef,
    create_stave,
    serialize_clef,
    serialize_stave,
)

logger = logging.getLogger(__name__)


async def create_default_staves_and_clefs():
    """
    Create DEMO staves and clefs for demonstration purposes.
    Loads configuration from demo-clickstream.yaml if available.
    """
    db = await get_db()

    # Check if DEMO staves already exist to prevent duplicates
    existing_demo_staves = await db.query(
        {"sql": "SELECT * FROM staves WHERE name LIKE 'DEMO-%'", "params": []}
    )
    if existing_demo_staves:
        logger.info("DEMO staves already exist. Skipping creation.")
        return

    logger.info("Creating DEMO staves and clefs...")

    # Try to load from YAML first
    try:
        from pathlib import Path

        import yaml

        yaml_path = Path(__file__).parent.parent / "examples" / "demo-complete.yaml"

        if yaml_path.exists():
            logger.info(f"Loading demo configuration from {yaml_path}")
            with open(yaml_path, "r") as f:
                config = yaml.safe_load(f)

            # Create staves
            for stave_config in config.get("staves", []):
                demo_stave = create_stave(
                    name=stave_config["name"],
                    data_source_type=stave_config["data_source_type"],
                    connection_config=stave_config["connection_config"],
                    description=stave_config.get("description"),
                )
                # Override ID if specified
                if "id" in stave_config:
                    demo_stave.id = stave_config["id"]

                await db.write([serialize_stave(demo_stave)], "staves")
                logger.info(f"✅ Created stave: {demo_stave.name}")

            # Create clefs
            for clef_config in config.get("clefs", []):
                demo_clef = create_clef(
                    stave_id=clef_config["stave_id"],
                    name=clef_config["name"],
                    check_type=clef_config["check_type"],
                    config=clef_config["config"],
                    description=clef_config.get("description"),
                    schedule=clef_config.get("schedule"),
                    is_active=clef_config.get("is_active", True),
                    warn=clef_config.get("warn"),
                    fail=clef_config.get("fail"),
                )
                # Override ID if specified
                if "id" in clef_config:
                    demo_clef.id = clef_config["id"]

                await db.write([serialize_clef(demo_clef)], "clefs")
                logger.info(f"✅ Created clef: {demo_clef.name}")

            logger.info("✅ Demo configuration loaded from YAML")
        else:
            logger.warning(f"YAML config not found at {yaml_path}, creating manually")
            raise FileNotFoundError("YAML not found")

    except Exception as e:
        logger.warning(f"Could not load YAML config: {e}. Creating manually...")

        # Fallback: Create manually
        demo_clickstream = create_stave(
            name="DEMO-Clickstream",
            data_source_type="sqlite",
            connection_config={"database_path": "demo.db"},
            description="Demo stave for clickstream data (clicks table only)",
        )
        await db.write([serialize_stave(demo_clickstream)], "staves")
        logger.info("✅ Created DEMO-Clickstream stave")

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
            params=[],
        )
        await demo_db.disconnect()
        logger.info("✅ Ensured clicks table exists in demo.db")
    except Exception as e:
        logger.error(f"Failed to create clicks table in demo.db: {e}")

    logger.info("Finished creating DEMO staves and clefs.")


async def generate_streaming_data_job():
    """A background job that generates and inserts clickstream data into demo.db."""
    logger.info("Running streaming clickstream data generation job...")
    try:
        from metronome_pulse_sqlite import SQLitePulse

        from .data_generator import generate_clickstream_data

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
            params=[],
        )

        data = generate_clickstream_data(count=random.randint(5, 20))
        await demo_db.write(data, "clicks")
        await demo_db.disconnect()
        logger.info(
            f"✅ Generated and inserted {len(data)} clickstream events into demo.db"
        )
    except Exception as e:
        logger.error(f"Error in streaming data generation job: {e}")
