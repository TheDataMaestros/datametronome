

### **Technical Design Document: The `Clef` and Check Architecture**

**Version:** 2.1
**Date:** August 14, 2025

#### **1. Purpose and Core Principles**

The `Clef` is a configuration object that defines the set of rules to be applied to a `Stave`. Its design is guided by these principles:

1.  **Declarative:** The user should define *what* they want to check, not *how* the check is executed.
2.  **Expressive:** The architecture must support a wide spectrum of checks, from simple validations to complex, multi-system orchestrations.
3.  **Extensible:** The system must be designed to allow new check types to be added (both internally and via plugins) without requiring changes to the core execution logic.
4.  **Clear Severity:** The outcome of any check must be classifiable into a clear severity level (`Harmony`, `Dissonance`, `Cacophony`).

#### **2. The `Clef` Data Structure**

A `Clef` is a dictionary defined within a `Stave`.

```yaml
clef:
  # (Optional) Metadata for the entire rule set
  owner: "@team-name"
  # (Optional) Default context for simple checks, reducing repetition.
  # Placeholders like {table} in a check's query will be substituted with this value.
  table: "public.users"

  # The list of individual check objects to be executed for this Stave.
  checks:
    - # ... Check Object 1 ...
    - # ... Check Object 2 ...
```

#### **3. The Generic Check Object**

Every item in the `checks` list is a dictionary that must conform to a base structure.

```yaml
- check: <check_type_name>   # REQUIRED. The unique identifier for the check (e.g., "row_count").
  name: "A human-readable description of this specific check's purpose." # Optional but recommended.
  # ... other keys specific to the check_type ...
```

#### **4. The Check Execution and Severity Model**

The Podium's check orchestrator will implement a standard execution pattern for every check.

1.  **Instantiation:** The orchestrator looks up the `check_type_name` in its **Check Registry** to find the handler class responsible for this check.
2.  **Execution:** The orchestrator calls the handler's `execute()` method, passing it the full check configuration and the necessary context (e.g., connected `DataPulse` instances).
3.  **Result Object:** The `execute()` method **must** return a standardized `CheckResult` object.

    ```python
    # A Pydantic model representing the outcome
    class CheckResult:
        status: Literal["pass", "warn", "fail"]
        observed_value: Any
        message: str
        metadata: dict = {} # For storing proof of failure (e.g., failing rows)
    ```

4.  **Severity Mapping:** The orchestrator maps the `CheckResult.status` to the final severity level:
    *   `pass` -> **Harmony**
    *   `warn` -> **Dissonance**
    *   `fail` -> **Cacophony**

#### **5. Detailed Specification of Check Types**

This section defines the contract for each check type, including its specific configuration keys and behavior.

##### **Level 1: Declarative Checks**

*   **`check: row_count`**
    *   **Description:** Checks the total number of rows in the `clef.table`.
    *   **Keys:**
        *   `warn`: (str) A condition string (e.g., `"> 5000"`, `"between 1000 and 2000"`) that triggers a `warn` status.
        *   `fail`: (str) A condition string that triggers a `fail` status.
    *   **Execution:** The handler generates a `SELECT count(*) FROM {table}` query, executes it, and compares the result against the `warn` and `fail` conditions.

*   **`check: freshness`**
    *   **Description:** Checks the time elapsed since the latest timestamp in a column.
    *   **Keys:**
        *   `column`: (str) The timestamp column to check.
        *   `warn`: (str) A duration string (e.g., `"> 12 hours"`) that triggers a `warn` status.
        *   `fail`: (str) A duration string that triggers a `fail` status.
    *   **Execution:** The handler generates a `SELECT MAX({column}) FROM {table}` query, calculates the difference from the current time, and compares it against the duration strings.

*   **`check: column_values`**
    *   **Description:** Performs validations on the values within a single column.
    *   **Keys:**
        *   `column`: (str) The column to validate.
        *   `fail`: (str) A condition string, e.g., `"if_null > 5%"`, `"if_not_unique > 0"`, `"if_not_in: ['A', 'B', 'C'] > 0"`.
    *   **Execution:** The handler generates the appropriate aggregate SQL query (e.g., `COUNT(*) WHERE {column} IS NULL`) to test the condition.

##### **Level 2: Intelligent Checks**

*   **`check: forecast`**
    *   **Description:** Uses a time-series model to detect if a metric's value is anomalous compared to its history.
    *   **Keys:**
        *   `metric`: (str) The metric to analyze (e.g., `"row_count"`).
        *   `strategy`: (dict) Parameters for the forecasting model, e.g., `{"model": "sarima", "confidence": 99}`.
    *   **Execution:** The handler fetches historical metric data from the `profile_history` table, passes it to the `brain-advanced` package, and compares the current value to the returned confidence interval.

*   **`check: data_profile_drift`**
    *   **Description:** Uses a statistical test to detect changes in a column's distribution.
    *   **Keys:**
        *   `column`: (str) The column to analyze.
        *   `strategy`: (dict) Parameters for the statistical test, e.g., `{"test": "kolmogorov_smirnov", "critical_p_value": 0.05}`.
    *   **Execution:** The handler fetches reference and comparison distribution profiles from storage, passes them to the `brain-base` package, and evaluates the resulting p-value.

##### **Level 3: Advanced Declarative Checks**

*   **`check: lookup_validation`**
    *   **Description:** The primary tool for declarative, cross-system integrity validation.
    *   **Keys:**
        *   `lookup`: (dict) A block defining the `pulse`, `query`, and `key_column` for the "driver" dataset.
        *   `validation`: (dict) A block defining the `pulse`, templated `query` (with `{{ lookup_keys }}`), and `key_column` for the "validation" dataset.
        *   `enforce`: (str) The assertion to check (e.g., `"existence_for_all"`).
    *   **Execution:** The handler orchestrates the two-step fetch, data passing, and final comparison.

##### **Level 4: Custom Code**

*   **`check: python`**
    *   **Description:** A secure "escape hatch" for developers.
    *   **Keys:**
        *   `script_path`: (str) The relative path from the project root to a `.py` file.
        *   `params`: (dict, optional) A dictionary of parameters to be passed to the script.
    *   **Execution:** The handler dynamically imports the `async def run_check(pulses, params)` function from the specified file, injects the necessary context (connected Pulses and params), and executes it. The list returned by the function determines the outcome.

You are correct. Explicitly framing the check architecture as a tiered model within the main TDD is a crucial clarification. It communicates the project's design philosophy and user-centric approach more effectively than just listing the check types.

Here is the updated, final TDD that integrates this tiered concept directly into its core specifications.

---

### **Technical Design Document (TDD): DataMetronome**

**Version:** 2.2 (Final)
**Date:** August 14, 2025

#### **1. Overall Architecture**

The system is a decoupled client-server architecture.

1.  **The Podium (Backend):** A headless FastAPI application. It is the single source of truth for logic and state.
2.  **The UI (Frontend):** A standalone web application that acts as a pure client to the Podium's API.
3.  **The Storage Layer:** A database (default: SQLite) that is accessed *only* by the Podium. It stores configuration, run history, and the historical metrics required for intelligent checks.

#### **2. Package & Repository Naming Convention**

*   **Official Project Name:** **DataMetronome**
*   **GitHub Repository Name:** `datametronome`
*   **Core Backend Package:** `datametronome-podium`
*   **Default UI Package:** `datametronome-ui-nuxt`
*   **Connector Interface Package:** `metronome-pulse-core`
*   **Connector Packages:** `metronome-pulse-postgres`, `metronome-pulse-api`, etc.

#### **3. Component Specifications**

##### **3.1 The Podium (`datametronome-podium`)**
*   **Responsibilities:**
    1.  **API Server & Authentication:** Exposes a secure, token-authenticated (JWT) API using FastAPI.
    2.  **Configuration & Credential Management:** Manages the hybrid configuration model (YAML + dynamic) and all secrets.
    3.  **Stateful Metric Collection:** For every Stave run, computes and persists key metrics (profiles, distributions) to the `profile_history` table.
    4.  **Check Orchestration:** Executes checks based on their type, as defined by the **Tiered Check Architecture** (see section 4).
    5.  **Scheduler & Job Queue:** Manages scheduled checks (APScheduler) and handles on-demand requests via an internal, asynchronous job queue (`asyncio.Queue`).
    6.  **Plugin System:** Discovers and loads optional plugins (e.g., `datametronome-dbt-plugin`) via `entry_points`.

##### **3.2 The UI (`datametronome-ui-nuxt`)**
*   **Responsibilities:** Provides the tiered configuration UX using shared component patterns, manages JWT authentication via Pinia, and orchestrates authenticated calls to the Podium API. Critically, its "Create Check" interface **must** guide the user through the **Tiered Check Architecture**, presenting simple options first and progressively revealing more complex check types.

##### **3.3 The DataPulse Ecosystem**
*   **Core Principle:** All connectors are independent, `pip` installable, async-first libraries that manage their own connection pools.
*   **Contract:** Each connector must implement the interfaces defined in `metronome-pulse-core` and the async context manager protocol.

#### **4. The `Clef` and the Tiered Check Architecture**

The `Clef` defines the set of rules for a `Stave`. The power of the system comes from its support for a spectrum of check types, each designed for a different user persona and level of complexity.

##### **Tier 1: Declarative Checks**
*   **Persona:** All Users (Analysts, Ops, Engineers).
*   **Goal:** Simple, no-code data hygiene on a single data source.
*   **Checks:** `row_count`, `freshness`, `schema`, `column_values`.
*   **Implementation:** The Podium executes simple, templated SQL queries against the Stave's source. The UI will present a simple form for each of these checks.

##### **Tier 2: Intelligent Checks**
*   **Persona:** Analysts, Data Scientists.
*   **Goal:** Proactive, low-config anomaly and drift detection.
*   **Checks:** `forecast`, `data_profile_drift`.
*   **Implementation:** The Podium fetches historical metrics from its storage layer. It passes this time-series data to a function in the `datametronome-brain-advanced` package, which contains the statistical models. The UI will allow users to select a metric and tune key model parameters.

##### **Tier 3: Advanced Declarative Checks**
*   **Persona:** Power Users, Data Analysts, Analytics Engineers.
*   **Goal:** Complex, multi-source logic without writing Python.
*   **Checks:** `custom_sql`, `reconciliation`, `lookup_validation`.
*   **Implementation:** The Podium orchestrates the fetching of data from one or more `DataPulse` connectors and performs the comparison or validation. The `lookup_validation` check is the primary tool for declarative, cross-system integrity validation. The UI will provide a guided, multi-step form for these checks.

##### **Tier 4: Custom Code (Developer Escape Hatch)**
*   **Persona:** Data Engineers, Software Engineers.
*   **Goal:** Ultimate flexibility for any business logic that cannot be expressed declaratively.
*   **Check:** `python`.
*   **Implementation:** The configuration **must** use a `script_path` key to reference a `.py` file. The Podium will import a designated `async def run_check(pulses, params)` function from this file and inject the necessary context. This provides a secure, testable, and maintainable workflow managed through version control.

#### **5. Development Roadmap**

*   **Phase 1: The Headless Core (MVP):** Build the Podium with its API, secure credential management, and core connectors. Implement the **Tier 1** and **Tier 3** check types.
*   **Phase 2: The Integrated Experience:** Build the UI with a smooth, tiered interface for creating checks. Implement the scheduler and job queue. Implement the **Tier 4** (`python`) check.
*   **Phase 3: Intelligence and Integration:** Build the stateful metric collection. Develop `datametronome-brain-advanced` and implement the **Tier 2** checks. Build the `dbt` and `GX` plugins.
*   **Phase 4: Hardening & Expansion:** Implement local TLS for UI-to-Podium communication. Formalize API versioning and add more connectors.
