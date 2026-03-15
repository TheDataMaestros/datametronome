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
    return db_path


async def verify_db():
    configure_paths()
    db_path = configure_env()

    from datametronome_podium.core.database import (  # noqa: E402
        get_db,
        init_db,
    )

    print("Running DB verification")
    print(f"Checking DB at: {db_path}")
    if not db_path.exists():
        print("❌ DB file does not exist!")
        return

    await init_db()
    db = await get_db()

    staves = await db.query({"sql": "SELECT * FROM staves", "params": []})
    print(f"Found {len(staves)} staves:")
    found_retail = False
    for s in staves:
        print(f" - {s['name']} (ID: {s['id']})")
        if "Retail" in s["name"]:
            found_retail = True

    if found_retail:
        print("✅ Retail Stave FOUND.")
    else:
        print("❌ Retail Stave NOT found.")


if __name__ == "__main__":
    asyncio.run(verify_db())
