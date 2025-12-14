#!/usr/bin/env python3
"""
Universal YAML Import Utility for DataMetronome.

This script can import any YAML file containing staves and/or clefs.

Usage:
    python3 scripts/import_yaml.py <yaml_file> [--clean] [--dry-run]

Arguments:
    yaml_file    Path to YAML file to import

Options:
    --clean      Delete existing staves/clefs with matching IDs before importing
    --dry-run    Show what would be imported without actually importing

Examples:
    # Import demo configuration
    python3 scripts/import_yaml.py examples/demo-complete.yaml

    # Clean import (replace existing)
    python3 scripts/import_yaml.py examples/demo-complete.yaml --clean

    # Dry run to see what would be imported
    python3 scripts/import_yaml.py examples/my-config.yaml --dry-run
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datametronome_podium.core.database import get_db
from datametronome_podium.services.stave_service import (
    create_clef,
    create_stave,
    serialize_clef,
    serialize_stave,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def clean_existing_items(stave_ids: List[str], clef_ids: List[str]):
    """Delete existing staves and clefs by ID."""
    db = await get_db()

    if clef_ids:
        logger.info(f"🧹 Cleaning {len(clef_ids)} existing clefs...")
        for clef_id in clef_ids:
            # Delete checks for this clef
            await db.execute("DELETE FROM checks WHERE clef_id = ?", [clef_id])
            # Delete the clef
            await db.execute("DELETE FROM clefs WHERE id = ?", [clef_id])
        logger.info(f"  ✅ Deleted {len(clef_ids)} clefs and their checks")

    if stave_ids:
        logger.info(f"🧹 Cleaning {len(stave_ids)} existing staves...")
        for stave_id in stave_ids:
            # Delete checks for this stave
            await db.execute("DELETE FROM checks WHERE stave_id = ?", [stave_id])
            # Delete clefs for this stave
            await db.execute("DELETE FROM clefs WHERE stave_id = ?", [stave_id])
            # Delete the stave
            await db.execute("DELETE FROM staves WHERE id = ?", [stave_id])
        logger.info(f"  ✅ Deleted {len(stave_ids)} staves and their dependencies")


async def import_yaml_config(
    yaml_file: str, clean: bool = False, dry_run: bool = False
):
    """Import configuration from YAML file."""
    yaml_path = Path(yaml_file)

    if not yaml_path.exists():
        logger.error(f"❌ YAML file not found: {yaml_path}")
        return False

    logger.info(f"📂 Loading configuration from {yaml_path}")

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    staves_config = config.get("staves", [])
    clefs_config = config.get("clefs", [])

    logger.info(f"📊 Found in YAML:")
    logger.info(f"  - Staves: {len(staves_config)}")
    logger.info(f"  - Clefs: {len(clefs_config)}")
    logger.info("")

    if dry_run:
        logger.info("🔍 DRY RUN MODE - Showing what would be imported:")
        logger.info("")
        logger.info("Staves:")
        for s in staves_config:
            logger.info(f"  - {s.get('name')} (ID: {s.get('id', 'auto-generated')})")
        logger.info("")
        logger.info("Clefs:")
        for c in clefs_config:
            logger.info(
                f"  - {c.get('name')} (ID: {c.get('id', 'auto-generated')}, Type: {c.get('check_type')})"
            )
        logger.info("")
        logger.info("✅ Dry run complete. Use without --dry-run to actually import.")
        return True

    db = await get_db()

    # Clean existing items if requested
    if clean:
        stave_ids = [s["id"] for s in staves_config if "id" in s]
        clef_ids = [c["id"] for c in clefs_config if "id" in c]
        await clean_existing_items(stave_ids, clef_ids)
        logger.info("")

    # Create staves
    logger.info(f"📊 Creating {len(staves_config)} staves...")
    for stave_config in staves_config:
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
        logger.info(f"  ✅ {stave.name} (ID: {stave.id})")

    # Create clefs
    logger.info(f"🎯 Creating {len(clefs_config)} clefs...")
    for clef_config in clefs_config:
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
        schedule_info = f" [{clef.schedule}]" if clef.schedule else ""
        logger.info(f"  ✅ {clef.name}{schedule_info}")

    logger.info("")
    logger.info("🎉 Configuration imported successfully!")
    logger.info("")
    logger.info("📊 Summary:")
    logger.info(f"  - Staves created: {len(staves_config)}")
    logger.info(f"  - Clefs created: {len(clefs_config)}")
    logger.info("")
    logger.info("🚀 Next steps:")
    logger.info("  1. Restart the Podium API to schedule the clefs:")
    logger.info("     python3 -m datametronome_podium.main")
    logger.info("  2. Open the dashboard: http://localhost:3000/dashboard.html")
    logger.info("  3. Generate sample data using the dashboard")
    logger.info("  4. Watch the checks run automatically!")
    logger.info("")

    return True


def print_usage():
    """Print usage information."""
    print(__doc__)


async def main():
    """Main entry point."""
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)

    yaml_file = sys.argv[1]
    clean = "--clean" in sys.argv
    dry_run = "--dry-run" in sys.argv

    if clean:
        logger.info(
            "🔄 CLEAN mode enabled - will delete existing items with matching IDs"
        )
        logger.info("")

    success = await import_yaml_config(yaml_file, clean=clean, dry_run=dry_run)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
