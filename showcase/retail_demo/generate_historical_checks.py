#!/usr/bin/env python3
"""
Generate historical check results for drift detection demo.

Creates past check results showing stable baseline, then drift detection.
"""

import json
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_historical_forecast_checks(
    podium_db_path: str,
    clef_id: str,
    stave_id: str = "retail-db-001",
    days_back: int = 7,
):
    """
    Generate historical forecast check results showing normal behavior, then anomaly.

    Args:
        podium_db_path: Path to the Podium SQLite database
        clef_id: ID of the forecast clef
        stave_id: ID of the stave
        days_back: Number of days of historical checks to create
    """
    conn = sqlite3.connect(podium_db_path)
    cur = conn.cursor()

    # Normal order volume: ~60-80 orders per day (with weekend variation)
    normal_mean = 70.0
    normal_std = 12.0

    # Generate historical checks (most showing normal, last showing anomaly)
    now = datetime.now(timezone.utc)
    check_results = []

    print(f"Generating {days_back} days of historical forecast check results...")

    for day_offset in range(days_back, 0, -1):  # From oldest to newest
        check_timestamp = now - timedelta(days=day_offset)
        check_timestamp = check_timestamp.replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        if day_offset == 1:
            # Today: Anomaly (low volume - outage scenario)
            observed_value = 18.0
            lower_bound = 27.0
            upper_bound = 98.0
            is_anomaly = True
            status = "fail"
            message = f"Anomaly Detected (fallback): Value {observed_value:.2f} (Expected range: [{lower_bound:.2f}, {upper_bound:.2f}])"
            severity = "cacophony"
        else:
            # Historical days: Normal volume
            observed_value = normal_mean + random.gauss(0, normal_std)
            observed_value = max(
                40, min(100, observed_value)
            )  # Keep in reasonable range

            # Calculate bounds around observed (should include it)
            mean = normal_mean
            std = normal_std
            k = 2.5
            lower_bound = mean - (k * std)
            upper_bound = mean + (k * std)

            # Ensure observed is within bounds (normal behavior)
            if observed_value < lower_bound:
                observed_value = lower_bound + 5
            if observed_value > upper_bound:
                observed_value = upper_bound - 5

            is_anomaly = False
            status = "pass"
            message = f"Forecast OK (fallback): Value {observed_value:.2f} (Expected range: [{lower_bound:.2f}, {upper_bound:.2f}])"
            severity = "harmony"

        check_id = (
            f"check-{clef_id}-{check_timestamp.isoformat().replace('+00:00', 'Z')}"
        )

        metadata = {
            "method": "fallback_band",
            "window_size": 30,
            "mean": normal_mean,
            "std": normal_std,
            "k": 2.5,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "observed_value": observed_value,
        }

        check_results.append(
            {
                "id": check_id,
                "stave_id": stave_id,
                "clef_id": clef_id,
                "check_type": "forecast",
                "status": status,
                "message": message,
                "details": json.dumps(metadata),
                "timestamp": check_timestamp.isoformat().replace("+00:00", "Z"),
                "execution_time": random.uniform(0.005, 0.01),
                "anomalies_count": 1 if is_anomaly else 0,
                "severity": severity,
            }
        )

    # Insert all historical checks
    for check in check_results:
        try:
            cur.execute(
                """
                INSERT OR REPLACE INTO checks
                (id, stave_id, clef_id, check_type, status, message, details, timestamp, execution_time, anomalies_count, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check["id"],
                    check["stave_id"],
                    check["clef_id"],
                    check["check_type"],
                    check["status"],
                    check["message"],
                    check["details"],
                    check["timestamp"],
                    check["execution_time"],
                    check["anomalies_count"],
                    check["severity"],
                ),
            )
        except sqlite3.IntegrityError:
            # Skip if already exists
            pass

    conn.commit()
    conn.close()
    print(f"✅ Created {len(check_results)} historical forecast check results")


def generate_historical_drift_checks(
    podium_db_path: str,
    clef_id: str,
    stave_id: str = "retail-db-001",
    days_back: int = 7,
):
    """
    Generate historical check results showing stable baseline, then drift.

    Args:
        podium_db_path: Path to the Podium SQLite database
        clef_id: ID of the drift detection clef
        stave_id: ID of the stave
        days_back: Number of days of historical checks to create
    """
    conn = sqlite3.connect(podium_db_path)
    cur = conn.cursor()

    # Baseline statistics (stable over time - this is the reference distribution)
    baseline_mean = 99.5
    baseline_std = 20.0

    # Generate historical checks showing TRUE DATA DRIFT (gradual distribution shift)
    now = datetime.now(timezone.utc)
    check_results = []

    print(
        f"Generating {days_back} days of historical check results showing gradual drift..."
    )

    for day_offset in range(days_back, 0, -1):  # From oldest to newest
        check_timestamp = now - timedelta(days=day_offset)
        check_timestamp = check_timestamp.replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        # TRUE DRIFT: Gradual distribution shift over time
        # Days 1-5: Stable (no drift)
        # Days 6-7: Gradual shift begins (drift detected)
        # Day 8 (today): Significant shift (strong drift)

        if day_offset >= 5:
            # Early days: Stable distribution (current matches baseline)
            current_mean = baseline_mean + random.gauss(0, 2)  # Small variation
            current_std = baseline_std + random.gauss(0, 1)
            p_value = random.uniform(0.15, 0.85)  # High p-value = no drift
            status = "pass"
            message = f"Stable Distribution: p-value {p_value:.4f} (Threshold: 0.05)"
            severity = "harmony"
            test_statistic = random.uniform(0.05, 0.15)  # Low test statistic
        elif day_offset == 3:
            # Day -2: Slight drift begins (3% shift)
            current_mean = baseline_mean + 3 + random.gauss(0, 1.5)
            current_std = baseline_std + 1 + random.gauss(0, 0.5)
            p_value = random.uniform(0.04, 0.08)  # Borderline drift
            status = "warn"
            message = f"Drift Detected: p-value {p_value:.4f} (Threshold: 0.05)"
            severity = "dissonance"
            test_statistic = random.uniform(0.15, 0.25)
        elif day_offset == 2:
            # Day -1: Moderate drift (8% shift)
            current_mean = baseline_mean + 8 + random.gauss(0, 1.5)
            current_std = baseline_std + 2 + random.gauss(0, 0.5)
            p_value = random.uniform(0.005, 0.02)  # Clear drift
            status = "fail"
            message = f"Drift Detected: p-value {p_value:.4f} (Threshold: 0.05)"
            severity = "cacophony"
            test_statistic = random.uniform(0.25, 0.35)
        else:
            # Day 0 (today): Significant drift (12% shift) - more realistic
            current_mean = baseline_mean + 12 + random.gauss(0, 1.5)
            current_std = baseline_std + 3 + random.gauss(0, 0.5)
            p_value = random.uniform(0.0005, 0.005)  # Strong drift
            status = "fail"
            message = f"Drift Detected: p-value {p_value:.4f} (Threshold: 0.05)"
            severity = "cacophony"
            test_statistic = random.uniform(0.35, 0.45)

        check_id = (
            f"check-{clef_id}-{check_timestamp.isoformat().replace('+00:00', 'Z')}"
        )

        metadata = {
            "test_statistic": test_statistic,
            "p_value": p_value,
            "baseline_size": random.randint(2300, 2400),
            "current_size": random.randint(18, 25),
            "stats_metadata": {
                "alternative": "two-sided",
                "baseline_mean": baseline_mean,  # Baseline stays stable
                "baseline_std": baseline_std,
                "current_mean": current_mean,  # Current distribution shifts
                "current_std": current_std,
            },
        }

        check_results.append(
            {
                "id": check_id,
                "stave_id": stave_id,
                "clef_id": clef_id,
                "check_type": "data_profile_drift",
                "status": status,
                "message": message,
                "details": json.dumps(metadata),
                "timestamp": check_timestamp.isoformat().replace("+00:00", "Z"),
                "execution_time": random.uniform(0.03, 0.08),
                "anomalies_count": 0,
                "severity": severity,
            }
        )

    # Insert all historical checks
    for check in check_results:
        try:
            cur.execute(
                """
                INSERT OR REPLACE INTO checks
                (id, stave_id, clef_id, check_type, status, message, details, timestamp, execution_time, anomalies_count, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check["id"],
                    check["stave_id"],
                    check["clef_id"],
                    check["check_type"],
                    check["status"],
                    check["message"],
                    check["details"],
                    check["timestamp"],
                    check["execution_time"],
                    check["anomalies_count"],
                    check["severity"],
                ),
            )
        except sqlite3.IntegrityError:
            # Skip if already exists
            pass

    conn.commit()
    conn.close()
    print(
        f"✅ Created {len(check_results)} historical check results showing stable baseline"
    )


if __name__ == "__main__":
    # Get paths from environment or use defaults
    podium_db_path = os.environ.get(
        "DATAMETRONOME_DATABASE_URL",
        "datametronome/podium/data/datametronome.db",
    )

    # Extract path from sqlite+aiosqlite:/// URL format if needed
    if podium_db_path.startswith("sqlite"):
        podium_db_path = podium_db_path.split("///")[-1]

    # Get clef ID from command line or environment
    import sys

    if len(sys.argv) > 1:
        clef_id = sys.argv[1]
    else:
        # Try to get from API or use default
        clef_id = os.environ.get("DRIFT_CLEF_ID", "clef-c72e3cac12e3")

    print(f"Using Podium DB: {podium_db_path}")

    # Generate historical checks for both drift and forecast
    if len(sys.argv) > 1:
        clef_id = sys.argv[1]
        if "drift" in sys.argv[1].lower() or "c72e3cac12e3" in sys.argv[1]:
            print(f"Generating drift checks for Clef ID: {clef_id}")
            generate_historical_drift_checks(podium_db_path, clef_id)
        elif "forecast" in sys.argv[1].lower() or "c26457fc085f" in sys.argv[1]:
            print(f"Generating forecast checks for Clef ID: {clef_id}")
            generate_historical_forecast_checks(podium_db_path, clef_id)
        else:
            # Default: generate both
            drift_clef = os.environ.get("DRIFT_CLEF_ID", "clef-c72e3cac12e3")
            forecast_clef = os.environ.get("FORECAST_CLEF_ID", "clef-c26457fc085f")
            print(f"Generating drift checks for Clef ID: {drift_clef}")
            generate_historical_drift_checks(podium_db_path, drift_clef)
            print(f"Generating forecast checks for Clef ID: {forecast_clef}")
            generate_historical_forecast_checks(podium_db_path, forecast_clef)
    else:
        # Default: generate both
        drift_clef = os.environ.get("DRIFT_CLEF_ID", "clef-c72e3cac12e3")
        forecast_clef = os.environ.get("FORECAST_CLEF_ID", "clef-c26457fc085f")
        print(f"Generating drift checks for Clef ID: {drift_clef}")
        generate_historical_drift_checks(podium_db_path, drift_clef)
        print(f"Generating forecast checks for Clef ID: {forecast_clef}")
        generate_historical_forecast_checks(podium_db_path, forecast_clef)
