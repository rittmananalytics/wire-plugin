---
description: Generate dbt warehouse-layer models only (alternative to the monolithic dbt-generate)
argument-hint: <project-folder>
---

# Generate dbt warehouse-layer models only (alternative to the monolithic dbt-generate)

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
description: Generate dbt warehouse models (_dim/_fact/_agg/_xa) ready for BI consumption
argument-hint: <project-folder>
---

# dbt Warehouse Models — Generate

## Purpose

Generate the warehouse layer: dimension tables (`_dim`), fact tables (`_fact`), aggregate tables (`_agg`), and cross-attribute / bridge tables (`_xa`) that reference only integration models. These are the final materialized tables consumed by the semantic layer and BI tools.

## Prerequisites

- `dbt_integration: generate: complete` in status.md
- Data model design at `.wire/<project_id>/design/data_model_specification.md`

This is the third and final step of the per-layer alternative to the monolithic `/wire:dbt-generate`. Run `/wire:dbt-staging-generate` and `/wire:dbt-integration-generate` (and their validate steps) first — this command reads `.wire/<project_id>/dev/dbt_integration_summary.md`, which only exists once the integration layer has been generated.

## Workflow

### Step 1: Read Upstream Context

1. Read `.wire/<project_id>/design/data_model_specification.md` for warehouse layer design
2. Read `.wire/<project_id>/dev/dbt_integration_summary.md` for available integration models

### Step 2: Generate Dimension Tables

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_dim.sql`

**SCD Type 1 (current state):**
```sql
{{
    config(
        materialized='table',
        tags=['warehouse', 'dimension'],
        cluster_by=['<entity>_pk']
    )
}}

with

s_<entity> as (
    select * from {{ ref('int_<group>__<entity>') }}
),

final as (
    select
        -- Keys
        <entity>_pk,
        <entity>_natural_key,

        -- Attributes
        <attribute_1>,
        <attribute_2>,

        -- Booleans
        is_current,

        -- Temporal data types
        current_timestamp() as dbt_updated_ts
    from s_<entity>
)

select * from final
```

**SCD Type 2 (historical tracking):** Use `materialized='incremental'`, `unique_key='<entity>_pk'` with `valid_from`, `valid_to`, `is_current` columns.

### Step 3: Generate Fact Tables

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_fact.sql`

```sql
{{
    config(
        materialized='table',
        tags=['warehouse', 'fact'],
        cluster_by=['<date_fk>', '<dimension_fk>']
    )
}}

with

s_<event> as (
    select * from {{ ref('int_<group>__<event>') }}
),

s_<dim> as (
    select * from {{ ref('wh_<group>__<dim>_dim') }}
),

final as (
    select
        -- Keys
        {{ dbt_utils.generate_surrogate_key(['<id_columns>']) }} as <fact>_pk,
        s_<dim>.<dim>_pk as <dim>_fk,

        -- Metrics
        s_<event>.<measure_1>,
        s_<event>.<measure_2_amount>,

        -- Temporal data types
        current_timestamp() as dbt_updated_ts
    from s_<event>
    left join s_<dim> on s_<event>.<dim>_id = s_<dim>.<dim>_id
)

select * from final
```

### Step 4: Generate Aggregate Tables (if required)

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_agg.sql`

```sql
{{
    config(
        materialized='table',
        tags=['warehouse', 'aggregate']
    )
}}

with

s_fact as (
    select * from {{ ref('wh_<group>__<entity>_fact') }}
),

final as (
    select
        <dimension_fk>,
        count(*) as total_count,
        sum(<measure>) as total_<measure>_amount
    from s_fact
    group by 1
)

select * from final
```

### Step 4.5: Generate Cross-Attribute / Bridge Tables (if required)

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_xa.sql` — for bridge / many-to-many / cross-entity attribute models (e.g. user-to-role, product-to-category).

### Step 5: Generate Macros (if needed)

**File:** `dbt/macros/<macro_name>.sql` — for shared business logic (e.g., date spine helpers, derived field calculations).

### Step 6: Generate Schema Documentation

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>.yml` — dimensions, facts, aggregates, and cross-attribute tables with relationship tests.

Include relationship tests: `relationships: to: ref('wh_<group>__<dim>_dim'), field: <dim>_pk`.

**Type Casting:** always use dbt's type-cast macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`, `{{ type_date() }}` (community macro, no `dbt.` prefix).

**Field ordering in `select` lists:** keys → attributes → indexes/ranks → metrics → booleans → temporal data types (dates/timestamps last).

### Step 7: Create Summary Document

**File:** `.wire/<project_id>/dev/dbt_warehouse_summary.md`

Include: list of dimensions, facts, aggregates, and cross-attribute tables created with row-grain descriptions.

### Step 8: Update Status

```
dbt_warehouse:
  generate: complete
```

### Step 9: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dbt_warehouse`
- `artifact_name`: `dbt Warehouse Summary`
- `file_path`: `.wire/<project_id>/dev/dbt_warehouse_summary.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 10: Suggest Next Steps

```
## Warehouse Models Generated

- <count> dimension tables in dbt/models/warehouse/wh_<group>/
- <count> fact tables in dbt/models/warehouse/wh_<group>/
- <count> aggregate tables in dbt/models/warehouse/wh_<group>/
- <count> cross-attribute / bridge tables in dbt/models/warehouse/wh_<group>/

Next steps:
1. /wire:dbt-warehouse-validate <project_id>
2. /wire:semantic_layer-generate <project_id>
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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
