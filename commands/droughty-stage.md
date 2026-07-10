---
description: Staging SQL and sources.yml generation (BigQuery only)
argument-hint: <release-folder>
---

# Staging SQL and sources.yml generation (BigQuery only)

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
description: Generate dbt staging models and sources.yml from a BigQuery dataset (BigQuery only)
argument-hint: <release-folder>
---

# Droughty Stage Command

## Purpose

Run `droughty stage` to generate dbt staging model SQL files and a `sources.yml` declaration from a BigQuery dataset in one operation. Each source table gets a `stg_<table_name>.sql` file that selects all columns with basic renaming conventions applied, plus a `sources.yml` entry for the parent dataset. Output lands in the dbt project staging directory.

**BigQuery only.** Snowflake staging model generation is not supported by `droughty stage`.

## Usage

```bash
/wire:droughty-stage <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete (BigQuery only)
- dbt project exists at the path configured in `droughty_project.yaml`
- The target dataset exists in BigQuery and is accessible

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete` and `droughty.setup.warehouse == bigquery`
3. Read `dbt_project_path` and `stage_path` from the setup block

If warehouse is Snowflake:
```
Error: droughty stage is a BigQuery-only command.

For Snowflake staging models, use /wire:dbt-generate which produces staging SQL
compatible with any warehouse.
```

### Step 2: Confirm Deployment Status

**Important**: `droughty stage` generates staging models from source tables, not from dbt-managed tables. Confirm the source dataset exists:

```
droughty stage will generate staging models for source tables in BigQuery.
This command does not require dbt to have been run.

Confirm: which BigQuery project and dataset contains the source tables?
(e.g. project: acme-raw-data, dataset: salesforce_raw)
```

Ask:
1. "GCP project ID for the source data (may differ from analytics project):"
2. "Dataset name containing the source tables:"
3. "Target a specific table, or all tables in the dataset? (table name or 'all'):"

### Step 3: Run droughty stage

```bash
droughty stage \
  --profile-dir ~/.droughty \
  --project-dir . \
  -p [gcp_project_id] \
  -d [dataset] \
  [-t [table_name]]   # only if single table targeted
```

Capture stdout and stderr. Surface any errors verbatim.

### Step 4: Verify Output

Check that files were written to `stage_path` (from `droughty_project.yaml`, defaulting to `[dbt_project_path]/models/staging/`):
- `sources.yml` — source declarations for the dataset
- `stg_[table_name].sql` — one file per table

Report file count and list generated model names.

### Step 5: Merge Check for Existing sources.yml

If a `sources.yml` already exists in the staging directory, check for conflicts:
- If the same source/table is already declared, warn the consultant and offer to skip those entries or overwrite
- Never silently overwrite an existing `sources.yml`

```
⚠️  A sources.yml already exists in [stage_path].
Droughty has generated new entries for [n] tables.

Options:
  a) Merge — append new entries, skip duplicates
  b) Overwrite — replace existing sources.yml with Droughty output
  c) Review diff first
```

### Step 6: Update status.md

```yaml
droughty:
  stage:
    status: complete
    models_generated: [n]
    source_dataset: "[project].[dataset]"
    output_path: "[stage_path]"
    completed_date: [today]
```

### Step 7: Confirm Output

```
## Staging Models Generated ✅

[n] staging models written to [stage_path]
sources.yml updated with [n] source table declarations

Generated models:
  [list of stg_*.sql filenames]

Next steps:
  1. Review generated staging SQL — Droughty uses a straight SELECT with column aliasing.
     Add incremental logic, source freshness tests, or business logic transformations as needed.
  2. Run dbt to test the generated models:
     /wire:utils-run-dbt [release]
  3. Augment with schema tests:
     /wire:droughty-dbt-tests [release]
```

## Output

This command creates:
- `[stage_path]/stg_[table_name].sql` — one file per source table
- `[stage_path]/sources.yml` — source declarations
- Updated `droughty.stage` block in `status.md`

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
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
