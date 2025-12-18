#!/usr/bin/env python3

import asyncio
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def configure_paths():
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT / "datametronome" / "podium"))


def configure_env():
    podium_db_path = PROJECT_ROOT / "datametronome" / "podium" / "data" / "datametronome.db"
    os.environ["DATAMETRONOME_DATABASE_URL"] = f"sqlite+aiosqlite:///{podium_db_path}"
    os.environ["DATAMETRONOME_SECRET_KEY"] = "dev-secret-key-change-in-production-32-chars"
    return podium_db_path


async def import_demo():
    configure_paths()
    podium_db_path = configure_env()

    from datametronome_podium.core.database import get_db, init_db  # noqa: E402
    from datametronome_podium.services.stave_yaml_loader import (  # noqa: E402
        import_staves_from_yaml,
        load_staves_from_yaml,
    )

    print("🚀 Importing Retail Demo configuration to main DB...")
    print(f"Using Podium DB Path: {podium_db_path}")

    if podium_db_path.exists():
        print(f"Removing existing DB at {podium_db_path} to ensure fresh schema...")
        podium_db_path.unlink()

    await init_db()
    db = await get_db()

    yaml_path = PROJECT_ROOT / "showcase" / "retail_demo" / "retail.yaml"

    staves, _clefs = load_staves_from_yaml(yaml_path, resolve_env=False)
    print(f"Loaded {len(staves)} staves from YAML:")
    for stave in staves:
        print(f" - {stave.id}: {stave.name}")

    if not os.environ.get("DB_PATH"):
        print(
            "⚠️  DB_PATH is not set. The Retail demo stave expects DB_PATH to point at the retail dataset SQLite file.\n"
            "    Example:\n"
            "      export DB_PATH=\"$(pwd)/datametronome/podium/data/retail.db\""
        )

    result = await import_staves_from_yaml(
        yaml_path=yaml_path,
        db=db,
        resolve_env=True,
        overwrite=False,
    )

    print(f"✅ Import complete: {result}")


if __name__ == "__main__":
    asyncio.run(import_demo())


