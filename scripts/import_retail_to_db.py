import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def configure_paths():
    sys.path.append(str(PROJECT_ROOT))
    sys.path.append(str(PROJECT_ROOT / "datametronome" / "podium"))


def configure_env():
    db_path = PROJECT_ROOT / "datametronome" / "podium" / "data" / "datametronome.db"
    os.environ["DATAMETRONOME_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["DATAMETRONOME_SECRET_KEY"] = "dev-secret-key-change-in-production-32-chars"
    return db_path


async def import_demo():
    configure_paths()
    db_path = configure_env()

    from datametronome_podium.core.database import get_db, init_db  # noqa: E402
    from datametronome_podium.services.stave_yaml_loader import (  # noqa: E402
        import_staves_from_yaml,
        load_staves_from_yaml,
    )

    print("🚀 Importing Retail Demo configuration to main DB...")
    print(f"Using DB Path: {db_path}")
    if db_path.exists():
        print(f"Removing existing DB at {db_path} to ensure fresh schema...")
        db_path.unlink()

    await init_db()
    db = await get_db()

    yaml_path = PROJECT_ROOT / "showcase" / "retail_demo" / "retail.yaml"

    staves, _clefs = load_staves_from_yaml(yaml_path, resolve_env=False)
    print(f"DEBUG: Loaded {len(staves)} staves from YAML:")
    for stave in staves:
        print(f" - {stave.id}: {stave.name}")

    try:
        count = await db.query({"sql": "SELECT COUNT(*) as count FROM staves", "params": []})
        print(f"DEBUG: Staves in DB before import: {count[0]['count']}")
    except Exception as exc:
        print(f"DEBUG: Could not count staves: {exc}")

    result = await import_staves_from_yaml(
        yaml_path=yaml_path,
        db=db,
        resolve_env=True,
        overwrite=False,
    )

    print(f"✅ Import complete: {result}")

if __name__ == "__main__":
    asyncio.run(import_demo())
