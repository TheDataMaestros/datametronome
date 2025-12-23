# 🎓 DataMetronome End-to-End Tutorial: Retail Monitoring

Welcome to the comprehensive tutorial for **DataMetronome**! In this guide, we will set up a complete data observability pipeline for a fictional retail company, "MetronomeStore".

We will cover:
1.  **Level 1 Checks**: Basic declarative monitoring (Reference Checks, Nulls, Volume).
2.  **Level 2 Checks**: Advanced ML-powered inspection (Forecasting & Drift Detection) using the **Brain Library** 🧠.
3.  **Declarative Configuration**: Managing checks as code (YAML).

---

## 🏗️ 1. The Scenario

You are the Data Engineer for MetronomeStore. You manage a local SQLite database with two critical tables:
*   `users`: Customer data (should have valid emails, steady growth).
*   `orders`: Transaction data (should follow seasonal volume, consistent order amounts).

You suspect that a recent deployment has caused:
1.  **Data Drift**: A pricing bug might have inflated order amounts.
2.  **Volume Anomaly**: An outage might have dropped today's order count.

We will use DataMetronome to detect these issues automatically.

---

## 🛠️ 2. Environment Setup

First, ensure you have the project installed.

```bash
# Clone and install dependencies
git clone https://github.com/datametronome/datametronome.git
cd datametronome
make install
```

We have prepared a showcase script that:
1.  Generates a synthetic `retail.db` with 60 days of history.
2.  Injects the anomalies for "today".

Generate the data:
```bash
# Generate the retail database with synthetic data
make retail-db
# Or directly:
python3 showcase/retail_demo/generate_db.py --out datametronome/podium/data/retail.db
```

> **Note**: The `import_to_podium.py` script (used in step 4) automatically generates historical check results, so you'll see rich graphs with past data when viewing checks in the UI.

---

## 📝 3. Defining the Stave (Configuration)

In DataMetronome, a **Stave** is a data source configuration, and **Clefs** are the checks applied to it. We define these declaratively in YAML.

Create or inspect `showcase/retail_demo/retail.yaml`:

```yaml
staves:
  - id: retail-db-001
    name: "Retail Production DB (SQLite)"
    data_source_type: "sqlite"
    connection_config:
      path: "${DB_PATH:-retail.db}"

clefs:
  # --- Level 1: Health Checks ---
  - name: "User Email Integrity"
    stave_id: retail-db-001
    check_type: "column_values"
    config:
      table: "users"
      column: "email"
      rule: "no_nulls"
      threshold: 0.05 # Allow 5% nulls

  # --- Level 2: Brain Intelligence 🧠 ---

  # 1. Forecasting: Did order volume drop unexpectedly?
  - name: "Order Volume Anomaly"
    stave_id: retail-db-001
    check_type: "forecast"
    config:
      # SARIMA model requires timestamp and numeric value
      query: |
        SELECT date(created_at) as day_ts, COUNT(*) as order_count
        FROM orders GROUP BY date(created_at) ORDER BY day_ts ASC
      timestamp_column: "day_ts"
      value_column: "order_count"

  # 2. Drift Detection: Did the distribution of order amounts change?
  - name: "Order Amount Drift"
    stave_id: retail-db-001
    check_type: "data_profile_drift"
    config:
      table: "orders"
      column: "amount"
      # Compare Today vs Last 30 Days using Kolmogorov-Smirnov test
      baseline_condition: "created_at BETWEEN date('now', '-30 days') AND date('now', '-1 day')"
      current_condition: "created_at >= date('now', '-1 day')"
      critical_p_value: 0.05
```

---

## 🚀 4. Running the Checks

We can use the **ClefExecutor** to parse this YAML and run the checks against our database.

Run the showcase runner:

```bash
python3 showcase/retail_demo/run_demo.py
```

### What to Expect

You should see an output similar to this:

```text
[3/4] 🚀 Executing Checks (Brain Engine)...
      Running checks...
      Running: User Email Integrity... ✅
      Running: Significant Order Volume... ✅
      Running: Order Volume Anomaly (Forecast)... 🚨
      Running: Order Amount Drift (Distribution)... 🚨

[4/4] 📊 Monitoring Report
============================================================
✅ PASS  | User Email Integrity
✅ PASS  | Significant Order Volume
🚨 FAIL  | Anomaly Detected: Value 10.00 (Expected range: [65.00, 95.00])
🚨 FAIL  | Drift Detected: p-value 0.0000 (Threshold: 0.05)
```

### Analysis
1.  **Email Integrity (Passed)**: The null rate was within the 5% threshold.
2.  **Order Volume (Failed)**: The Forecast check expected ~80 orders based on historical trends but saw only 10 (our simulated outage).
3.  **Amount Drift (Failed)**: The Drift check detected a statistically significant difference in order amounts today compared to the last 30 days (our simulated pricing bug).

---

## 🧩 5. Integration

To run this in production:

1.  **Mount your YAMLs**: Place your `retail.yaml` in the `data/staves/` directory of your Podium instance.
2.  **Start Podium**: `make start-podium`.
3.  **View in UI**: Open the dashboard to see these checks running on a schedule.

The **Scheduler** will automatically pick up the YAML configuration, schedule the checks, and the **Brain** libraries will persist the models and detect anomalies in real-time.

---

## 📚 Further Reading

- [Stave Configuration Guide](services/stave_yaml_loader.py) (Source)
- [Brain Forecasting Implementation](../../datametronome/brain/base/README.md)
- [Quick Start Guide](quickstart.md)
