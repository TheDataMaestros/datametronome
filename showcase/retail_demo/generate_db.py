#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Generate the Retail demo SQLite database.")
    p.add_argument(
        "--out",
        default="datametronome/podium/data/retail.db",
        help="Output SQLite DB path (relative to repo root by default).",
    )
    p.add_argument(
        "--generate-historical-checks",
        action="store_true",
        help="Also generate historical check results (requires Podium DB and clefs to exist).",
    )
    return p.parse_args()


def main():
    args = parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (project_root / out_path).resolve()

    out_path.parent.mkdir(parents=True, exist_ok=True)

    from showcase.retail_demo.generate_data import create_retail_db

    print(f"Generating Retail demo DB at: {out_path}")
    create_retail_db(str(out_path))

    # Optionally generate historical checks if requested
    if args.generate_historical_checks:
        print("\n📊 Generating historical check results...")
        try:
            from showcase.retail_demo.generate_historical_checks import (
                generate_historical_drift_checks,
                generate_historical_forecast_checks,
            )

            # Get Podium DB path
            podium_db_path = os.environ.get(
                "DATAMETRONOME_DATABASE_URL",
                str(
                    project_root
                    / "datametronome"
                    / "podium"
                    / "data"
                    / "datametronome.db"
                ),
            )
            if podium_db_path.startswith("sqlite"):
                podium_db_path = podium_db_path.split("///")[-1]

            # Default clef IDs (will be updated if clefs exist)
            drift_clef_id = os.environ.get("DRIFT_CLEF_ID", "clef-c72e3cac12e3")
            forecast_clef_id = os.environ.get("FORECAST_CLEF_ID", "clef-c26457fc085f")

            # Try to get clef IDs from API if available
            try:
                import json
                import urllib.request

                api_base = os.environ.get("PODIUM_BASE_URL", "http://localhost:8000")
                response = urllib.request.urlopen(
                    f"{api_base}/api/v1/clefs/", timeout=2
                )
                clefs = json.loads(response.read().decode())
                for clef in clefs:
                    name = clef.get("name", "")
                    if "Drift" in name and "Distribution" in name:
                        drift_clef_id = clef.get("id", drift_clef_id)
                    elif "Anomaly" in name and "Forecast" in name:
                        forecast_clef_id = clef.get("id", forecast_clef_id)
            except Exception:
                # API not available, use defaults
                pass

            print(f"  Generating drift checks for: {drift_clef_id}")
            generate_historical_drift_checks(podium_db_path, drift_clef_id)
            print(f"  Generating forecast checks for: {forecast_clef_id}")
            generate_historical_forecast_checks(podium_db_path, forecast_clef_id)
            print("✅ Historical checks generated successfully")
        except Exception as e:
            print(f"⚠️  Could not generate historical checks: {e}")
            print("   (This is optional - clefs may not exist yet)")


if __name__ == "__main__":
    main()
