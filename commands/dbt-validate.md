---
description: Run dbt tests and validation
argument-hint: <project-folder>
---

# Run dbt tests and validation

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Validate dbt models - run tests, check conventions, verify documentation and testing coverage
argument-hint: <project-folder>
---

# dbt Validation Command

## Purpose

Validate generated dbt models by running dbt tests, checking naming conventions, verifying SQL structure, model configuration, testing coverage, documentation coverage, and optionally running sqlfluff. Produces a structured validation report with severity-rated issues.

> **Per-layer alternative**: If the dbt project was built layer-by-layer instead of via `/wire:dbt-generate`, validate each layer with its own command instead: `/wire:dbt-staging-validate`, `/wire:dbt-integration-validate`, `/wire:dbt-warehouse-validate` — run after the corresponding `/wire:dbt-*-generate` command.

## Usage

```bash
/wire:dbt-validate YYYYMMDD_project_name
```

## Prerequisites

- dbt models must be generated (`/wire:dbt-generate` complete)
- dbt models must be run successfully (`/wire:utils-run-dbt` complete)
- dbt Cloud or dbt Core configured

## Workflow

### Step 1: Verify dbt Models Exist

**Process**:
1. Check that `dbt.generate == complete` in status.md
2. Verify dbt models exist in `dbt/models/`

**If not generated**:
```
Error: dbt models not generated yet.

Run `/wire:dbt-generate [folder]` first.
```

### Step 1.5: Load Convention Source

**Priority Order (2-tier system):**

1. **Project-specific conventions** (highest priority)
   - Check for `.dbt-conventions.md` in project root
   - Check for `dbt_coding_conventions.md` in project root
   - Check for `docs/dbt_conventions.md` in project

2. **Embedded conventions** (fallback — use the conventions defined in this spec)

**Detection:**
- Use Glob to search for convention files in project root
- If found, read and use project conventions
- If not found, use the embedded conventions below
- Note which source is being used in validation output

### Step 2: Run dbt Tests

**Process**:
1. Ask user how to run tests:
   - dbt Cloud (API call)
   - dbt Core (local command)
   - Show manual command

**For dbt Core**:
```bash
cd dbt/
dbt test
```

**Capture test results**:
- Total tests run
- Tests passed
- Tests failed (with details)

### Step 3: Check Naming Conventions

#### 3.1 File and Model Naming

| Check | Rule | Example | Severity |
|-------|------|---------|----------|
| Singular names | All objects are SINGULAR | `user` not `users` | Critical |
| Staging models | `stg_<group>__<entity>.sql` | `stg_salesforce__user.sql` | Critical |
| Integration models | `int_<group>__<entity>.sql` | `int_core__user.sql` | Critical |
| Intermediate models | `int_<group>__<entity>__<action>.sql` (past tense verbs) | `int_core__user__unioned.sql` | Critical |
| Warehouse dimensions | `wh_<group>__<entity>_dim.sql` | `wh_core__user_dim.sql` | Critical |
| Warehouse facts | `wh_<group>__<entity>_fact.sql` | `wh_finance__transaction_fact.sql` | Critical |
| Warehouse cross-attribute | `wh_<group>__<entity>_xa.sql` (bridge / many-to-many / cross-entity attribute models) | `wh_core__user_role_xa.sql` | Critical |
| Aggregate tables | `wh_<group>__<entity>_agg.sql` | `wh_core__course_summary_by_year_agg.sql` | Critical |
| Files | Lowercase with underscores only | ✅ `wh_core__user_dim.sql` ❌ `StudentDim.sql` | Critical |

**Directory Structure Check**:
```
models/
├── staging/
│   └── <group>/
│       ├── stg_<group>.yml
│       └── stg_<group>__<entity>.sql
├── integration/
│   ├── int_<group>/
│   │   ├── intermediate/
│   │   │   ├── intermediate.yml
│   │   │   └── int_<group>__<entity>__<action>.sql
│   │   ├── int_<group>__<entity>.sql
│   │   └── integration.yml
└── warehouse/
    └── wh_<group>/
        ├── wh_<group>.yml
        ├── wh_<group>__<entity>_dim.sql
        ├── wh_<group>__<entity>_fact.sql
        └── wh_<group>__<entity>_xa.sql
```

**Violations to Flag:**
- Plural object names
- Missing or incorrect prefixes/suffixes
- Non-standard directory structure
- Mismatched filename and directory location

#### 3.2 Field Naming Conventions

For each model, check ALL fields against these conventions:

| Type | Pattern | Example | Severity |
|------|---------|---------|----------|
| Primary Key | `<entity>_pk`, generated via `dbt_utils.generate_surrogate_key(...)` | `user_pk`, `transaction_pk` | Critical |
| Foreign Key | `<referenced_entity>_fk`, generated via `dbt_utils.generate_surrogate_key(...)` | `user_fk`, `account_fk` | Critical |
| Natural Key | `<descriptive_name>_natural_key` | `salesforce_user_natural_key` | Important |
| Date | `<event>_dt` | `user_created_dt` | Important |
| Timestamp (UTC) | `<event>_ts` — always assumed UTC unless otherwise indicated | `created_ts`, `updated_ts` | Important |
| Timestamp (non-UTC) | `<event>_<tz>_ts` — timezone tag inserted before `_ts` | `created_cet_ts`, `created_pt_ts` | Important |
| Boolean | `is_<state>`, `has_<thing>`, or `was_<event>` | `is_active`, `has_subscription`, `was_refunded` | Important |
| Revenue / Money | `<entity>_<measure>_amount` — decimal currency, converted from cents at the staging layer | `user_account_balance_amount` (not `price_in_cents`) | Important |
| Common fields | `<entity>_<field>` prefix | `customer_name` (not just `name`) | Important |

**Type Casting:**
- Always use dbt's type-cast macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`, `{{ type_date() }}` (community macro, no `dbt.` prefix)
- This keeps models portable across warehouses (BigQuery / Snowflake / Databricks / Postgres)

**General Rules:**
- All names in `snake_case`
- Use business terminology, not source terminology
- Avoid SQL reserved words
- Consistency across models (same field names for same concepts)

**Violations to Flag:**
- Inconsistent naming patterns across models
- Missing `_pk`/`_fk` suffixes; PKs/FKs not generated via `dbt_utils.generate_surrogate_key`
- Timestamps without `_ts` suffix; dates without `_dt` suffix; non-UTC timestamps without a timezone tag before `_ts`
- Booleans without `is_`/`has_`/`was_` prefix
- Revenue columns without `_amount` suffix
- Raw SQL type casts instead of `dbt.type_*()` macros
- Reserved words as column names

#### 3.3 Field Ordering

Check that fields in each model's `select` list follow this ordering:

1. **Keys** — pk, fks, natural keys
2. **Attributes** — dimensions, slicing fields, descriptive columns
3. **Indexes / ranks** — `row_number()`, rank columns, sequence positions
4. **Metrics** — measures, aggregatable values, `_amount` columns
5. **Booleans** — `is_*`, `has_*`, `was_*` flags
6. **Temporal data types** — `_dt`, `_ts` columns last

### Step 3.5: Validate SQL Structure

For each model file, check:

#### CTE Structure

| Check | Rule | Severity |
|-------|------|----------|
| Refs at top | All `{{ ref() }}` and `{{ source() }}` calls in top CTEs | Critical |
| CTE naming | `s_` prefix for ref/source CTEs | Important |
| Final CTE | Must have `final` CTE with `select * from final` at end | Critical |
| One logical unit | Each CTE does one transformation | Info |

**Required Pattern:**
```sql
with

s_source_table as (
    select * from {{ ref('source_model') }}
),

transformation_cte as (
    select ... from s_source_table
),

final as (
    select ... from transformation_cte
)

select * from final
```

**Violations to Flag:**
- `ref()` or `source()` calls outside of top CTEs
- Missing final CTE
- Non-staging models selecting from `{{ source() }}`

#### SQL Style

| Check | Rule | Severity |
|-------|------|----------|
| Indentation | 4 spaces (not tabs) | Important |
| Line length | Max 80 characters | Info |
| Case | Lowercase field names and SQL functions | Important |
| Aliases | Always use `as` keyword | Important |
| Joins | Explicit: `inner join`, `left join` (never just `join`) | Critical |
| Table aliases | Full descriptive names, not initialisms (`customer`, not `c`) | Important |
| Column prefixes | Required when joining 2+ tables | Important |
| Union | `union all` preferred over `union distinct` | Info |
| Group by | Column names, not numbers | Important |

**Violations to Flag:**
- Implicit joins or missing join qualifiers
- Hard-to-understand table aliases (single letters)
- Uppercase SQL keywords or functions
- Improper indentation or line length

### Step 3.6: Validate Model Configuration

| Check | Rule | Severity |
|-------|------|----------|
| Warehouse models | Always materialized as `table` | Critical |
| Staging models | `view` or ephemeral (not `table` unless performance requires) | Important |
| Integration models | `view` or ephemeral (not `table` unless performance requires) | Important |
| Config placement | Model-specific in `{{ config() }}` block, directory-wide in `dbt_project.yml` | Info |

**Violations to Flag:**
- Warehouse models not materialized as tables
- Unnecessary table materializations in staging/integration
- Config that should be in `dbt_project.yml` but is in model

### Step 3.7: Validate Testing Coverage

#### Minimum Testing Requirements

**Every Model Must Have:**
- Entry in a `schema.yml` file
- Primary key with `unique` and `not_null` tests

**By Layer:**

| Layer | Required Tests | Severity |
|-------|---------------|----------|
| Staging | `unique` + `not_null` on pk, `not_null` on critical fields | Critical |
| Integration | `unique` + `not_null` on pk, `dbt_utils.unique_combination_of_columns` for multi-source | Critical |
| Warehouse | `unique` + `not_null` on pk, `relationships` on all fk fields | Critical |

**Additional Tests to Check:**
- `relationships` tests for foreign keys
- `accepted_values` for enum/status fields
- `not_null_where` for conditional requirements
- Custom data tests in `tests/` directory for KPI validation

**Schema.yml Location:**
- Every subdirectory should contain a `.yml` file
- Named after directory: `stg_<source>.yml`, `integration.yml`, etc.

**Violations to Flag:**
- Missing `schema.yml` file for a subdirectory
- Models without any test coverage
- Primary keys without `unique`/`not_null` tests
- Missing `relationships` tests on foreign keys
- Integration models without `unique_combination_of_columns`

### Step 3.8: Validate Documentation Coverage

| Layer | Required Coverage | Severity |
|-------|------------------|----------|
| Staging | 100% — all models and columns documented | Critical |
| Warehouse | 100% — all models and columns documented | Critical |
| Integration | As needed — document complex logic and special cases | Important |

**Checks:**
- Every staging model has a `description` in schema.yml
- Every warehouse model has a `description` in schema.yml
- Every column in staging/warehouse has a `description`
- Descriptions use business terminology (not just field names)
- Complex/calculated fields have explanatory descriptions

**Best Practices to Check:**
- Use of `{% docs %}` blocks for shared documentation
- Doc blocks stored in `models/docs/` directory
- Descriptions focus on WHY, not just WHAT

**Violations to Flag:**
- Staging/warehouse models without descriptions
- Missing column documentation in staging/warehouse
- Vague or unhelpful descriptions (e.g., description matches field name)

### Step 3.9: Run sqlfluff Validation (If Available)

**Process:**
1. Check for sqlfluff: `which sqlfluff`
2. Check for `.sqlfluff` config in project root

**If sqlfluff available:**
```bash
sqlfluff lint models/ --dialect <bigquery|snowflake|postgres>
```

Include sqlfluff violations in validation output. sqlfluff enforces many style conventions automatically:
- Line length limits
- Indentation consistency
- Capitalization rules
- Trailing commas
- Whitespace rules

**If not available:**
- Note in output: "sqlfluff not detected — recommend installing for automated linting"
- Provide manual validation of style conventions (Steps 3.5 and above)

### Step 4: Verify Model Dependencies

**Check for**:
- All `{{ ref() }}` references point to existing models
- No circular dependencies
- Proper layer order (staging → integration → warehouse)

**Use**:
```bash
dbt compile --select [models]
```

If compile fails, there are dependency issues.

### Step 5: Generate Validation Report

**Output Format:**

```markdown
## dbt Model Validation Report

**Project:** [PROJECT_NAME]
**Status:** PASS | FAIL
**Convention Source:** [project-specific / embedded defaults]
**Models Location:** dbt/models/

### Summary
- ✓ X checks passed
- ⚠️ Y issues found (N critical, M important, P nice-to-have)

### Test Results

✅/❌ **[passed]/[total] tests passed**

**By Layer:**
- Staging: [x]/[y] passed
- Integration: [x]/[y] passed
- Warehouse: [x]/[y] passed

**Failed Tests** (if any):
1. `test_name` - [failure details]
   - **Model:** `model_name`
   - **Fix:** [suggested fix]

### Naming Conventions
[✓/⚠️] **File naming:** [details]
[✓/⚠️] **Field naming:** [details]
[✓/⚠️] **Field ordering:** [details]

### SQL Structure
[✓/⚠️] **CTE structure:** [details]
[✓/⚠️] **Style compliance:** [details]
[✓/⚠️] **Layer boundaries:** [details]

### Configuration
[✓/⚠️] **Materialization:** [details]
[✓/⚠️] **Performance settings:** [details]

### Testing Coverage
[✓/⚠️] **Schema.yml exists:** [details]
[✓/⚠️] **Primary key tests:** [details]
[✓/⚠️] **Foreign key tests:** [details]
[✓/⚠️] **Additional tests:** [details]

### Documentation Coverage
[✓/⚠️] **Staging models documented:** [x]/[y]
[✓/⚠️] **Warehouse models documented:** [x]/[y]
[✓/⚠️] **Column descriptions:** [x]/[y]

### sqlfluff
[✓/⚠️/N/A] **Linter results:** [details]

### Dependency Check
[✓/⚠️] **All refs resolve:** [details]
[✓/⚠️] **Layer ordering:** [details]

---

## Recommendations

### Critical Issues (must fix)
1. [issue description]
   - **Location:** [file:line or section]
   - **Current:** `[current code]`
   - **Should be:** `[correct pattern]`
   - **Reason:** [why this matters]

### Important Issues (should fix)
[same format]

### Nice-to-have Improvements
[same format]

---

### Next Steps

1. **Fix issues** (if FAIL): Address critical and important issues, then re-validate
2. **Review dbt models with team**: `/wire:dbt-review [folder]`
3. **Generate semantic layer**: `/wire:semantic_layer-generate [folder]`
```

## Priority Levels

| Level | Criteria | Examples |
|-------|----------|---------|
| **Critical** | Breaks functionality, violates core principles, missing required tests | Missing pk tests, `ref()` outside CTEs, warehouse not materialized as table |
| **Important** | Inconsistent with conventions, maintainability issues, missing documentation | Wrong field naming, missing docs, implicit joins, no table aliases |
| **Nice-to-have** | Style preferences, minor optimizations, enhanced documentation | Line length, indentation, `union all` vs `union distinct` |

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.dbt section:
   ```yaml
   dbt:
     generate: complete
     validate: pass | fail
     review: not_started
     tests_passed: 32
     tests_failed: 0
     validated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `dbt`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### dbt Not Run Yet

If models haven't been run:
```
Warning: dbt models haven't been run yet.

Tests require models to be materialized first.

Run dbt models: /wire:utils-run-dbt [folder]
```

### dbt Command Not Found

If dbt not installed (local mode):
```
Error: dbt command not found.

Please either:
1. Install dbt: pip install dbt-bigquery
2. Use dbt Cloud instead
3. Show manual test commands
```

### Some Tests Failing

If tests fail:
- Set validate status to `fail`
- Show which tests failed with severity classification
- Suggest fixes based on test type
- User must fix data/models and re-run

### No Convention Source Found

```
Note: No project-specific conventions found.
Using embedded conventions from this specification.

To use project-specific conventions, create one of:
- .dbt-conventions.md
- dbt_coding_conventions.md
- docs/dbt_conventions.md
```

## Common Violations Reference

❌ **Don't:**
- Use plural object names (`users` → use `user`)
- Put `ref()` calls outside top CTEs
- Use implicit joins or just `join` (use `inner join`, `left join`)
- Use table alias initialisms (`c` → use `customer`)
- Mix tabs and spaces (use 4 spaces)
- Skip tests on primary keys
- Leave staging/warehouse models undocumented
- Select from sources in non-staging models
- Use `union distinct` without good reason
- Look up PKs in separate queries (generate with `dbt_utils.generate_surrogate_key()`)

✅ **Do:**
- Use singular names
- All refs in top CTEs (prefixed with `s_`)
- Explicit join types
- Descriptive table aliases
- Consistent indentation (4 spaces)
- Test all primary keys (`unique` + `not_null`)
- Document staging and warehouse 100%
- Respect layer boundaries
- Prefer `union all`
- Generate PKs/FKs with `dbt_utils.generate_surrogate_key()`
- Use `dbt.type_*()` macros for all type casting

## Output

This command:
- Runs dbt tests
- Validates naming conventions (file, field, ordering)
- Checks SQL structure and style
- Validates model configuration
- Checks testing coverage
- Checks documentation coverage
- Runs sqlfluff (if available)
- Checks dependencies
- Produces severity-rated validation report
- Updates `status.md` with validation results
- Provides actionable feedback if issues found

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
