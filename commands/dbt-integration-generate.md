---
description: Generate dbt integration-layer models only (alternative to the monolithic dbt-generate)
argument-hint: <project-folder>
---

# Generate dbt integration-layer models only (alternative to the monolithic dbt-generate)

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
description: Generate dbt integration-layer models (int_<group>__) applying business logic and cross-source joins
argument-hint: <project-folder>
---

# dbt Integration Models — Generate

## Purpose

Generate the integration layer: `int_<group>__` models that apply business logic, cross-source joins, deduplication, and entity resolution on top of validated staging models. No `{{ source() }}` calls — only `{{ ref() }}` to staging models.

## Prerequisites

- `dbt_staging: generate: complete` in status.md
- Data model design at `.wire/<project_id>/design/data_model_specification.md`

This is the second step of the per-layer alternative to the monolithic `/wire:dbt-generate`. Run `/wire:dbt-staging-generate` (and ideally `/wire:dbt-staging-validate`) first — this command reads `.wire/<project_id>/dev/dbt_staging_summary.md`, which only exists once the staging layer has been generated.

## Workflow

### Step 1: Read Upstream Context

1. Read `.wire/<project_id>/design/data_model_specification.md` for integration-layer design
2. Read `.wire/<project_id>/dev/dbt_staging_summary.md` for available staging models

### Step 2: Generate Intermediate Models (if needed)

For complex multi-step transformations, create intermediate ephemeral models first:

**File:** `dbt/models/integration/int_<group>/intermediate/int_<group>__<entity>__<action>.sql` (action is a past-tense verb, e.g. `unioned`, `deduped`)

```sql
{{
    config(
        materialized='ephemeral',
        tags=['integration', 'intermediate']
    )
}}

with

s_<entity> as (
    select * from {{ ref('stg_<group>__<entity>') }}
),

final as (
    select
        s_<entity>.*,
        <derived_field>
    from s_<entity>
)

select * from final
```

### Step 3: Generate Final Integration Models

**File:** `dbt/models/integration/int_<group>/int_<group>__<entity>.sql`

```sql
{{
    config(
        materialized='view',
        tags=['integration']
    )
}}

with

s_<entity> as (
    select * from {{ ref('stg_<source>__<entity>') }}
),

s_<other> as (
    select * from {{ ref('stg_<source>__<other>') }}
),

joined as (
    select
        s_<entity>.*,
        s_<other>.<field>
    from s_<entity>
    left join s_<other>
        on s_<entity>.<key> = s_<other>.<key>
),

final as (
    select * from joined
)

select * from final
```

### Step 4: Multi-Source Framework (if applicable)

If the data model identifies multiple source systems for the same entity, apply the configuration-driven merge pattern:

1. Add source arrays to `dbt_project.yml` vars (e.g. `crm_company_sources: ['hubspot', 'salesforce']`)
2. Create a `merge_sources` macro in `dbt/macros/merge_sources.sql`
3. Use `{{ merge_sources(sources=var('crm_company_sources'), model_suffix='__company') }}` in integration models
4. Deduplicate using `array_agg(distinct source_id)` pattern and `max`/`min` for attribute resolution

### Step 5: Create Schema Documentation

**File:** `dbt/models/integration/int_<group>/integration.yml`

Document all `int_<group>__` models with column descriptions for complex transformations.

### Step 6: Create Summary Document

**File:** `.wire/<project_id>/dev/dbt_integration_summary.md`

Include: list of integration models, entities covered, cross-source joins applied.

### Step 7: Update Status

```
dbt_integration:
  generate: complete
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dbt_integration`
- `artifact_name`: `dbt Integration Summary`
- `file_path`: `.wire/<project_id>/dev/dbt_integration_summary.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Suggest Next Steps

```
## Integration Models Generated

- <count> integration models created in dbt/models/integration/
- Next: /wire:dbt-integration-validate <project_id>
- Then: /wire:dbt-warehouse-generate <project_id>
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
