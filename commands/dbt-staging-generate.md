---
description: Generate dbt staging-layer models only (alternative to the monolithic dbt-generate)
argument-hint: <project-folder>
---

# Generate dbt staging-layer models only (alternative to the monolithic dbt-generate)

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
description: Generate dbt staging models (stg_) that clean and standardize raw source data
argument-hint: <project-folder>
---

# dbt Staging Models — Generate

## Purpose

Generate the staging layer of the dbt project: one model per source table, applying cleaning, renaming, type casting, and surrogate key generation. Only staging models may use `{{ source() }}`; all other layers use `{{ ref() }}`.

## Prerequisites

- `data_model`: dbt model design specification must be complete — read `.wire/<project_id>/design/data_model_specification.md`

This is the first step of the per-layer alternative to the monolithic `/wire:dbt-generate` — it can be run standalone on any project that has an approved data model, without `dbt-generate` having been run first.

## Workflow

### Step 1: Read Data Model Design

Read `.wire/<project_id>/design/data_model_specification.md` and extract:
- Source systems and tables
- Column mappings and renames
- Required tests and naming conventions

### Step 2: Load Naming Conventions

Priority order:
1. Project-specific: `.dbt-conventions.md`, `dbt_coding_conventions.md`, or `docs/dbt_conventions.md` in repo root
2. Embedded conventions below (fallback)

**Naming conventions:**

| Type | Pattern | Example |
|------|---------|---------|
| Primary Key | `<object>_pk` | `user_pk` |
| Foreign Key | `<referenced_object>_fk` | `account_fk` |
| Natural Key | `<source>_<entity>_natural_key` | `salesforce_user_natural_key` |
| Timestamp | `<event>_ts` | `created_ts` |
| Boolean | `is_<state>` / `has_<thing>` | `is_active` |

**SQL style:** 4-space indent, lowercase, explicit joins, all refs in CTEs prefixed `s_`, final CTE always named `final`.

### Step 3: Determine dbt Project Location

Check for existing dbt project at `dbt/`, `transform/`, or similar. If ambiguous, ask the user. Default to `dbt/`.

### Step 4: Generate Staging Models

For each source table, create:

**File:** `dbt/models/staging/<source_system>/stg_<source>__<table>.sql`

```sql
{{
    config(
        materialized='view',
        tags=['staging', '<source_system>']
    )
}}

with

s_<source_system>_<table> as (
    select * from {{ source('<source_system>', '<table_name>') }}
),

final as (
    select
        -- Keys
        {{ dbt_utils.generate_surrogate_key(['<id_column>']) }}
            as <table>_pk,
        <id_column> as <source>_<table>_natural_key,

        -- Timestamps
        cast(<date_column> as timestamp) as <event>_ts,

        -- Attributes
        lower(trim(<source_column>)) as <standard_name>,

        -- Metadata
        current_timestamp() as dbt_loaded_ts

    from s_<source_system>_<table>
)

select * from final
```

**Also create:** `dbt/models/staging/<source_system>/stg_<source_system>.yml` with source and model definitions, not_null and unique tests on primary keys.

### Step 5: Generate dbt_project.yml (if new project)

Create `dbt/dbt_project.yml` with staging, integration, and warehouse model path configurations.

### Step 6: Create Summary Document

**File:** `.wire/<project_id>/dev/dbt_staging_summary.md`

Include: list of staging models created, source tables covered, tests configured.

### Step 7: Update Status

Update `.wire/<project_id>/status.md`:
```
dbt_staging:
  generate: complete
```

### Step 8: Suggest Next Steps

```
## Staging Models Generated

- <count> staging models created in dbt/models/staging/
- Next: /wire:dbt-staging-validate <project_id>
- Then: /wire:dbt-integration-generate <project_id>
```

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
