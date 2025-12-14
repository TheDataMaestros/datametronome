# Check System Implementation Action Plan

**Date**: November 30, 2025
**Priority**: CRITICAL - Core functionality
**Status**: Assessment Complete

---

## 🔍 Current State Assessment

### ✅ What's Already Implemented

1. **Core Infrastructure** ✅
   - `ClefExecutor` class exists and routes to handlers
   - `CheckResult` dataclass with proper structure
   - API endpoints for check execution (`POST /clefs/{id}/run-now`)
   - Result persistence to database
   - Severity mapping (pass/warn/fail → Harmony/Dissonance/Cacophony)

2. **Level 1 Checks - Partially Complete** ⚠️
   - ✅ `row_count` - **FULLY IMPLEMENTED** (lines 1035-1120)
   - ✅ `freshness` - **FULLY IMPLEMENTED** (lines 1293-1448)
   - ⚠️ `column_values` - **PARTIALLY IMPLEMENTED** (lines 912-1033)
     - ✅ Supports `if_null` condition
     - ❌ Missing: `if_not_unique`, `if_not_in`, `range_check` variants
     - ❌ Missing: Proper condition string parsing per TDD spec

3. **Level 2-4 Checks** ❌
   - All return mock results (not production-ready)

---

## 🎯 Critical Gaps Identified

### 1. `column_values` Check - Incomplete Implementation

**Current State**: Only supports `if_null > X%` condition

**TDD Specification** (from `docs/TDD_Clefs.md`):
```yaml
check: column_values
  column: (str) The column to validate
  fail: (str) A condition string, e.g.,
    - "if_null > 5%"
    - "if_not_unique > 0"
    - "if_not_in: ['A', 'B', 'C'] > 0"
```

**What's Missing**:
- `if_not_unique` - Check for duplicate values
- `if_not_in` - Check values not in allowed list
- Proper condition string parser that handles all variants
- Support for percentage-based thresholds

### 2. Condition Evaluation Logic

**Current State**: Basic numeric evaluation exists (`_evaluate_condition_numeric`)

**Issues**:
- Doesn't properly parse TDD condition strings like `"if_null > 5%"`
- Doesn't handle `if_not_in: ['A', 'B'] > 0` syntax
- Needs robust parsing for all condition types

### 3. Testing & Validation

**Missing**:
- Unit tests for each check handler
- Integration tests with real databases
- Edge case handling (empty tables, null values, etc.)

---

## 📋 Implementation Plan

### Phase 1: Complete Level 1 Checks (IMMEDIATE - 1-2 days)

#### Task 1.1: Enhance `column_values` Check Handler
**Priority**: CRITICAL
**Estimated Time**: 4-6 hours

**Requirements**:
1. Support all TDD-specified conditions:
   - `if_null > X%` ✅ (already works)
   - `if_not_unique > 0` ❌ (needs implementation)
   - `if_not_in: ['val1', 'val2'] > 0` ❌ (needs implementation)

2. Build proper condition parser:
   ```python
   def parse_condition(condition_str: str) -> Condition:
       # Parse: "if_null > 5%" -> Condition(type="if_null", operator=">", value=0.05)
       # Parse: "if_not_in: ['A', 'B'] > 0" -> Condition(type="if_not_in", values=['A','B'], operator=">", value=0)
   ```

3. Generate appropriate SQL queries for each condition type:
   - `if_null`: `COUNT(*) WHERE column IS NULL`
   - `if_not_unique`: `SELECT column, COUNT(*) FROM table GROUP BY column HAVING COUNT(*) > 1`
   - `if_not_in`: `COUNT(*) WHERE column NOT IN (...)`

**Files to Modify**:
- `datametronome/podium/datametronome_podium/services/clef_executor.py`
  - Enhance `_execute_column_values_check` method
  - Add condition parsing utilities
  - Add SQL generation for each condition type

#### Task 1.2: Fix Condition Evaluation
**Priority**: HIGH
**Estimated Time**: 2-3 hours

**Requirements**:
1. Create robust condition parser that handles:
   - Percentage values (`> 5%`)
   - List values (`if_not_in: ['A', 'B']`)
   - Multiple operators (`>`, `<`, `>=`, `<=`, `==`, `!=`)
   - Complex conditions

2. Ensure `row_count` and `freshness` use proper condition evaluation

**Files to Modify**:
- `datametronome/podium/datametronome_podium/services/clef_executor.py`
  - Enhance `_evaluate_condition` method
  - Add `parse_condition_string` utility
  - Test with various condition formats

#### Task 1.3: Add Comprehensive Tests
**Priority**: HIGH
**Estimated Time**: 3-4 hours

**Requirements**:
1. Unit tests for each Level 1 check handler
2. Test condition parsing with edge cases
3. Integration tests with SQLite (in-memory)
4. Test error handling (missing config, invalid SQL, etc.)

**Files to Create**:
- `datametronome/podium/tests/test_clef_executor_level1.py`
- `datametronome/podium/tests/test_condition_parsing.py`

---

### Phase 2: Validate & Fix Existing Implementations (1 day)

#### Task 2.1: Test `row_count` Check
- Test with various condition strings
- Test edge cases (empty table, very large counts)
- Verify condition evaluation works correctly

#### Task 2.2: Test `freshness` Check
- Test with various duration formats
- Test with different timestamp formats
- Verify age calculation is correct

#### Task 2.3: End-to-End Testing
- Create test clefs via API
- Execute checks via API
- Verify results are stored correctly
- Test UI integration

---

### Phase 3: Documentation & Examples (0.5 days)

#### Task 3.1: Update Documentation
- Document all supported condition formats
- Add examples for each check type
- Create troubleshooting guide

#### Task 3.2: Add Example Configurations
- Add example YAML files for each Level 1 check
- Add example API requests/responses

---

## 🚀 Quick Start: Immediate Actions

### Step 1: Fix `column_values` Check (Start Here)

The most critical gap is the incomplete `column_values` implementation. Here's what needs to be done:

1. **Create condition parser utility**:
```python
# Add to clef_executor.py
def parse_column_values_condition(condition_str: str) -> dict:
    """
    Parse condition strings like:
    - "if_null > 5%"
    - "if_not_unique > 0"
    - "if_not_in: ['A', 'B', 'C'] > 0"
    """
    # Implementation needed
```

2. **Enhance `_execute_column_values_check`**:
   - Detect condition type (if_null, if_not_unique, if_not_in)
   - Generate appropriate SQL query
   - Execute and evaluate results
   - Return proper CheckResult

3. **Test thoroughly**:
   - Create test cases for each condition type
   - Test with real database data
   - Verify results match expectations

---

## 📊 Success Criteria

### Phase 1 Complete When:
- ✅ All three Level 1 checks (`row_count`, `freshness`, `column_values`) fully implemented
- ✅ All TDD-specified condition formats supported
- ✅ Unit tests passing for all Level 1 checks
- ✅ Can create and execute Level 1 checks via API
- ✅ Results properly stored and retrievable

### Phase 2 Complete When:
- ✅ All existing implementations tested and validated
- ✅ Edge cases handled properly
- ✅ Error messages are clear and helpful
- ✅ Performance is acceptable (< 1s for simple checks)

---

## 🔗 Reference Documents

- **TDD Specification**: `docs/TDD_Clefs.md` - Lines 71-94 (Level 1 checks)
- **Current Implementation**: `datametronome/podium/datametronome_podium/services/clef_executor.py`
- **API Endpoints**: `datametronome/podium/datametronome_podium/api/v1/endpoints/clef_actions.py`

---

## 💡 Recommendations

1. **Start with `column_values`** - This is the biggest gap and most commonly used
2. **Test incrementally** - Build one condition type at a time, test thoroughly
3. **Use TDD approach** - Write tests first, then implement
4. **Document as you go** - Update examples and docs as you implement

---

**🎵 Let's get the core check system rock-solid!**

