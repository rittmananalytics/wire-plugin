---
description: Schema inventory report — tables, columns, PK/FK coverage
argument-hint: <release-folder>
---

# Schema inventory report — tables, columns, PK/FK coverage

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
description: Generate a schema inventory report — tables, columns, row counts, and PK/FK coverage across all schemas in scope
argument-hint: <release-folder>
---

# Droughty Introspect Command

## Purpose

Produce a schema inventory report for all tables and columns in the Droughty-configured schemas. Reports table counts, column counts, estimated row counts, PK/FK coverage, null-rate signals, and data type distributions. Output lands in the Wire artifact directory as `schema_inventory.md` and is available to subsequent Wire commands as evidence for the problem definition, requirements, and data model phases.

This command uses the warehouse's `INFORMATION_SCHEMA` directly via the configured MCP or SQL connection — not the Droughty CLI itself — so it runs regardless of whether dbt models have been deployed.

## Usage

```bash
/wire:droughty-introspect <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete for this release
- Warehouse accessible (BigQuery MCP or Snowflake connection active)

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete`
3. Extract `warehouse`, `schemas`, and `profile_name`

If setup is not complete:
```
Error: Droughty setup not complete.

Run /wire:droughty-setup [release] first.
```

### Step 2: Query INFORMATION_SCHEMA

For each schema in `droughty.setup.schemas`, query the warehouse:

**BigQuery** (via BigQuery MCP or `bq` CLI):
```sql
SELECT
  table_schema,
  table_name,
  COUNT(*) AS column_count,
  SUM(CASE WHEN is_nullable = 'YES' THEN 1 ELSE 0 END) AS nullable_columns
FROM [project].[schema].INFORMATION_SCHEMA.COLUMNS
GROUP BY 1, 2
ORDER BY 1, 2
```

For row counts (approximate is fine):
```sql
SELECT
  table_schema,
  table_name,
  row_count
FROM [project].[schema].__TABLES__
ORDER BY 1, 2
```

**Snowflake** (via SQL):
```sql
SELECT
  table_schema,
  table_name,
  column_count,
  row_count
FROM information_schema.tables
WHERE table_schema IN ('[schema1]', '[schema2]')
ORDER BY 1, 2
```

### Step 3: Identify PK/FK Coverage

Scan column names for naming convention signals:
- Columns ending in `_pk` or `_id` (with no other `_pk` column on the table) → likely primary keys
- Columns ending in `_fk` or referencing another table by `[table]_id` pattern → likely foreign keys

Compute:
- `pk_coverage` — proportion of tables with at least one likely PK column
- `fk_coverage` — proportion of tables with at least one likely FK column

These are heuristics, not enforced constraints. Flag them clearly as inferred.

### Step 4: Generate Schema Inventory Report

Write to `.wire/releases/[release]/artifacts/droughty/schema_inventory.md`:

```markdown
# Schema Inventory — [client_name]

**Generated**: [today]
**Warehouse**: [warehouse_type]
**Schemas scanned**: [comma-separated list]
**Total tables**: [n]
**Total columns**: [n]

---

## Summary

| Metric | Value |
|---|---|
| Schemas in scope | [n] |
| Total tables | [n] |
| Tables with row counts | [n] |
| Estimated total rows | [n] |
| Tables with likely PK column | [n] ([pct]%) |
| Tables with at least one FK column | [n] ([pct]%) |

---

## Tables by Schema

### [schema_name]

| Table | Columns | Rows (approx) | PK col | FK cols |
|---|---|---|---|---|
| [table_name] | [n] | [n or —] | [col or —] | [cols or —] |
...

---

## Columns by Table

[For each table, list columns with type and nullable flag — truncated if >50 columns per table]

---

## Coverage Signals

**PK coverage** ([pct]% of tables have a likely primary key column):
Tables without a likely PK: [list]

**FK coverage** ([pct]% of tables have at least one FK reference column):
Tables with FK columns: [list with the FK column names]

---

## Notes

- Row counts are approximations from warehouse metadata, not COUNT(*) queries.
- PK/FK detection is based on column naming conventions (`_pk`, `_fk`, `_id` suffixes). Confirm against actual constraints or dbt schema.yml tests.
- This inventory was generated on [today] and reflects the current warehouse state.
```

### Step 5: Update status.md

```yaml
droughty:
  introspect:
    status: complete
    tables_found: [n]
    columns_found: [n]
    schemas_scanned: [[list]]
    pk_coverage_pct: [n]
    artifact: .wire/releases/[release]/artifacts/droughty/schema_inventory.md
    completed_date: [today]
```

### Step 6: Confirm Output

```
## Schema Inventory Complete ✅

[n] tables across [n] schemas — [n] columns total
PK coverage: [pct]% | FK coverage: [pct]%

Artifact: .wire/releases/[release]/artifacts/droughty/schema_inventory.md

This inventory is now available to:
  /wire:problem-definition-generate    — embeds the schema summary as evidence
  /wire:requirements-generate          — seeds the data landscape section
  /wire:droughty-dbml [release]        — generates the entity-relationship diagram
```

## Output

This command creates:
- `.wire/releases/[release]/artifacts/droughty/schema_inventory.md`
- Updated `droughty.introspect` block in `status.md`

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
