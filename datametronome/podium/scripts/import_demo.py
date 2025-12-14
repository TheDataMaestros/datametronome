#!/usr/bin/env python3
"""
Import demo configuration from YAML file.

Usage:
    python3 scripts/import_demo.py [--clean]

Options:
    --clean    Delete existing DEMO staves/clefs before importing
"""

import asyncio
import logging
import sys
from pathlib import Path

import yaml

# Add parent directory to path so we can import from datametronome_podium
sys.path.insert(0, str(Path(__file__).parent.parent))

from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import (
    create_clef,
    create_stave,
    serialize_clef,
    serialize_stave,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clean_demo_data():
    """Delete existing DEMO staves and clefs."""
    logger.info("🧹 Cleaning existing DEMO data...")
    db = await get_db()

    # Delete checks first (foreign key constraint)
    await db.execute(
        "DELETE FROM checks WHERE stave_id IN (SELECT id FROM staves WHERE name LIKE 'DEMO-%')",
        [],
    )
    logger.info("  ✅ Deleted demo checks")

    # Delete clefs
    await db.execute(
        "DELETE FROM clefs WHERE stave_id IN (SELECT id FROM staves WHERE name LIKE 'DEMO-%')",
        [],
    )
    logger.info("  ✅ Deleted demo clefs")

    # Delete staves
    await db.execute("DELETE FROM staves WHERE name LIKE 'DEMO-%'", [])
    logger.info("  ✅ Deleted demo staves")
    logger.info("🎉 Cleanup complete!")


async def import_demo_config(yaml_file: str = "examples/demo-complete.yaml"):
    """Import demo configuration from YAML file."""
    yaml_path = Path(yaml_file)

    if not yaml_path.exists():
        logger.error(f"❌ YAML file not found: {yaml_path}")
        return False

    logger.info(f"📂 Loading configuration from {yaml_path}")

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    db = await get_db()

    # Create staves
    logger.info(f"📊 Creating {len(config.get('staves', []))} staves...")
    for stave_config in config.get("staves", []):
        stave = create_stave(
            name=stave_config["name"],
            data_source_type=stave_config["data_source_type"],
            connection_config=stave_config["connection_config"],
            description=stave_config.get("description"),
        )
        # Override ID if specified
        if "id" in stave_config:
            stave.id = stave_config["id"]

        await db.write([serialize_stave(stave)], "staves")
        logger.info(f"  ✅ Created stave: {stave.name} (ID: {stave.id})")

    # Create clefs
    logger.info(f"🎯 Creating {len(config.get('clefs', []))} clefs...")
    for clef_config in config.get("clefs", []):
        clef = create_clef(
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
            clef.id = clef_config["id"]

        await db.write([serialize_clef(clef)], "clefs")
        logger.info(f"  ✅ Created clef: {clef.name} (ID: {clef.id})")

    logger.info("🎉 Demo configuration imported successfully!")
    logger.info("")
    logger.info("📊 Summary:")
    logger.info(f"  - Staves created: {len(config.get('staves', []))}")
    logger.info(f"  - Clefs created: {len(config.get('clefs', []))}")
    logger.info("")
    logger.info("🚀 Next steps:")
    logger.info("  1. Start/restart the Podium API to schedule the clefs")
    logger.info("  2. Open the dashboard: http://localhost:3000/dashboard.html")
    logger.info("  3. Generate sample data using the dashboard")
    logger.info("  4. Watch the checks run automatically!")

    return True


async def main():
    """Main entry point."""
    clean = "--clean" in sys.argv

    if clean:
        logger.info("🔄 Running in CLEAN mode - will delete existing DEMO data first")
        await clean_demo_data()
        logger.info("")

    success = await import_demo_config()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
