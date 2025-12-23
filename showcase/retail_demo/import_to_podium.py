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
    podium_db_path = (
        PROJECT_ROOT / "datametronome" / "podium" / "data" / "datametronome.db"
    )
    os.environ["DATAMETRONOME_DATABASE_URL"] = f"sqlite+aiosqlite:///{podium_db_path}"
    os.environ[
        "DATAMETRONOME_SECRET_KEY"
    ] = "dev-secret-key-change-in-production-32-chars"
    return podium_db_path


async def import_demo():
    configure_paths()
    podium_db_path = configure_env()

    from datametronome_podium.core.database import (  # type: ignore # noqa: E402
        get_db,
        init_db,
    )
    from datametronome_podium.services.stave_yaml_loader import (  # type: ignore # noqa: E402
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
            '      export DB_PATH="$(pwd)/datametronome/podium/data/retail.db"'
        )

    result = await import_staves_from_yaml(
        yaml_path=yaml_path,
        db=db,
        resolve_env=True,
        overwrite=False,
    )

    print(f"✅ Import complete: {result}")

    # Generate historical check results for better visualization
    print("\n📊 Generating historical check results...")
    try:
        from showcase.retail_demo.generate_historical_checks import (
            generate_historical_drift_checks,
            generate_historical_forecast_checks,
        )

        # Get clef IDs from database
        clefs_result = await db.query(
            {
                "sql": "SELECT id, name FROM clefs WHERE stave_id = ?",
                "params": ["retail-db-001"],
            }
        )
        drift_clef_id = None
        forecast_clef_id = None

        for clef_row in clefs_result:
            clef_id = clef_row.get("id")
            name = clef_row.get("name", "")
            if "Drift" in name and "Distribution" in name:
                drift_clef_id = clef_id
            elif "Anomaly" in name and "Forecast" in name:
                forecast_clef_id = clef_id

        if drift_clef_id:
            print(f"  Generating drift checks for: {drift_clef_id}")
            generate_historical_drift_checks(str(podium_db_path), drift_clef_id)
        if forecast_clef_id:
            print(f"  Generating forecast checks for: {forecast_clef_id}")
            generate_historical_forecast_checks(str(podium_db_path), forecast_clef_id)
        print("✅ Historical checks generated successfully")
    except Exception as e:
        print(f"⚠️  Could not generate historical checks: {e}")
        print("   (This is optional - continuing anyway)")


if __name__ == "__main__":
    asyncio.run(import_demo())
