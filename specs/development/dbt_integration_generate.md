---
wire_schema: "1.0"
command: utility
artifact: dbt
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: utility
logs_execution: true
preconditions: dynamic
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
description: Generate dbt integration-layer models (int_<group>__) applying business logic and cross-source joins
argument-hint: <project-folder> [--slice <slice>]
delegates_to:
  - utils/precondition_gate
---

# dbt Integration Models — Generate

## Purpose

Generate the integration layer: `int_<group>__` models that apply business logic, cross-source joins, deduplication, and entity resolution on top of validated staging models. No `{{ source() }}` calls: only `{{ ref() }}` to staging and intermediate models, never to base models. Create an integration model only where one is needed; otherwise the warehouse model reads staging.

## Existing projects

These rules apply before every other rule in this spec.

- Never rename or move an existing model, column, seed, snapshot or schema. The conventions below apply to new and changed code only.
- Names in the release's approved data model specification (`data_model.review: approved` in `status.md`) are used as written, even where they do not follow the naming rules in this spec or the convention. Do not rename an approved name, and do not stop to ask about it. List each one that differs from the convention in the generate report, marked "approved in the data model specification".
- Where the data model specification is not yet approved, use the convention's form, and list each name that differs from the specification in the generate report for the data model review to settle.
- A model or column the specification does not name follows the convention.
- Where the project keeps an old form (for example singular staging names, unprefixed columns, `tests:`, or `_<source>__sources.yml`), follow the ruling recorded in the release's `decisions.md` and the `form_choices:` block in the project's `.wire/conventions/dbt.yml`. Generate new models in that form. Keys: `model_name_number: plural|singular`, `column_prefix: entity|none`, `test_key: data_tests|tests`, `source_file_name: _sources|_<source>__sources`.
- Where no ruling exists, generate new models in the new form. Mixed naming inside one project is allowed.
- Do not change `dbt_project.yml` or `packages.yml` in an existing project. Report differences from the new-project templates in `specs/development/dbt_generate.md` (Step 8) as suggestions only.
- Keep the date-cast macro the project already uses (`type_date()` or similar). `ra_type_date()` is for new projects.

A project is new when this command creates its `dbt_project.yml`; otherwise it is existing.

## Prerequisites

- `dbt_staging: generate: complete` in status.md
- Data model design at `.wire/<project_id>/design/data_model_specification.md`

This is the second step of the per-layer alternative to the monolithic `/wire:dbt-generate`. Run `/wire:dbt-staging-generate` (and ideally `/wire:dbt-staging-validate`) first — this command reads `.wire/<project_id>/dev/dbt_staging_summary.md`, which only exists once the staging layer has been generated.

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and reads and writes the slice's integration models and their `schema.yml` entries only
(`specs/utils/ticket_delivery.md`, "The `--slice` option"). Without
`--slice`, the workflow below runs as written.

1. The slice must be in `tickets.yaml`. If it is not, stop and list the valid
   slices.
2. The precondition gate evaluates this slice's dependencies, not the whole
   release's (`specs/utils/precondition_gate.md`, "Sliced runs").
3. Add or replace the slice's part only. Never regenerate the whole document
   or project to change one slice; every other line stays as it is.
4. On a ticket branch, write the step's result to the ticket record's front
   matter (`results:`) and the log row to the ticket run log
   (`iterations/<ticket>.execution_log.md`), not to `status.md` and
   `execution_log.md`. The status and Jira or Linear updates in the workflow
   below are made by `/wire:status-sync`'s ticket roll-up when the pull request
   merges.

## Workflow

### Step 1: Read Upstream Context

1. Read `.wire/<project_id>/design/data_model_specification.md` for integration-layer design
2. Read `.wire/<project_id>/dev/dbt_staging_summary.md` for available staging models

### Step 1.5: Load Conventions

Priority order: rulings in `decisions.md` and `form_choices:` in the project's `.wire/conventions/dbt.yml`, then project convention files, then the conventions in `specs/development/dbt_generate.md`, Step 3.

Integration-layer rules:
- An integration model exists only where one is needed: a join across sources, a filter to the concept the warehouse exposes, or derived fields. Otherwise the warehouse model reads staging directly.
- Integration models read staging and intermediate models only, never base models or sources.
- Model names are plural: `int_<group>__<entities>`, `int_<group>__<entities>__<verb>`.
- Every output column carries the entity prefix. New columns follow staging conventions: lowercased attribute strings (never natural keys or identifiers), cast macros, `ra_type_date()` for dates in new projects (an existing project keeps its date macro).
- No primary or foreign keys. They are created in the warehouse layer.
- Aggregated columns lead with the function: `sum_invoice_line_item_amount`, `max_by_activity_user_name`.
- Columns in eight groups, each opened by a Jinja comment: `{# primary key #}`, `{# foreign keys #}`, `{# natural keys #}`, `{# attributes #}`, `{# indexes and ranks #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal #}` (omit groups the model does not have).
- Every model's `config()` `description` opens with `Grain: One row per ...`. Lines up to 120 characters. Last CTE `final`; model ends with `select * from final`. A CTE that removes rows carries a comment saying why.

### Step 2: Generate Intermediate Models (if needed)

Where the same concept arrives from more than one source, combine it in an intermediate model first:

**File:** `dbt/models/integration/int_<group>/intermediate/int_<group>__<entities>__<verb>.sql` (verb is past tense, e.g. `unioned`, `deduped`)

New intermediate models are views, set by the integration folder config. They carry no `materialized` setting. An existing project that sets intermediate models to `ephemeral` keeps that setting.

```sql
{{
    config(
        description = """
            Grain: One row per <entity> per source system.
            <Entities> from <source_a> and <source_b>, unioned.
        """,
        tags = ['integration', 'intermediate']
    )
}}

with s_<source_a>_<entities> as (

    select * from {{ ref('stg_<source_a>__<entities>') }}

),

s_<source_b>_<entities> as (

    select * from {{ ref('stg_<source_b>__<entities>') }}

),

unioned as (

    select

        {# natural keys #}
        <entity>_natural_key,
        {# attributes #}
        <entity>_name,
        '<source_a>' as <entity>_source_system_name

    from s_<source_a>_<entities>

    union all

    select

        {# natural keys #}
        <entity>_natural_key,
        {# attributes #}
        <entity>_name,
        '<source_b>' as <entity>_source_system_name

    from s_<source_b>_<entities>

),

final as (

    select * from unioned

)

select * from final
```

### Step 3: Generate Final Integration Models

**File:** `dbt/models/integration/int_<group>/int_<group>__<entities>.sql`

```sql
{{
    config(
        description = """
            Grain: One row per <entity>.
            <What the model holds.>
        """,
        tags = ['integration']
    )
}}

with s_<entities> as (

    select * from {{ ref('int_<group>__<entities>__unioned') }}

),

s_<others> as (

    select * from {{ ref('stg_<source>__<others>') }}

),

joined as (

    select

        {# natural keys #}
        s_<entities>.<entity>_natural_key,
        {# attributes #}
        s_<entities>.<entity>_name,
        s_<others>.<other>_name as <entity>_<other>_name

    from s_<entities>
    left join s_<others>
        on s_<entities>.<entity>_<other>_natural_key = s_<others>.<other>_natural_key

),

final as (

    select * from joined

)

select * from final
```

### Step 4: Multi-Source Framework (if applicable)

If the data model identifies multiple source systems for the same entity, apply the configuration-driven merge pattern (full example in `specs/development/dbt_generate.md`, Step 5.5):

1. Add source arrays to `dbt_project.yml` vars (e.g. `crm_company_sources: ['hubspot', 'salesforce']`)
2. Create a merge macro: `dbt/macros/macro__merge_sources.sql` in a new project, described in `macros/_schema_macros.yml`. An existing project keeps `merge_sources` where it is.
3. Use `{{ macro__merge_sources(sources=var('crm_company_sources'), model_suffix='__companies') }}` in integration models (or the existing macro name)
4. Deduplicate using `array_agg(distinct <entity>_natural_key)` and `max`/`min` for attribute resolution, with aggregated columns named for the function (`max_company_website`)

### Step 5: Create Schema Documentation

**File:** `dbt/models/integration/int_<group>/_schema.yml` (not where the project uses droughty). An existing project adds entries to its current schema file (for example `integration.yml`).

- Document every `int_<group>__` and intermediate model and every column. Column descriptions reference doc blocks in `models/field_descriptions.md` (`'{{ doc("<column>") }}'`); add a doc block for each new column.
- Tests: the natural key that identifies a row gets `unique` + `not_null`. Other columns get `not_null` + `dbt_utils.at_least_one`; `at_least_one` never replaces `not_null`. Drop `not_null` only where the column can be null, and note why.
- Test key: `data_tests:` on dbt 1.8 or later, `tests:` before (find the version from `dbt --version`, `require-dbt-version`, or the pinned dbt or adapter version). A `form_choices: test_key` ruling wins. Keep `tests:` in a schema file that already uses it. If the version cannot be found, write `tests:`. Never both on one resource.

### Step 5.5: Convention Self-Check

Resolve the convention file: the project's `.wire/conventions/dbt.yml` if present, else the plugin's `conventions/dbt.yml`. Then run:

```bash
# New project
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/integration --new-project

# Existing project (added and changed models only)
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/integration \
  --changed-from "$(git merge-base HEAD <release branch>)"
```

Fix every `error` finding in the generated models without renaming or moving anything that already existed. List warnings in the summary with a reason.

### Step 6: Create Summary Document

**File:** `.wire/<project_id>/dev/dbt_integration_summary.md`

Include: whether the project is new or existing, the convention file and any `form_choices:` rulings applied, the test key used, intermediate and integration models with their grain, entities covered, cross-source joins applied, any column where `not_null` was dropped (with the reason), and the convention lint result.

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
