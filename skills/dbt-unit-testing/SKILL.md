---
name: dbt-unit-testing
description: Proactive skill for creating dbt unit tests. Auto-activates when working with dbt model testing, mock inputs/outputs, or transformation validation. Covers the Model-Inputs-Outputs pattern, format selection (dict/CSV/SQL), BigQuery-specific caveats, and production deployment guidance.
---

# dbt Unit Testing Skill

## Purpose

This skill automatically activates when creating or discussing dbt unit tests. It guides the creation of effective unit tests using dbt's native unit testing framework (dbt Core 1.8+), ensuring that complex transformation logic is verified with mock inputs and expected outputs before deployment.

Unit tests validate **transformation logic in isolation** -- they confirm that given specific input rows, a model produces the expected output rows. They complement schema tests (not_null, unique, relationships) which validate **data quality in production**.

## When This Skill Activates

### User-Triggered Activation

This skill should activate when users:
- **Request unit tests:** "Add unit tests for this model"
- **Discuss transformation testing:** "How do I test this window function logic?"
- **Work with mock data:** "I need to mock inputs for testing"
- **Debug test failures:** "My unit test is failing with unexpected output"
- **Ask about test coverage:** "Which models need unit tests?"

**Keywords to watch for:**
- "unit test", "test logic", "mock inputs", "test transformation"
- "model-inputs-outputs", "expected output", "test fixtures"
- "dbt test --select test_type:unit"
- "dict format", "csv format", "sql format" (in testing context)

### Self-Triggered Activation (Proactive)

**Activate BEFORE writing or reviewing unit tests when:**
- You're about to create a unit test YAML file
- You detect complex transformation logic that should be unit tested
- User asks to "test" a model that contains business logic
- You're reviewing a model with regex, date calculations, window functions, or case statements
- You encounter a `unit_tests:` block in any YAML file

**Example internal triggers:**
- "I'll add tests for this model..." and the model has complex logic -> Activate skill first
- User shows a model with window functions -> Suggest unit tests
- "Let me write a unit test..." -> Check format selection and conventions

## When NOT to Activate

- **Schema tests** (not_null, unique, accepted_values, relationships): Defer to the `dbt-development` skill
- **Test coverage strategy** (which tests to write across a project): Refer to `testing-reference.md` in the dbt-development skill
- **Data quality monitoring** (freshness, volume checks): Outside scope of unit tests
- **Integration/end-to-end testing**: Unit tests are for isolated logic validation only

---

## Instructions

### 1. When to Write Unit Tests

Unit tests are valuable when a model contains **complex transformation logic** that could break silently. Write unit tests for models that include:

| Logic Type | Example | Why Unit Test? |
|---|---|---|
| **Regex extraction** | `regexp_extract(url, r'/product/(\d+)')` | Regex is error-prone and hard to validate visually |
| **Date calculations** | `date_diff(created_at, closed_at, DAY)` | Edge cases around month boundaries, nulls |
| **Window functions** | `row_number() over (partition by customer_id order by updated_at desc)` | Partitioning and ordering logic is subtle |
| **Case statements** | Multi-branch `CASE WHEN` with business rules | Business logic branches need explicit verification |
| **Multi-join logic** | Joining 3+ tables with conditional inclusion | Join conditions can silently drop or duplicate rows |
| **Conditional aggregation** | `sum(case when status = 'active' then amount end)` | Filter conditions within aggregations |
| **Type casting with logic** | `safe_cast` with fallback values | Edge cases in type conversion |
| **Deduplication** | `qualify row_number() over (...) = 1` | Dedup key selection affects which row survives |
| **Pivoting/unpivoting** | Dynamic column generation | Column mapping is fragile |
| **Currency/unit conversion** | Rate application with rounding | Precision and rounding errors |

### 2. When NOT to Write Unit Tests

Do not write unit tests for:

- **Simple ref/source pass-through:** Models that just select columns from a single source without transformation
- **Built-in function wrappers:** `coalesce(field, 'Unknown')`, `lower(email)`, `trim(name)` -- these are already tested by the database engine
- **Pure SQL without business logic:** Simple joins that just combine two tables on a foreign key
- **Materialization-only models:** Models whose purpose is performance (e.g., incremental refresh) rather than logic
- **Models with only rename/recast:** Staging models that only rename columns and cast types

**Rule of thumb:** If the model's SQL could be understood correctly by reading it once, it probably does not need a unit test. If you need to "think through" what the SQL does, it needs a unit test.

---

### 3. The Model-Inputs-Outputs Pattern

Every dbt unit test follows the same pattern:

```
MODEL (what we're testing)
  + INPUTS (mock data fed to the model's dependencies)
  = EXPECTED OUTPUTS (what the model should produce)
```

**How it works:**
1. You specify the **model** to test
2. You provide **mock input rows** for each `ref()` or `source()` the model depends on
3. You define the **expected output rows** the model should produce
4. dbt replaces real tables with your mock data, runs the model, and compares actual vs expected output

**Key concepts:**
- Only mock the inputs relevant to your test case -- you don't need to mock every column
- Columns not included in mocks get default values (NULL for nullable, type-appropriate defaults otherwise)
- Each unit test should test **one specific behavior** -- not the entire model
- Multiple unit tests per model is encouraged and expected

---

### 4. Format Selection

dbt supports three formats for specifying mock data. Choose based on readability and requirements:

#### Dict Format (Default -- Use This First)

Best for: Most cases. Readable, explicit, easy to maintain.

```yaml
unit_tests:
  - name: test_status_classification
    model: int_orders_classified
    given:
      - input: ref('stg_shopify__orders')
        rows:
          - {order_id: 1, status: "fulfilled", total: 100.00}
          - {order_id: 2, status: "pending", total: 50.00}
          - {order_id: 3, status: "cancelled", total: 75.00}
    expect:
      rows:
        - {order_id: 1, status_category: "complete", total: 100.00}
        - {order_id: 2, status_category: "in_progress", total: 50.00}
        - {order_id: 3, status_category: "cancelled", total: 75.00}
```

**Advantages:** Most readable, easy to diff in code review, clear column-value mapping.

**Limitations:** Can become verbose for many columns.

#### CSV Format

Best for: Tabular data with many columns or many rows.

```yaml
unit_tests:
  - name: test_revenue_calculation
    model: int_orders_revenue
    given:
      - input: ref('stg_shopify__orders')
        format: csv
        rows: |
          order_id,quantity,unit_price,discount_pct
          1,10,25.00,0.10
          2,5,50.00,0.00
          3,1,100.00,0.25
    expect:
      format: csv
      rows: |
        order_id,gross_revenue,net_revenue
        1,250.00,225.00
        2,250.00,250.00
        3,100.00,75.00
```

**Advantages:** Compact, easy to read as a table, quick to add rows.

**Limitations:** Harder to spot column alignment issues. String values with commas need quoting.

#### SQL Format

Best for: Complex data setup, ephemeral model dependencies, or when you need database functions.

```yaml
unit_tests:
  - name: test_date_spine_join
    model: fct_daily_active_users
    given:
      - input: ref('stg_app__user_sessions')
        format: sql
        rows: |
          SELECT 1 AS user_id, TIMESTAMP '2024-01-15 10:00:00' AS session_start
          UNION ALL
          SELECT 1 AS user_id, TIMESTAMP '2024-01-15 14:00:00' AS session_start
          UNION ALL
          SELECT 2 AS user_id, TIMESTAMP '2024-01-16 09:00:00' AS session_start
    expect:
      format: sql
      rows: |
        SELECT DATE '2024-01-15' AS activity_date, 1 AS active_users
        UNION ALL
        SELECT DATE '2024-01-16' AS activity_date, 1 AS active_users
```

**Advantages:** Full SQL expressiveness, can use database functions for dates/timestamps, required for mocking ephemeral model dependencies.

**Limitations:** Least readable, harder to maintain, database-specific syntax.

**When SQL format is required:**
- Mocking an **ephemeral model** dependency (ephemeral models have no table to replace)
- Using **database-specific functions** to generate test data (e.g., `GENERATE_DATE_ARRAY` in BigQuery)
- Complex data types that cannot be expressed in dict/CSV format

---

### 5. Writing the Unit Test YAML

#### File Location

Unit test definitions go in the model's schema YAML file or in a dedicated test file:

```
models/
  staging/
    shopify/
      stg_shopify__orders.sql
      stg_shopify__orders.yml        # schema + unit tests here
  integration/
    int_orders_classified.sql
    int_orders_classified.yml        # or here
  warehouse/
    fct_orders.sql
    unit_test_fct_orders.yml         # or in dedicated file (RA convention)
```

#### Full Syntax Reference

```yaml
unit_tests:
  - name: test_<descriptive_name>          # Required. Snake_case, prefix with test_
    description: >                          # Optional but recommended
      Verify that [specific behavior] produces [expected result]
      when given [specific input conditions].
    model: <model_name>                     # Required. The model being tested
    config:
      tags: ["unit-test"]                   # Optional. Useful for selective runs
    given:                                  # Required. List of mock inputs
      - input: ref('<upstream_model>')      # or source('schema', 'table')
        rows:                               # Mock rows for this input
          - {col1: val1, col2: val2}
          - {col1: val3, col2: val4}
      - input: ref('<another_model>')
        rows:
          - {col_a: val_a}
    expect:                                 # Required. Expected output rows
      rows:
        - {result_col1: expected1, result_col2: expected2}
        - {result_col1: expected3, result_col2: expected4}

  - name: test_<another_behavior>           # Multiple tests per model
    model: <model_name>
    given:
      - input: ref('<upstream_model>')
        rows: []                            # Empty input -- tests zero-row handling
    expect:
      rows: []                              # Expect empty output
```

#### Overriding Macros and Vars

```yaml
unit_tests:
  - name: test_with_custom_var
    model: my_model
    overrides:
      vars:
        my_date_var: "2024-01-15"           # Override project vars
      macros:
        my_custom_macro: "hardcoded_value"  # Override macro return values
    given:
      - input: ref('upstream')
        rows:
          - {id: 1}
    expect:
      rows:
        - {id: 1, computed_date: "2024-01-15"}
```

#### Testing Incremental Models

For incremental models, you can provide the "existing" state of the model using `this`:

```yaml
unit_tests:
  - name: test_incremental_merge
    model: fct_orders
    overrides:
      macros:
        is_incremental: true                # Simulate incremental run
    given:
      - input: this                         # The current state of the model
        rows:
          - {order_id: 1, status: "pending", updated_at: "2024-01-01"}
      - input: ref('stg_orders')            # New incoming data
        rows:
          - {order_id: 1, status: "shipped", updated_at: "2024-01-15"}
          - {order_id: 2, status: "pending", updated_at: "2024-01-15"}
    expect:
      rows:
        - {order_id: 1, status: "shipped", updated_at: "2024-01-15"}
        - {order_id: 2, status: "pending", updated_at: "2024-01-15"}
```

---

### 6. Running Unit Tests

#### Execute Unit Tests

```bash
# Run all unit tests in the project
dbt test --select test_type:unit

# Run unit tests for a specific model
dbt test --select test_type:unit,model_name

# Run a specific unit test by name
dbt test --select test_name

# Run unit tests as part of a full build
dbt build --select +my_model   # Runs model + all associated tests

# Run with verbose output for debugging
dbt test --select test_type:unit -v
```

#### The `--empty` Flag

Use `--empty` to validate that unit test YAML parses correctly without actually running against the database:

```bash
dbt test --select test_type:unit --empty
```

This is useful for CI validation of test syntax before merging.

---

### 7. Interpreting Failures

When a unit test fails, dbt shows a diff between expected and actual output:

```
FAIL 1/1 test_status_classification

Failure in unit_test test_status_classification (models/integration/int_orders_classified.yml)

Got 1 result, configured to fail if != 0

  actual                        | expected                      | diff
  {order_id: 1,                 | {order_id: 1,                 |
   status_category: "active"}   |  status_category: "complete"} | !=
```

**How to read the diff:**
- **actual**: What the model actually produced
- **expected**: What you said it should produce
- **diff**: `!=` indicates mismatched rows

**Common failure causes:**
1. **Logic error in the model** -- The model's SQL is wrong. Fix the SQL.
2. **Wrong expected value** -- Your expectation was incorrect. Fix the test.
3. **Missing mock input** -- A dependency wasn't mocked, causing NULLs. Add the missing input.
4. **Row ordering** -- Unit tests compare sets, not ordered lists. Order should not matter, but if it does, check for non-deterministic ordering in the model.
5. **Type mismatch** -- Expected `"100"` (string) but got `100` (integer). Match types exactly.
6. **Precision mismatch** -- Expected `100.00` but got `100.0` or `99.999999`. See BigQuery caveats below.

---

### 8. BigQuery-Specific Caveats

When writing unit tests for BigQuery targets, be aware of these platform-specific behaviors:

#### STRUCT Handling

BigQuery STRUCT types require special handling in unit tests. Use SQL format for STRUCT inputs:

```yaml
unit_tests:
  - name: test_struct_extraction
    model: stg_ga4__events
    given:
      - input: source('google_analytics', 'events')
        format: sql
        rows: |
          SELECT
            'event_1' AS event_id,
            STRUCT('page_view' AS value) AS event_name,
            [STRUCT('page_location' AS key, STRUCT('https://example.com' AS string_value) AS value)] AS event_params
    expect:
      rows:
        - {event_id: "event_1", event_name: "page_view", page_location: "https://example.com"}
```

#### TIMESTAMP Precision

BigQuery TIMESTAMPs have microsecond precision. When comparing timestamps in expected output, match the precision:

```yaml
# Correct -- explicit precision
expect:
  rows:
    - {created_at: "2024-01-15 10:00:00.000000 UTC"}

# Risky -- may fail depending on how the model outputs timestamps
expect:
  rows:
    - {created_at: "2024-01-15 10:00:00"}
```

Use SQL format if timestamp precision is problematic:

```yaml
expect:
  format: sql
  rows: |
    SELECT TIMESTAMP '2024-01-15 10:00:00 UTC' AS created_at
```

#### GEOGRAPHY Type

BigQuery GEOGRAPHY columns cannot be compared directly in dict format. Use SQL format with `ST_GEOGPOINT`:

```yaml
given:
  - input: ref('stg_locations')
    format: sql
    rows: |
      SELECT 1 AS location_id, ST_GEOGPOINT(-122.4194, 37.7749) AS geo_point
```

#### NUMERIC/BIGNUMERIC Precision

BigQuery NUMERIC (38 digits, 9 decimal) and BIGNUMERIC (76 digits, 38 decimal) may cause precision mismatches:

```yaml
# Use explicit cast in SQL format for precision-sensitive comparisons
expect:
  format: sql
  rows: |
    SELECT NUMERIC '123.456789' AS amount
```

#### DATE and DATETIME Formatting

BigQuery distinguishes between DATE, DATETIME, and TIMESTAMP. Ensure your mock data matches the column type:

```yaml
# DATE column
rows:
  - {order_date: "2024-01-15"}

# DATETIME column
rows:
  - {created_datetime: "2024-01-15T10:00:00"}

# TIMESTAMP column (requires timezone)
rows:
  - {created_at: "2024-01-15 10:00:00 UTC"}
```

#### Snowflake-Specific Notes

For projects targeting Snowflake:
- VARIANT columns: Use SQL format with `PARSE_JSON()`
- TIMESTAMP_NTZ vs TIMESTAMP_TZ: Be explicit about timezone handling
- ARRAY columns: Use SQL format with `ARRAY_CONSTRUCT()`

---

### 9. Production Deployment

Unit tests should run in **CI/CD** (development and staging) but typically not in production scheduled jobs:

```bash
# Production job -- exclude unit tests
dbt build --exclude-resource-type unit_test

# CI/CD job -- include unit tests
dbt build --select state:modified+
# (unit tests run automatically when their model is selected)
```

**Rationale:** Unit tests validate logic correctness, which is a development concern. Production jobs should run schema tests (data quality) but not re-validate logic that was already verified in CI.

**dbt Cloud configuration:**
- In **CI jobs**: Unit tests run by default when a model is selected
- In **Production jobs**: Add `--exclude-resource-type unit_test` to the job command
- In **Slim CI**: Unit tests for modified models run automatically with `state:modified+`

---

### 10. Common Mistakes

| Mistake | Problem | Fix |
|---|---|---|
| Testing too much in one test | One test validates 5 different behaviors | Split into separate focused tests |
| Mocking every column | Test is brittle and hard to maintain | Mock only columns relevant to the behavior under test |
| Not mocking a dependency | NULL values propagate, test fails mysteriously | Ensure every `ref()` and `source()` used by the tested code path is mocked |
| Wrong data types in mock | `"100"` (string) vs `100` (integer) | Match column types from the source schema |
| Testing implementation, not behavior | Test breaks when SQL is refactored | Test the output contract, not how the SQL achieves it |
| Ignoring NULL handling | Model works with mock data but fails on real NULLs | Include NULL values in mock inputs to test edge cases |
| Copy-pasting between tests | Tests drift out of sync, hard to maintain | Use YAML anchors or extract common fixtures |
| Not testing empty inputs | Model crashes on zero rows in production | Add a test with `rows: []` for each input |
| Forgetting `format: sql` for ephemeral deps | Test fails because ephemeral model has no table | Always use SQL format when mocking ephemeral model dependencies |
| Hardcoding dates that expire | Test breaks when "tomorrow" becomes "yesterday" | Use `overrides.vars` with a fixed reference date |

---

## RA-Specific Conventions

### Unit Test Requirements by Layer

| Model Layer | Unit Test Required? | Guidance |
|---|---|---|
| **Staging** (`stg_`) | Recommended if non-trivial | Only if the staging model contains regex, date logic, or case statements beyond simple rename/recast |
| **Integration** (`int_`) | Required if business logic present | Multi-source joins with conditional logic, entity resolution, deduplication |
| **Warehouse - Dimension** (`_dim`) | Required | SCD logic, derived attributes, business classifications |
| **Warehouse - Fact** (`_fct`) | Required | Metric calculations, status derivations, temporal logic |

### File Naming Convention

Use dedicated unit test files with the naming pattern:

```
unit_test_{model_name}.yml
```

Place in the same directory as the model's schema YAML:

```
models/
  warehouse/
    fct_orders.sql
    fct_orders.yml                 # Schema tests, column descriptions
    unit_test_fct_orders.yml       # Unit tests (separate file)
```

**Rationale:** Separating unit tests from schema definitions keeps both files manageable and makes it easy to find all unit tests via glob patterns (`unit_test_*.yml`).

### Test Naming Convention

```yaml
unit_tests:
  - name: test_{model_name}__{behavior_description}
    # Examples:
    # test_fct_orders__cancelled_orders_excluded_from_revenue
    # test_int_customers__dedup_keeps_latest_record
    # test_dim_products__inactive_products_flagged
```

### Cross-Reference: Overall Test Strategy

For guidance on **which types of tests** to write (schema tests, unit tests, data tests) and **how much coverage** is needed per model layer, refer to `testing-reference.md` in the `dbt-development` skill. This skill covers only the mechanics of writing unit tests.

---

## Additional Resources

- **Examples:** See the `examples/` directory for complete, runnable unit test files
  - `unit-test-example.yml` -- Simple staging model unit test
  - `unit-test-complex.yml` -- Complex unit test with window functions and date logic
- **dbt Documentation:** [Unit Tests](https://docs.getdbt.com/docs/build/unit-tests) (dbt Core 1.8+)

---

## Attribution

Adapted from [dbt-labs/dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) (Apache-2.0 License). Original skill: `adding-dbt-unit-test`. Modified for Rittman Analytics conventions, BigQuery focus, and Wire Framework integration.
