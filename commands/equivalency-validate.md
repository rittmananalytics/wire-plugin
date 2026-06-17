---
description: Run equivalency checks across all in-scope tables (parallel fan-out)
argument-hint: <release-folder>
---

# Run equivalency checks across all in-scope tables (parallel fan-out)

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Run equivalency checks across all in-scope tables (repeatable loop, parallel fan-out)
---

## Data Safety — Read Before Proceeding

Before running any queries, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  All queries against the source platform are SELECT only.
  Do NOT run INSERT, UPDATE, DELETE, CREATE TABLE, or DROP against the source.

Target reads from: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not write to these):
  [list each production project ID]
```

If any check query would write to a source platform or production project, stop and report the conflict.

---

# Equivalency — Validate

## Purpose

This is a repeatable loop command — not a standard generate/validate/review artifact. It runs all seven check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum, business invariants) across all in-scope migration objects, updates the equivalency tracking block in status.md, and unblocks the cutover command when `checks_failing == 0`.

Each invocation adds a new entry to `equivalency_validation.loop_history` in status.md, preserving the full audit trail of every run.

## Prerequisites

- `orchestration_migration review: approved`
- Target platform has data (Fivetran connectors have completed at least one sync)

## Behaviour

This command can be run as many times as needed. There is no "approved" state — the loop continues until equivalency passes or the team decides to proceed to cutover despite known failures (requires explicit override).

## Workflow

### Step 1: Load scope

Read the list of in-scope tables and dbt models from `migration/migration_inventory.md`. This is the full check scope.

For projects with >50 in-scope objects: fan out checks in parallel subagents — one per schema or one per dbt layer. Each subagent runs the per-object check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum) for its assigned objects and reports back. Business invariants (check type 7) are run once for the release, not per object, since many are cross-table aggregates. This dramatically reduces wall-clock time for large migrations.

### Step 2: Run all check types

For each in-scope object, run check types 1–6. Run check type 7 (business invariants) once per release. For each object:

**Check type 1 — Row count**
```sql
-- Source
SELECT COUNT(*) AS row_count FROM source_project.source_schema.table_name;
-- Target
SELECT COUNT(*) AS row_count FROM target_db.target_schema.table_name;
```
PASS: |source_count - target_count| / source_count ≤ tolerance (default 0.1%, configurable per table in migration strategy)
FAIL: Count outside tolerance

**Check type 2 — Schema**
Compare column names, types, and nullability between source and target.
PASS: All columns match (modulo expected type translations per type_mapping.md)
FAIL: Missing columns, extra columns, or unexpected type changes

**Check type 3 — Value sampling**
For numeric columns: compare mean, min, max, null percentage (sample 10K rows if table >10M rows)
For string columns: compare distinct count and null percentage
PASS: Statistical measures within ±1% (configurable)
FAIL: Deviation outside threshold

**Check type 4 — Freshness**
Compare max(updated_at) or max(loaded_at) between source and target.
PASS: Target is within max(sync_frequency, 24h) of source
FAIL: Target data is more than 24 hours stale relative to source

**Check type 5 — dbt tests**
Run `dbt test --profiles-dir ~/.dbt --target target_profile` for the translated dbt models.
PASS: All tests pass
FAIL: List failing tests

**Check type 6 — Row-level checksum**
Statistical sampling (check type 3) can pass while individual rows differ — two columns can share a mean and min/max and still be wrong row by row. The checksum check closes that gap by hashing the row content and comparing.

For each in-scope table, compute a hash over the concatenated, canonically-ordered column values and compare an aggregate of those hashes between source and target. For tables ≤10M rows, hash all rows; for larger tables, hash a deterministic sample (e.g. rows where `MOD(ABS(FARM_FINGERPRINT(pk)), 100) = 0`) so the same rows are sampled on both sides.

```sql
-- BigQuery side
SELECT COUNT(*) AS n, SUM(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS hash_agg
FROM target_db.target_schema.table_name AS t;
-- Snowflake side
SELECT COUNT(*) AS n, SUM(HASH(OBJECT_CONSTRUCT(*)::STRING)) AS hash_agg
FROM source_project.source_schema.table_name;
```
Canonicalise before hashing so the comparison is not defeated by benign representation differences — see the edge-case checklist below. PASS: aggregate hashes match over the same row set. FAIL: mismatch (drill into the differing rows via `equivalency-investigate`).

**Check type 7 — Business invariants**
The checks above confirm the data moved; invariants confirm it still *means* the same thing. For each invariant defined in the migration strategy, run the same aggregate query on both platforms and compare.

Typical invariants: total revenue (`SUM(amount)` over orders), active customer count, row counts per key dimension (e.g. orders per region), and any control total the client already trusts. These are engagement-specific and come from `migration_strategy.md`.

PASS: each invariant matches within its defined tolerance (default: exact for counts, ±0.01% for monetary sums to allow for float representation). FAIL: list the invariant, source value, target value, and delta.

**Edge cases to canonicalise (checks 3, 6, 7)**
These cause false mismatches or, worse, false passes. Account for them before comparing:
- **NULL vs empty string** — `''` and `NULL` may have been merged or split in translation. Compare null-handling explicitly.
- **Unicode / encoding** — normalise (NFC) before hashing; the same glyph can have multiple byte representations.
- **Timezone** — compare timestamps in a single canonical zone (UTC). A model that silently shifted timezone will pass a row count and fail here.
- **Numeric precision / scale** — `NUMBER(38,9)` → `NUMERIC`/`BIGNUMERIC` can round. Round both sides to an agreed scale before hashing monetary columns.
- **Float ordering / trailing zeros** — `1.0` vs `1` and `-0.0` vs `0.0` hash differently; cast to a fixed format first.

### Step 3: Compile results

Aggregate:
- `checks_total`: total checks run
- `checks_passing`: objects that passed all applicable check types (plus the release-level invariant result)
- `checks_failing`: checks with at least one failure
- `checks_by_type`: breakdown of pass/fail per check type
- Per-object summary: which checks passed/failed for each object

### Step 4: Write equivalency report

**Output location**: `.wire/releases/$ARGUMENTS/migration/equivalency_report_{run_number}.md`

Use the template at `TEMPLATES/migration/equivalency_report.md`. Include:
- Run summary: date, run number, total/passing/failing
- Objects failing by check type
- Top 10 failures sorted by severity (schema failures first, then count, then value)

### Step 5: Update status

```yaml
migration:
  equivalency_validation:
    checks_total: N
    checks_passing: N
    checks_failing: N
    last_run_date: "{{TODAY}}"
    loop_history:
      - run: 1
        date: "{{TODAY}}"
        passing: N
        failing: N
        report: migration/equivalency_report_1.md
    status: "passing" | "failing" | "complete"
```

Set `status: complete` only when `checks_failing == 0`.

### Step 6: Output results

If `checks_failing == 0`:
```
All equivalency checks PASS (N/N objects)
Cutover is now unblocked.
/wire:cutover-generate $ARGUMENTS
```

If `checks_failing > 0`:
```
Equivalency checks: N passing, N failing

Top failures:
[List top 5 failing objects with check type and detail]

To investigate a specific failure:
/wire:equivalency-investigate $ARGUMENTS --object <table_or_model>

To apply a fix and re-run affected checks:
/wire:equivalency-fix $ARGUMENTS --object <name> --approach <description>

Re-run all checks after fixes:
/wire:equivalency-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact_id, `Equivalency Validation` as artifact_name, and the `file` value from `artifacts.equivalency` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `equivalency` as artifact, `validate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

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
