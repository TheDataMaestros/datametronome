#!/usr/bin/env python3
"""
Docker showcase bootstrap:
- Generates retail SQLite DB in shared volume
- Imports showcase YAML into Podium (with env interpolation) using the API
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from showcase.retail_demo.generate_data import create_retail_db  # noqa: E402


def wait_for_podium(base_url: str, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    url = f"{base_url}/health"
    last_error = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if 200 <= resp.status < 300:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(2)

    raise RuntimeError(f"Podium not ready after {timeout_s}s: {last_error}")


def post_json(url: str, payload: dict, timeout_s: int = 240) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc


def get_json(url: str, timeout_s: int = 240) -> dict | list:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc


def main() -> None:
    podium_base = os.environ.get("PODIUM_BASE_URL", "http://podium:8001")
    retail_db_path = Path(os.environ.get("RETAIL_DB_PATH", "/app/data/retail.db"))
    yaml_path = Path(
        os.environ.get("SHOWCASE_YAML_PATH", "/app/showcase/retail_demo/retail.yaml")
    )

    retail_db_path.parent.mkdir(parents=True, exist_ok=True)
    if retail_db_path.exists():
        retail_db_path.unlink()

    print(f"[showcase] generating retail db at: {retail_db_path}")
    create_retail_db(str(retail_db_path))

    print(f"[showcase] waiting for podium: {podium_base}")
    wait_for_podium(podium_base)

    print(f"[showcase] importing YAML: {yaml_path}")
    result = post_json(
        f"{podium_base}/api/v1/config/import/yaml/advanced",
        {
            "file_path": str(yaml_path),
            "interpolate_env": True,
            "strict_validation": False,
            "clean": True,
        },
    )

    print(f"[showcase] import result: {result}")
    if not result.get("success", False):
        raise RuntimeError(f"Showcase import failed: {result}")

    print("[showcase] executing imported clefs once (seed UI with results)...")
    clefs = get_json(f"{podium_base}/api/v1/clefs/")  # type: ignore[assignment]
    retail_clefs = [c for c in clefs if c.get("stave_id") == "retail-db-001"]

    # Prefer executing "Level 1" style checks first so the UI has fast wins even if
    # ML dependencies are missing or a single check fails.
    priority = {"column_values": 0, "row_count": 1, "freshness": 2}
    retail_clefs.sort(key=lambda c: priority.get(c.get("check_type") or "", 99))

    executed = 0
    failed = 0

    # Find drift and forecast clef IDs for historical checks generation
    drift_clef_id = None
    forecast_clef_id = None
    for clef in retail_clefs:
        name = clef.get("name", "")
        if "Drift" in name and "Distribution" in name:
            drift_clef_id = clef.get("id")
        elif "Anomaly" in name and "Forecast" in name:
            forecast_clef_id = clef.get("id")

    for clef in retail_clefs:
        clef_id = clef.get("id")
        name = clef.get("name")
        if not clef_id:
            continue
        try:
            # ML checks can take longer on first run (model fitting).
            exec_result = post_json(
                f"{podium_base}/api/v1/scheduler/clefs/{clef_id}/execute",
                {},
                timeout_s=240,
            )
            ok = bool(exec_result.get("success", False))
            executed += 1
            failed += 0 if ok else 1
            print(f"[showcase] executed {name}: {ok}")
        except Exception as exc:
            executed += 1
            failed += 1
            print(f"[showcase] executed {name}: False ({exc})")
        # Give SQLite a tiny breather between runs (avoids bursts of writes).
        time.sleep(0.5)

    print(f"[showcase] executed {executed} clefs (failed={failed})")

    # Generate historical check results for better visualization
    if drift_clef_id or forecast_clef_id:
        print("[showcase] generating historical check results...")
        try:
            from showcase.retail_demo.generate_historical_checks import (
                generate_historical_drift_checks,
                generate_historical_forecast_checks,
            )

            podium_db_path = Path(os.environ.get("DATAMETRONOME_DATABASE_URL", ""))
            if podium_db_path and str(podium_db_path).startswith("sqlite"):
                podium_db_path = Path(str(podium_db_path).split("///")[-1])
            else:
                # Default path in Docker
                podium_db_path = Path("/app/data/datametronome.db")

            if podium_db_path.exists():
                if drift_clef_id:
                    print(f"  Generating drift checks for: {drift_clef_id}")
                    generate_historical_drift_checks(str(podium_db_path), drift_clef_id)
                if forecast_clef_id:
                    print(f"  Generating forecast checks for: {forecast_clef_id}")
                    generate_historical_forecast_checks(
                        str(podium_db_path), forecast_clef_id
                    )
                print("[showcase] ✅ Historical checks generated")
            else:
                print(
                    f"[showcase] ⚠️  Podium DB not found at {podium_db_path}, skipping historical checks"
                )
        except Exception as e:
            print(f"[showcase] ⚠️  Could not generate historical checks: {e}")

    print("[showcase] done")


if __name__ == "__main__":
    main()
