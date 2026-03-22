---
name: dbt-migration
description: Proactive skill for migrating dbt projects between data platforms (BigQuery, Snowflake, Databricks) or upgrading between dbt versions. Auto-activates when working on warehouse migrations, platform switches, or dbt version upgrades. Provides systematic workflow with validation at each step.
---

# dbt Migration Skill

## Purpose

This skill provides a systematic, validation-driven workflow for migrating dbt projects between data platforms (BigQuery, Snowflake, Databricks) or upgrading between dbt versions. It covers cross-platform SQL dialect translation, pre/post-migration testing, and documentation of all changes made.

Migrations are high-risk operations. This skill enforces a disciplined approach: assess first, test before changing, fix one category at a time, validate continuously, and document everything.

## When This Skill Activates

### User-Triggered Activation

This skill should activate when users:
- **Plan a migration:** "We need to move from Snowflake to BigQuery"
- **Start migration work:** "Migrate this dbt project to Databricks"
- **Fix dialect issues:** "This SQL doesn't work on BigQuery" (when in migration context)
- **Upgrade dbt:** "Upgrade from dbt 1.5 to 1.8" or "Move to dbt Cloud"
- **Convert legacy SQL:** "Convert these stored procedures to dbt models"
- **Ask about platform differences:** "What's the BigQuery equivalent of DATEADD?"

**Keywords to watch for:**
- "migrate", "migration", "platform migration", "warehouse migration"
- "cross-platform", "switch warehouse", "move to BigQuery", "move to Snowflake"
- "BigQuery to Snowflake", "Snowflake to BigQuery", "Snowflake to Databricks"
- "Databricks to BigQuery", "dialect", "SQL dialect"
- "dbt upgrade", "dbt version", "upgrade dbt", "dbt Cloud migration"
- "stored procedure", "legacy SQL", "convert SQL"
- "DATEADD vs DATE_ADD", "NVL vs IFNULL", "backticks vs quotes"

### Self-Triggered Activation (Proactive)

**Activate BEFORE making migration-related changes when:**
- You detect SQL compilation errors that suggest a platform mismatch
- You see platform-specific functions in SQL that don't match the target warehouse
- User is configuring a new `profiles.yml` target for a different platform
- You detect `target/` errors after a platform switch
- Working with files that contain cross-platform adapter macros

**Example internal triggers:**
- SQL uses `SAFE_CAST` but target is Snowflake -> Activate skill
- SQL uses `DATEADD` but target is BigQuery -> Activate skill
- User changes `type: bigquery` to `type: snowflake` in profiles -> Activate skill

### When NOT to Activate

Do **not** activate this skill when:
- Working on normal dbt development within a single platform (defer to **dbt-development**)
- Writing new models from scratch that don't involve platform translation
- The user is asking about dbt Semantic Layer (defer to **dbt-semantic-layer**)

## Instructions

### 1. Migration Types

#### 1.1 Cross-Platform Migration

Moving a dbt project from one data warehouse to another. This is the most complex migration type.

**Supported platform pairs (RA primary):**
- BigQuery <-> Snowflake
- BigQuery <-> Databricks
- Snowflake <-> Databricks

**Key challenges:**
- SQL dialect differences (functions, data types, syntax)
- Platform-specific macros and packages
- Identifier quoting conventions
- Data type mappings
- Performance optimization differences

#### 1.2 dbt Version Upgrade

Upgrading between dbt versions (e.g., 1.5 -> 1.8, Core -> Cloud).

**Key challenges:**
- Breaking changes in dbt APIs
- Deprecated config options
- YAML schema changes
- Macro API changes
- Package compatibility

#### 1.3 Legacy SQL Migration

Converting stored procedures, views, or raw SQL scripts into dbt models.

**Key challenges:**
- Decomposing monolithic SQL into modular models
- Identifying source tables and creating source definitions
- Replacing procedural logic with set-based transformations
- Handling control flow (IF/ELSE, WHILE loops) that doesn't translate to dbt

---

### 2. Cross-Platform Migration Workflow

Follow these seven steps in order. Do not skip steps.

#### Step 1: Assess

Inventory the existing project to understand scope and identify platform-specific code.

**Actions:**
1. Count models by layer (staging, integration, marts)
2. List all packages in `packages.yml` — check for platform-specific packages
3. Identify custom macros in `macros/` — catalogue which use platform-specific SQL
4. Search for platform-specific functions in all `.sql` files
5. Check `dbt_project.yml` for platform-specific configurations
6. Review `profiles.yml` for current target configuration
7. List all tests, especially custom schema tests that may use platform SQL

**Platform-specific function search patterns:**

| Source Platform | Functions to Find |
|----------------|------------------|
| BigQuery | `SAFE_CAST`, `IFNULL`, `FARM_FINGERPRINT`, `GENERATE_DATE_ARRAY`, `UNNEST`, `STRUCT`, `ARRAY_AGG`, `FORMAT_DATE`, `DATE_DIFF`, `DATE_ADD`, `DATE_SUB`, `PARSE_DATE`, `TIMESTAMP_DIFF`, `REGEXP_EXTRACT`, `REGEXP_CONTAINS`, `SPLIT(x)[OFFSET(n)]`, backtick identifiers |
| Snowflake | `DATEADD`, `DATEDIFF`, `NVL`, `NVL2`, `TRY_CAST`, `FLATTEN`, `LATERAL`, `PARSE_JSON`, `GET_PATH`, `OBJECT_CONSTRUCT`, `ARRAY_CONSTRUCT`, `IFF`, `REGEXP_SUBSTR`, `REGEXP_LIKE`, `SPLIT_PART`, double-quote identifiers, `$$` delimiters |
| Databricks | `date_add`, `date_sub`, `datediff`, `nvl`, `explode`, `from_json`, `to_json`, `collect_list`, `collect_set`, `regexp_extract`, `split`, backtick identifiers |

**Output:** A migration assessment document listing:
- Total model count and breakdown by layer
- Platform-specific code inventory (file, line, function/syntax)
- Package compatibility assessment
- Estimated complexity (low/medium/high per model)

#### Step 2: Pre-Migration Testing

Generate unit tests on the SOURCE platform to capture expected outputs. These tests become the acceptance criteria for the migration.

**Actions:**
1. For each model with complex logic, create a dbt unit test that captures current behavior
2. Focus on models with:
   - Date/time transformations
   - String manipulations
   - Type casting
   - Window functions
   - JSON/array handling
   - Custom macros
3. Run all unit tests on the source platform to confirm they pass
4. Document the test baseline (number of tests, all passing)

**Why this matters:** Without pre-migration tests, you cannot verify that the migrated code produces identical results. This step is non-negotiable.

**Example unit test for migration:**
```yaml
unit_tests:
  - name: test_date_formatting_migration
    description: "Captures expected date formatting behavior for migration validation"
    model: int_orders_enriched
    given:
      - input: ref('stg_orders')
        rows:
          - {order_id: 1, order_date: "2024-01-15", status: "completed"}
          - {order_id: 2, order_date: "2024-02-28", status: "pending"}
    expect:
      rows:
        - {order_id: 1, order_month: "2024-01", is_completed: true}
        - {order_id: 2, order_month: "2024-02", is_completed: false}
```

#### Step 3: Environment Setup

Configure the new target platform.

**Actions:**
1. Add a new target in `profiles.yml` for the destination platform
2. Verify credentials with `dbt debug`
3. Ensure the target database/schema exists
4. Update `dbt_project.yml` if needed (e.g., dataset vs schema naming)
5. Check and update `packages.yml`:
   - Replace platform-specific packages with cross-platform alternatives
   - Update `dbt-utils` to a version supporting both platforms
   - Add adapter-specific packages if needed (e.g., `dbt-bigquery-utils`)

**Profile configuration examples:**

BigQuery target:
```yaml
target_bigquery:
  type: bigquery
  method: oauth
  project: my-gcp-project
  dataset: analytics
  threads: 4
  location: EU
```

Snowflake target:
```yaml
target_snowflake:
  type: snowflake
  account: xy12345.eu-west-1
  user: "{{ env_var('SNOWFLAKE_USER') }}"
  password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
  role: transformer
  database: analytics
  warehouse: transforming
  schema: public
  threads: 4
```

Databricks target:
```yaml
target_databricks:
  type: databricks
  host: "{{ env_var('DATABRICKS_HOST') }}"
  http_path: /sql/1.0/warehouses/abc123
  token: "{{ env_var('DATABRICKS_TOKEN') }}"
  catalog: analytics
  schema: public
  threads: 4
```

#### Step 4: Compilation Check

Attempt to compile the project against the new target. Do NOT try to run models yet.

**Actions:**
1. Clear the `target/` directory:
   ```bash
   rm -rf target/
   ```
2. Compile:
   ```bash
   dbt compile --target target_new_platform
   ```
3. Catalogue ALL errors — do not stop at the first error
4. Classify each error by category (see Step 5)
5. Count errors by category to prioritize fixes

**Important:** Always clear `target/` before recompiling after making changes. Stale compilation artifacts cause false errors.

#### Step 5: Iterative Fixes

Work through compilation errors by category, fixing one category at a time.

**Fix order (most impactful first):**

1. **Data type mismatches** — Change type declarations and casts
2. **Date/time functions** — Translate date functions (see dialect-differences.md)
3. **String functions** — Translate string operations
4. **NULL handling** — Replace platform-specific NULL functions
5. **Identifier quoting** — Switch quoting style (backticks vs double-quotes)
6. **Array/Struct/JSON** — Translate complex type operations
7. **Window functions** — Adjust syntax differences
8. **Custom macros** — Rewrite macros for new platform or use cross-platform alternatives
9. **Package-specific** — Replace or update packages

**After each category:**
1. Clear `target/`
2. Recompile
3. Verify the error count decreased
4. Document changes made in `migration_changes.md`

**Cross-platform macro pattern:**
When a function exists on all platforms but with different names, create a dispatch macro:

```sql
-- macros/cross_platform/date_add_days.sql
{% macro date_add_days(date_expr, days) %}
    {{ return(adapter.dispatch('date_add_days')(date_expr, days)) }}
{% endmacro %}

{% macro bigquery__date_add_days(date_expr, days) %}
    DATE_ADD({{ date_expr }}, INTERVAL {{ days }} DAY)
{% endmacro %}

{% macro snowflake__date_add_days(date_expr, days) %}
    DATEADD(day, {{ days }}, {{ date_expr }})
{% endmacro %}

{% macro databricks__date_add_days(date_expr, days) %}
    date_add({{ date_expr }}, {{ days }})
{% endmacro %}
```

#### Step 6: Validation

Run the full project on the new platform and compare results to pre-migration tests.

**Actions:**
1. Run all models:
   ```bash
   dbt build --target target_new_platform
   ```
2. Check for runtime errors (queries that compile but fail at execution)
3. Run unit tests:
   ```bash
   dbt test --target target_new_platform --select "test_type:unit"
   ```
4. Compare unit test results to the Step 2 baseline
5. Run data tests:
   ```bash
   dbt test --target target_new_platform
   ```
6. For models without unit tests, spot-check row counts and key aggregates

**Success criteria:**
- 0 compilation errors
- 0 runtime errors
- All unit tests pass
- All data tests pass
- Row counts match source platform (within acceptable tolerance for float differences)

#### Step 7: Documentation

Create a comprehensive record of all migration changes.

**Create `migration_changes.md` in the project root (or `.wire/{project}/` for Wire projects):**

```markdown
# Migration Changes: {Source Platform} -> {Target Platform}

## Summary
- **Date:** YYYY-MM-DD
- **Source:** {platform} / dbt {version}
- **Target:** {platform} / dbt {version}
- **Models migrated:** {count}
- **Tests migrated:** {count}
- **Macros changed:** {count}

## Changes by Category

### Data Types
| File | Line | Original | Migrated | Notes |
|------|------|----------|----------|-------|

### Date/Time Functions
| File | Line | Original | Migrated | Notes |
|------|------|----------|----------|-------|

### String Functions
| File | Line | Original | Migrated | Notes |
|------|------|----------|----------|-------|

(... continue for each category ...)

## Packages Changed
| Package | Old Version | New Version/Replacement | Notes |
|---------|------------|------------------------|-------|

## Known Differences
- List any acceptable differences in behavior between platforms

## Rollback Plan
- Steps to revert if migration needs to be rolled back
```

---

### 3. SQL Dialect Differences

This section provides a quick reference for the most common translation needs. For a comprehensive reference, see `dialect-differences.md` in this skill's directory.

#### Date/Time Functions

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Add days | `DATE_ADD(d, INTERVAL n DAY)` | `DATEADD(day, n, d)` | `date_add(d, n)` |
| Subtract days | `DATE_SUB(d, INTERVAL n DAY)` | `DATEADD(day, -n, d)` | `date_sub(d, n)` |
| Difference | `DATE_DIFF(d1, d2, DAY)` | `DATEDIFF(day, d2, d1)` | `datediff(d1, d2)` |
| Truncate | `DATE_TRUNC(d, MONTH)` | `DATE_TRUNC('month', d)` | `date_trunc('month', d)` |
| Extract | `EXTRACT(YEAR FROM d)` | `EXTRACT(YEAR FROM d)` | `extract(YEAR FROM d)` |
| Format | `FORMAT_DATE('%Y-%m', d)` | `TO_CHAR(d, 'YYYY-MM')` | `date_format(d, 'yyyy-MM')` |
| Parse | `PARSE_DATE('%Y-%m-%d', s)` | `TO_DATE(s, 'YYYY-MM-DD')` | `to_date(s, 'yyyy-MM-dd')` |
| Current date | `CURRENT_DATE()` | `CURRENT_DATE()` | `current_date()` |
| Current timestamp | `CURRENT_TIMESTAMP()` | `CURRENT_TIMESTAMP()` | `current_timestamp()` |

#### String Functions

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Concatenate | `CONCAT(a, b)` or `a \|\| b` | `CONCAT(a, b)` or `a \|\| b` | `concat(a, b)` or `a \|\| b` |
| Substring | `SUBSTR(s, start, len)` | `SUBSTR(s, start, len)` | `substring(s, start, len)` |
| Length | `LENGTH(s)` | `LENGTH(s)` | `length(s)` |
| Upper/Lower | `UPPER(s)` / `LOWER(s)` | `UPPER(s)` / `LOWER(s)` | `upper(s)` / `lower(s)` |
| Trim | `TRIM(s)` | `TRIM(s)` | `trim(s)` |
| Replace | `REPLACE(s, old, new)` | `REPLACE(s, old, new)` | `replace(s, old, new)` |
| Regex extract | `REGEXP_EXTRACT(s, pattern)` | `REGEXP_SUBSTR(s, pattern)` | `regexp_extract(s, pattern, 0)` |
| Regex match | `REGEXP_CONTAINS(s, pattern)` | `REGEXP_LIKE(s, pattern)` | `s RLIKE pattern` |
| Split | `SPLIT(s, delim)` | `SPLIT(s, delim)` | `split(s, delim)` |
| Split and index | `SPLIT(s, delim)[OFFSET(n)]` | `SPLIT_PART(s, delim, n+1)` | `split(s, delim)[n]` |

#### Data Types

| Concept | BigQuery | Snowflake | Databricks |
|---------|----------|-----------|------------|
| Integer | `INT64` | `INTEGER` / `NUMBER` | `BIGINT` / `INT` |
| Float | `FLOAT64` | `FLOAT` / `DOUBLE` | `DOUBLE` |
| Decimal | `NUMERIC` / `BIGNUMERIC` | `NUMBER(p,s)` | `DECIMAL(p,s)` |
| String | `STRING` | `VARCHAR` / `STRING` | `STRING` |
| Boolean | `BOOL` | `BOOLEAN` | `BOOLEAN` |
| Date | `DATE` | `DATE` | `DATE` |
| Timestamp | `TIMESTAMP` | `TIMESTAMP_NTZ` | `TIMESTAMP` |
| JSON | `JSON` (or `STRING`) | `VARIANT` | `STRING` (with JSON functions) |
| Array | `ARRAY<T>` | `ARRAY` | `ARRAY<T>` |
| Struct | `STRUCT<fields>` | `OBJECT` | `STRUCT<fields>` |

#### NULL Handling

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Coalesce | `COALESCE(a, b)` | `COALESCE(a, b)` | `coalesce(a, b)` |
| If null | `IFNULL(a, b)` | `NVL(a, b)` or `IFNULL(a, b)` | `nvl(a, b)` or `ifnull(a, b)` |
| Null if | `NULLIF(a, b)` | `NULLIF(a, b)` | `nullif(a, b)` |
| Safe cast | `SAFE_CAST(x AS type)` | `TRY_CAST(x AS type)` | `try_cast(x AS type)` |
| Safe divide | `SAFE_DIVIDE(a, b)` | `DIV0NULL(a, b)` or `a / NULLIF(b, 0)` | `a / NULLIF(b, 0)` |

#### Identifier Quoting

| Platform | Style | Example |
|----------|-------|---------|
| BigQuery | Backticks | `` `project.dataset.table` `` |
| Snowflake | Double quotes | `"DATABASE"."SCHEMA"."TABLE"` |
| Databricks | Backticks | `` `catalog`.`schema`.`table` `` |

**Recommendation:** Use dbt's `{{ ref() }}` and `{{ source() }}` functions wherever possible. They handle quoting automatically. Only worry about manual quoting for raw SQL in macros or ad-hoc queries.

---

### 4. dbt Version Upgrade Guide

#### General Upgrade Workflow

1. Read the [dbt migration guide](https://docs.getdbt.com/docs/dbt-versions/core-upgrade) for the target version
2. Check `packages.yml` — ensure all packages support the target version
3. Update `require-dbt-version` in `dbt_project.yml`
4. Run `dbt deps` to update packages
5. Run `dbt compile` and fix deprecation warnings
6. Run `dbt build` and verify all models and tests pass

#### Breaking Changes by Version

**dbt 1.5 -> 1.6:**
- Semantic Layer (MetricFlow) introduced
- `metrics:` YAML schema changed from legacy Metrics Layer to MetricFlow format
- `dbt_metrics` package deprecated

**dbt 1.6 -> 1.7:**
- `dbt_utils.surrogate_key()` renamed to `dbt_utils.generate_surrogate_key()`
- Model contracts introduced (enforce column types)
- Unit tests introduced (experimental)

**dbt 1.7 -> 1.8:**
- Unit tests GA
- `--empty` flag for development builds
- Microbatch incremental strategy (experimental)

**dbt 1.8 -> 1.9:**
- Microbatch GA
- Snapshot config changes (`updated_at` -> `loaded_at`)
- `dbt retry` command improved

**dbt 1.9 -> 1.10+:**
- See latest release notes; check for deprecation warnings in `dbt compile` output

#### Common Macro API Changes

| Old | New | Since |
|-----|-----|-------|
| `adapter.dispatch('macro')()` | `adapter.dispatch('macro', 'package')()` | 1.0 |
| `dbt_utils.surrogate_key()` | `dbt_utils.generate_surrogate_key()` | 1.7 |
| `config(severity='warn')` | `config(severity='warn', warn_if='!=0')` | 1.5 |
| `dbt_utils.pivot()` | Community package / custom macro | 1.5+ |

#### Config API Changes

| Old | New | Since |
|-----|-----|-------|
| `materialized: table` in schema.yml | `config(materialized='table')` in model or `dbt_project.yml` | - |
| `vars: {}` in schema.yml | `vars: {}` in `dbt_project.yml` only | 1.0 |
| `database` config for BigQuery | `project` config (with `database` as alias) | 1.0 |

---

### 5. Legacy SQL Migration

For converting stored procedures, views, or raw SQL into dbt models.

**Workflow:**

1. **Inventory:** List all stored procedures, views, and scripts to migrate
2. **Dependency mapping:** Trace which tables feed into which procedures
3. **Source definitions:** Create `sources.yml` for all raw/landing tables
4. **Decompose:** Break monolithic procedures into discrete transformations
5. **Layer assignment:** Assign each transformation to staging, integration, or marts
6. **Convert:** Rewrite SQL as dbt models following RA conventions (see dbt-development skill)
7. **Handle procedural logic:**
   - `IF/ELSE` -> `CASE WHEN` expressions
   - `WHILE` loops -> Set-based operations or incremental models
   - `CURSOR` -> Window functions or CTEs
   - Temporary tables -> CTEs or ephemeral models
   - Variables -> Jinja variables or dbt vars
8. **Test:** Write tests for each converted model
9. **Validate:** Compare output of dbt models to original procedure output

---

### 6. Anti-Patterns

These are common mistakes during migrations. Avoid them.

| Anti-Pattern | Why It's Bad | What to Do Instead |
|-------------|-------------|-------------------|
| **Fixing SQL before understanding the error** | You may introduce new bugs or mask the real issue | Read the full error message; classify it first; refer to dialect reference |
| **Skipping pre-migration tests** | No way to verify migration correctness | Always generate unit tests on the source platform first (Step 2) |
| **Changing model architecture during migration** | Two changes at once makes debugging impossible | Migration is a translation exercise; refactoring comes after |
| **Not clearing target/ between compiles** | Stale artifacts cause confusing errors | Always `rm -rf target/` before recompiling |
| **Fixing errors one at a time** | Slow; errors may be related | Classify all errors first, fix by category |
| **Using platform-specific SQL in new code** | Creates future migration debt | Use dbt macros (`{{ dbt.date_trunc() }}`) or dispatch macros |
| **Ignoring deprecation warnings** | Warnings become errors in future versions | Fix all warnings during migration |
| **Manual find-and-replace across all files** | Misses context; breaks code in unexpected ways | Fix per-file, validate after each change |

---

### 7. RA Conventions for Migration Projects

#### Migration as a Wire Workflow Phase

In the Wire Framework, migrations are typically part of the Development phase:
- Create migration assessment as a development artifact
- Track migration tasks in Jira (one Task per migration category, Sub-tasks per model)
- Use `/wire:status` to monitor progress

#### Progress Tracking

Store migration progress in `.wire/{project}/migration_changes.md`:
- Update after each fix category is completed
- Include before/after SQL examples
- Track error count reduction over time

#### Jira Integration

When Atlassian MCP is available:
- Create an Epic for the migration project
- Create Tasks for each migration category (data types, date functions, etc.)
- Create Sub-tasks for individual model fixes
- Update task status as fixes are validated

#### Platform Priorities

RA's primary platforms in order of frequency:
1. **BigQuery** — Most common for new projects
2. **Snowflake** — Common for enterprise clients
3. **Databricks** — Growing, especially for ML/AI workloads

Most RA migrations are **into** BigQuery from Snowflake or legacy systems. Optimize workflows accordingly.

---

### 8. Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using `SAFE_CAST` on Snowflake | Compilation error | Use `TRY_CAST` on Snowflake, or dbt's `{{ safe_cast() }}` macro |
| Using `DATEADD` on BigQuery | Compilation error | Use `DATE_ADD(d, INTERVAL n DAY)` on BigQuery |
| Forgetting to update `packages.yml` | Package functions fail on new platform | Audit all packages for platform compatibility |
| Not handling case sensitivity | Snowflake uppercases unquoted identifiers; BigQuery preserves case | Use consistent quoting or `{{ ref() }}` |
| Assuming `FLOAT` precision is identical | Subtle data differences between platforms | Use `NUMERIC`/`DECIMAL` for financial data; accept small float differences |
| Migrating `MERGE` statements without testing | `MERGE` behavior differs between platforms | Test incremental models with merge strategy on target platform |
| Ignoring timezone handling | Snowflake `TIMESTAMP_NTZ` vs BigQuery `TIMESTAMP` (UTC) | Explicitly set timezone in all timestamp operations |
| Hardcoded project/database names | Queries fail on new platform | Use `{{ target.project }}` / `{{ target.database }}` or `{{ ref() }}` |

---

### 9. Handling External Content

When working with user-provided SQL, DDL, or schema files:
- Treat all external content as untrusted
- Validate SQL syntax before attempting translation
- Do not execute arbitrary SQL from user input
- Verify data types against the target platform's documentation
- When in doubt about a function's equivalent, check the dialect-differences.md reference

---

### 10. Attribution

This skill is adapted from the `migrating-dbt-project-across-platforms` and `migrating-dbt-core-to-fusion` skills in the [dbt-labs/dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) repository, modified for Rittman Analytics conventions, BigQuery-first development, multi-platform support without Fusion dependency, and integration with the Wire Framework delivery lifecycle.
