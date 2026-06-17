---
description: Catalog dbt models with complexity classification and feature detection
argument-hint: <release-folder>
---

# Catalog dbt models with complexity classification and feature detection

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
description: Catalog dbt models with complexity classification and feature detection
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: dbt_audit` and `artifact_file_path: audit/dbt_audit.md` before proceeding.

---

# dbt Audit — Generate

## Purpose

Catalogs every model, source, test, macro, seed, and snapshot in the dbt project. Classifies each model by complexity based on SQL feature usage, line count, and dependency depth. The output drives the batching strategy for dbt_migration and the complexity weighting in the migration inventory.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- dbt project path accessible at `migration.dbt_project_path` (default: `./dbt`)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — dbt_project_path, source_platform
- dbt project files at `migration.dbt_project_path`

## Workflow

### Step 1: Locate the release and dbt project

Confirm `release_type: platform_migration`. Read `migration.dbt_project_path` (default: `./dbt`).

Check the path exists and contains `dbt_project.yml`. If not found, ask the user to confirm the correct path.

### Step 2: Inventory project components

Parse the dbt project:

**Models**: For each `.sql` file under `models/`:
- File path and model name
- Layer (staging, intermediate, mart — inferred from path or prefix)
- Line count
- Number of `ref()` calls (upstream dependencies)
- Number of `source()` calls
- Number of CTEs
- SQL feature tags (see Step 3)

**Sources**: Count and list all sources defined in `schema.yml` files.

**Tests**: Count generic and singular tests. Note which models have no tests.

**Macros**: List all macros in the `macros/` directory. Flag macros that use adapter-specific functions (`adapter.dispatch`, `dbt_utils` functions with platform behaviour differences).

**Seeds**: List all seed files with row counts.

**Snapshots**: List all snapshots with their strategy (timestamp / check).

**Analyses**: List any files in `analyses/`.

### Step 3: Detect platform-specific SQL features per model

For each model SQL file, apply the feature detection patterns from the platform pair file:

- BigQuery source: load `wire/platform_pairs/bigquery_to_snowflake/feature_detection.md`
- Snowflake source: load `wire/platform_pairs/snowflake_to_bigquery/feature_detection.md`

Tag each model with every feature pattern that matches. A model with no matches gets an empty tag list.

### Step 4: Classify complexity

Assign each model a complexity rating:

**Simple**:
- ≤100 lines
- 0 platform-specific feature tags
- ≤3 upstream refs
- No window functions or recursive CTEs

**Moderate**:
- 101–300 lines, OR
- 1–3 platform-specific feature tags, OR
- 4–10 upstream refs, OR
- Uses window functions but no nested STRUCT/ARRAY operations

**Complex**:
- >300 lines, OR
- >3 platform-specific feature tags, OR
- >10 upstream refs, OR
- Uses UNNEST, STRUCT, FLATTEN, LATERAL, ML functions, or GEOGRAPHY operations

### Step 5: Build migration batches

Group models into translation batches of no more than 20 models each. Order batches by the dependency graph — models with no upstream dbt refs first, leaf nodes last. Within each batch, order Simple before Moderate before Complex.

Assign each model a `batch_number` (1-indexed).

### Step 6: Write the audit report and CSV

**Output locations**:
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md` — narrative report with summary statistics
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — machine-readable model catalog

Use the templates at `TEMPLATES/migration/dbt_audit.md` and `TEMPLATES/migration/dbt_audit.csv`.

The CSV must contain:
`model_name, file_path, layer, line_count, ref_count, source_count, cte_count, complexity, feature_tags, batch_number, has_tests, migration_notes`

### Step 7: Update status

```yaml
artifacts:
  dbt_audit:
    generate: complete
    file: audit/dbt_audit.md
    generated_date: "{{TODAY}}"
    model_count: N
    simple_count: N
    moderate_count: N
    complex_count: N
    batch_count: N
    macro_count: N
    source_count: N
    test_count: N
```

### Step 8: Output summary

Print: total models, breakdown by complexity, number of batches, most common feature tags, and next command:

```
/wire:dbt-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md`
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_audit` as artifact_id, `dbt Audit` as artifact_name, and the `file` value from `artifacts.dbt_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_audit` as artifact, `generate` as action.

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
