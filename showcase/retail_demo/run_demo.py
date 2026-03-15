#!/usr/bin/env python3
"""
Retail Data Showcase
-------------------
Runs the comprehensive DataMetronome demo using synthetic retail data.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
# Add podium source to path
sys.path.append(str(PROJECT_ROOT / "datametronome" / "podium"))

from datametronome_podium.services.clef_executor import (  # noqa: E402
    ClefExecutor,
)
from datametronome_podium.services.stave_yaml_loader import (  # noqa: E402
    load_staves_from_yaml,
)

# Imports for data generation
try:
    from showcase.retail_demo.generate_data import create_retail_db
except ImportError:
    # If running directly from folder
    sys.path.append(str(Path(__file__).parent))
    from generate_data import create_retail_db  # noqa: E402


def status_icon(status):
    if status == "pass":
        return "✅"
    if status == "fail":
        return "🚨"
    return "⚠️"


async def run_showcase():
    print("\n🎵 DataMetronome Retail Showcase")
    print("=" * 60)

    # 1. Setup Data
    db_path = Path("retail.db").absolute()
    print("\n[1/4] 🏭 Generating Synthetic Retail Data...")
    if db_path.exists():
        os.remove(db_path)
    create_retail_db(str(db_path))

    # Set env var for YAML loader
    os.environ["DB_PATH"] = str(db_path)

    # 2. Load Configuration
    print("\n[2/4] 📖 Loading Configuration from YAML...")
    yaml_path = Path(__file__).parent / "retail.yaml"
    staves, clefs = load_staves_from_yaml(yaml_path)

    stave = staves[0]
    print(f"      Loaded Stave: {stave.name} ({stave.data_source_type})")
    print(f"      Loaded {len(clefs)} Clefs:")
    for c in clefs:
        print(f"      - {c.name} ({c.check_type})")

    # 3. Execute Checks
    print("\n[3/4] 🚀 Executing Checks (Brain Engine)...")
    executor = ClefExecutor()
    results = []

    print("      Running checks...")
    start_time = datetime.now()

    for clef in clefs:
        print(f"      Running: {clef.name}...", end="", flush=True)
        result = await executor.execute_clef(clef, stave)
        results.append(result)

        print(f" {status_icon(result.status)}")

    duration = (datetime.now() - start_time).total_seconds()

    # 4. Report
    print("\n[4/4] 📊 Monitoring Report")
    print("=" * 60)
    print(f"Target: {stave.name}")
    print(f"Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cost:   {duration:.2f}s")
    print("-" * 60)

    for res in results:
        if res.status == "pass":
            color_code = "\033[92m"  # Green
        elif res.status == "warn":
            color_code = "\033[93m"  # Yellow
        else:
            color_code = "\033[91m"  # Red
        reset_code = "\033[0m"

        icon = status_icon(res.status)
        print(f"{icon} {color_code}{res.status.upper():<5}{reset_code} | {res.message}")
        if res.metadata:
            # Print relevant metadata
            filtered_meta = {
                k: v
                for k, v in res.metadata.items()
                if k not in ["model_info", "stats_metadata"]
            }
            print(f"          {filtered_meta}")
            if "p_value" in res.metadata:
                print(f"          p-value: {res.metadata['p_value']:.4f}")

    print("=" * 60)

    # Interpret Findings
    print("\n🧐 Findings Analysis:")
    failures = [r for r in results if r.status == "fail"]
    if failures:
        print(f"Found {len(failures)} critical issues!")
        drift_fail = any("Drift" in r.message for r in failures)
        forecast_fail = any("Anomaly Detected" in r.message for r in failures)

        if drift_fail:
            print(
                " -> 📉 Data Drift Detected! "
                "The pricing bug validation worked. "
                "New order amounts are significantly different from history."
            )
        if forecast_fail:
            print(
                " -> 📉 Volume Anomaly Detected! "
                "The outage validation worked. "
                "Order volume dropped unexpectedly today."
            )
    else:
        print("System Healthy.")


if __name__ == "__main__":
    asyncio.run(run_showcase())
