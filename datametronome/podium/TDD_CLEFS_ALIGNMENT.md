# TDD Clefs Alignment Analysis

## Overview
This document compares our current Clef implementation with the TDD Clefs specification and outlines the necessary changes to achieve full alignment.

## Key Differences Found

### 1. **Data Structure Mismatch**
**TDD Specification:**
```yaml
clef:
  owner: "@team-name"
  table: "public.users"
  checks:
    - check: row_count
      name: "Daily row count check"
      warn: "> 5000"
      fail: "< 1000"
```

**Current Implementation:**
```yaml
clefs:
  - id: "clef-001"
    stave_id: "stave-001"
    name: "Daily row count check"
    check_type: "volume_check"
    config:
      table: "users"
      expected_min: 1000
      expected_max: 5000
```

### 2. **Check Type Naming**
**TDD Specification:**
- `row_count`
- `freshness`
- `column_values`
- `forecast`
- `data_profile_drift`
- `lookup_validation`
- `python`

**Current Implementation:**
- `volume_check` (should be `row_count`)
- `freshness_check` (should be `freshness`)
- `null_check`, `range_check`, `pattern_check` (should be `column_values`)
- `forecast` ✓ (matches)
- `drift_detection` (should be `data_profile_drift`)
- `lookup_validation` ✓ (matches)
- `custom_python` (should be `python`)

### 3. **Severity Mapping**
**TDD Specification:**
```python
class CheckResult:
    status: Literal["pass", "warn", "fail"]
    observed_value: Any
    message: str
    metadata: dict = {}

# Mapping:
# pass -> Harmony
# warn -> Dissonance
# fail -> Cacophony
```

**Current Implementation:**
```python
class CheckResult:
    severity: SeverityLevel  # Direct Harmony/Dissonance/Cacophony
    message: str
    details: Dict[str, Any]
    check_value: float | None
```

### 4. **Check Configuration Structure**
**TDD Specification:**
```yaml
- check: row_count
  name: "Daily row count check"
  warn: "> 5000"
  fail: "< 1000"
```

**Current Implementation:**
```yaml
- check_type: "volume_check"
  config:
    table: "users"
    expected_min: 1000
    expected_max: 5000
  severity_config:
    warn: "> 5000"
    fail: "< 1000"
```

### 5. **Tier Organization**
**TDD Specification:**
- **Level 1:** Declarative Checks (row_count, freshness, column_values)
- **Level 2:** Intelligent Checks (forecast, data_profile_drift)
- **Level 3:** Advanced Declarative Checks (lookup_validation)
- **Level 4:** Custom Code (python)

**Current Implementation:**
- **Tier 1:** Simple Declarative (null_check, range_check, etc.)
- **Tier 2:** Advanced Declarative (reconciliation, freshness_check, etc.)
- **Tier 3:** Intelligent (forecast, drift_detection, anomaly_detection)
- **Tier 4:** Custom Python (custom_python, custom_sql)

## Required Changes

### 1. Update Check Types
- Rename `volume_check` → `row_count`
- Rename `freshness_check` → `freshness`
- Consolidate `null_check`, `range_check`, `pattern_check` → `column_values`
- Rename `drift_detection` → `data_profile_drift`
- Rename `custom_python` → `python`
- Remove `custom_sql` (not in TDD)

### 2. Update CheckResult Model
- Change `severity: SeverityLevel` → `status: Literal["pass", "warn", "fail"]`
- Change `details` → `metadata`
- Add `observed_value: Any`
- Keep `message: str`

### 3. Update Configuration Structure
- Move severity conditions (`warn`, `fail`) to top level
- Simplify `config` structure to match TDD specifications
- Remove `severity_config` (redundant with top-level warn/fail)

### 4. Update YAML Structure
- Support both formats:
  - **Legacy:** Individual clef objects
  - **TDD Compliant:** `clef.checks` array structure

### 5. Update Tier Organization
- Align with TDD levels instead of custom tiers
- Update tier descriptions and mappings

## Benefits of Alignment

1. **Consistency:** Matches the official TDD specification
2. **Clarity:** Simpler configuration structure
3. **Standards:** Follows established patterns
4. **Maintainability:** Easier to understand and extend
5. **Documentation:** Aligns with existing documentation

## Implementation Plan

1. ✅ Update check type names and mappings
2. ✅ Update CheckResult model to match TDD
3. ✅ Update configuration structure
4. ✅ Update YAML loader to support both formats
5. ✅ Update examples and tests
6. ✅ Update documentation

## Backward Compatibility

We'll maintain backward compatibility by:
- Supporting both old and new configuration formats
- Providing migration utilities
- Deprecating old formats with warnings
- Gradual transition to TDD-compliant format
