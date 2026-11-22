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
description: Generate dbt warehouse models (_dim/_fact/_agg/_xa) ready for BI consumption
argument-hint: <project-folder> [--slice <slice>]
delegates_to:
  - utils/precondition_gate
---

# dbt Warehouse Models — Generate

## Purpose

Generate the warehouse layer: dimension tables (`_dim`), fact tables (`_fact`) and extended aggregate tables (`_xa`). They read integration models, or staging models where no integration model is needed. Primary and foreign keys are created here. These are the final materialized tables consumed by the semantic layer and BI tools. Existing `_agg` models stay as they are.

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

- `dbt_integration: generate: complete` in status.md
- Data model design at `.wire/<project_id>/design/data_model_specification.md`

This is the third and final step of the per-layer alternative to the monolithic `/wire:dbt-generate`. Run `/wire:dbt-staging-generate` and `/wire:dbt-integration-generate` (and their validate steps) first — this command reads `.wire/<project_id>/dev/dbt_integration_summary.md`, which only exists once the integration layer has been generated.

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and reads and writes the slice's warehouse models and their `schema.yml` entries only
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

1. Read `.wire/<project_id>/design/data_model_specification.md` for warehouse layer design
2. Read `.wire/<project_id>/dev/dbt_integration_summary.md` for available integration models

### Step 1.5: Load Conventions

Priority order: rulings in `decisions.md` and `form_choices:` in the project's `.wire/conventions/dbt.yml`, then project convention files, then the conventions in `specs/development/dbt_generate.md`, Step 3.

Warehouse-layer rules:
- Model names are singular: `wh_<group>__<entity>_dim`, `wh_<group>__<entity>_fact`, `wh_<group>__<entity>_xa`.
- Dimension and fact models read integration models, or staging where no integration model is needed. Never base models or sources.
- Primary keys (`<entity>_pk`) and foreign keys (`<referenced_entity>_fk`) are created here, and only here, via `dbt_utils.generate_surrogate_key`. A foreign key is built from the same inputs as the primary key it references.
- An entity's attributes live on its dimension. Other models reference the entity by foreign key.
- Every output column carries the entity prefix; foreign keys keep the referenced entity's prefix. Booleans are `<entity>_is_`, `<entity>_has_`, `<entity>_was_`. Aggregated columns lead with the function (`sum_`, `count_`, `max_by_`).
- Columns in eight groups, each opened by a Jinja comment: `{# primary key #}`, `{# foreign keys #}`, `{# natural keys #}`, `{# attributes #}`, `{# indexes and ranks #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal #}`.
- Every model's `config()` `description` opens with `Grain: One row per ...`. Lines up to 120 characters. Last CTE `final`; model ends with `select * from final`.
- Materialized as a table by the folder config. A model may be `incremental` where the client decides; the client sets the strategy.

### Step 2: Generate Dimension Tables

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_dim.sql`

**SCD Type 1 (current state):**
```sql
{{
    config(
        description = """
            Grain: One row per <entity>.
            <What the dimension holds.>
        """,
        tags = ['warehouse', 'dimension'],
        cluster_by = ['<entity>_pk']
    )
}}

with s_<entities> as (

    select * from {{ ref('int_<group>__<entities>') }}

),

add_primary_key as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['<entity>_natural_key']) }} as <entity>_pk,
        {# natural keys #}
        <entity>_natural_key,
        {# attributes #}
        <entity>_<attribute_1>,
        <entity>_<attribute_2>,
        {# booleans #}
        <entity>_is_<state>,
        {# temporal #}
        <entity>_created_ts

    from s_<entities>

),

final as (

    select * from add_primary_key

)

select * from final
```

**SCD Type 2 (historical tracking):** prefer a snapshot of the source (`snapshots/snapshot_<source>/snapshot_<source>__<source_table>.sql`, read by staging). The dimension holds one row per version, with the primary key built from `<entity>_natural_key` and `<entity>_valid_from_ts`, plus `<entity>_valid_to_ts` and `<entity>_is_current`. Where a snapshot is not possible, use `materialized='incremental'` with `unique_key='<entity>_pk'`. Full template in `specs/development/dbt_generate.md`, Step 5.

### Step 3: Generate Fact Tables

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_fact.sql`

```sql
{{
    config(
        description = """
            Grain: One row per <event>.
            <What the fact holds.>
        """,
        tags = ['warehouse', 'fact'],
        cluster_by = ['<event>_<event>_dt', '<dimension>_fk']
    )
}}

with s_<events> as (

    select * from {{ ref('int_<group>__<events>') }}

),

add_keys as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['<event>_natural_key']) }} as <event>_pk,
        {# foreign keys #}
        {{ dbt_utils.generate_surrogate_key(['<event>_<dimension>_natural_key']) }} as <dimension>_fk,
        {# natural keys #}
        <event>_natural_key,
        <event>_<dimension>_natural_key,
        {# metrics #}
        <event>_<measure>_amount,
        <event>_<thing>_count,
        {# booleans #}
        <event>_is_<state>,
        {# temporal #}
        <event>_<event>_dt

    from s_<events>

),

final as (

    select * from add_keys

)

select * from final
```

### Step 4: Generate Extended Aggregate Tables (if required)

**File:** `dbt/models/warehouse/wh_<group>/wh_<group>__<entity>_xa.sql`

`_xa` means extended aggregate: a denormalised table built from fact and dimension models. It either aggregates to a summary grain (such as a daily summary) or combines several facts at a shared grain (such as an event stream).

```sql
{{
    config(
        description = """
            Grain: One row per <dimension> per day.
            Daily summary of <events>.
        """,
        tags = ['warehouse', 'extended_aggregate']
    )
}}

with s_<event>_facts as (

    select * from {{ ref('wh_<group>__<event>_fact') }}

),

aggregated as (

    select

        <dimension>_fk,
        <event>_<event>_dt,
        count(*) as count_<event>_pk,
        sum(<event>_<measure>_amount) as sum_<event>_<measure>_amount

    from s_<event>_facts

    group by <dimension>_fk, <event>_<event>_dt

),

add_primary_key as (

    select

        {# primary key #}
        {{ dbt_utils.generate_surrogate_key(['<dimension>_fk', '<event>_<event>_dt']) }} as <entity>_pk,
        {# foreign keys #}
        <dimension>_fk,
        {# metrics #}
        count_<event>_pk,
        sum_<event>_<measure>_amount,
        {# temporal #}
        <event>_<event>_dt

    from aggregated

),

final as (

    select * from add_primary_key

)

select * from final
```

### Step 4.5: Existing Aggregate and Bridge Models

New aggregate models use `_xa`. Existing `_agg` models keep their names, and an existing `_xa` model built as a cross-attribute or bridge table keeps its name and shape. Do not rename either.

### Step 5: Generate Macros (if needed)

**File:** `dbt/macros/macro__<name>.sql` (utility macros in `dbt/macros/utility/`), one macro per file, named `macro__<name>`, with adapter versions in the same file. Describe each new macro in `dbt/macros/_schema_macros.yml` (`name`, `description`, `arguments` with `name`, `type`, `description`). dbt override macros such as `generate_schema_name` keep their dbt names. Existing macros keep their names.

### Step 6: Generate Schema Documentation

**File:** `dbt/models/warehouse/wh_<group>/_schema.yml` (not where the project uses droughty, which writes `models/droughty_schema.yml`). An existing project adds entries to its current schema file (for example `wh_<group>.yml`).

- Every model has a description opening `Grain: One row per ...`. Every column is documented with a doc block in `models/field_descriptions.md`, referenced as `'{{ doc("<column>") }}'`.
- Primary keys: `unique` + `not_null`.
- Foreign keys: `not_null` + `dbt_utils.at_least_one` + `relationships: to: ref('wh_<group>__<dim>_dim'), field: <dim>_pk`.
- Other columns: `not_null` + `dbt_utils.at_least_one`. `at_least_one` never replaces `not_null`. Drop `not_null` only where the column can be null, and note why.
- Test key: `data_tests:` on dbt 1.8 or later, `tests:` before (find the version from `dbt --version`, `require-dbt-version`, or the pinned dbt or adapter version). A `form_choices: test_key` ruling wins. Keep `tests:` in a schema file that already uses it. If the version cannot be found, write `tests:`. Never both on one resource.
- In a new project, `dbt_project.yml` sets `+meta` `required_docs: true` and `required_tests: {"unique": 1, "not_null": 1}` on the warehouse layer (`required_docs: false` where the project uses droughty). Where `packages.yml` includes `dbt_meta_testing`, check with `dbt run-operation required_docs` and `dbt run-operation required_tests`. In an existing project, do not add these; list them as suggestions in the summary.

**Type Casting:** always use cast macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_int() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`. Dates use `{{ ra_type_date() }}` in new projects; an existing project keeps its date macro (for example `{{ type_date() }}`).

**Field ordering in `select` lists:** primary key → foreign keys → natural keys → attributes → indexes and ranks → metrics → booleans → temporal, each group opened by its `{# group #}` comment.

### Step 6.5: Convention Self-Check

Resolve the convention file: the project's `.wire/conventions/dbt.yml` if present, else the plugin's `conventions/dbt.yml`. Then run:

```bash
# New project
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/warehouse --new-project

# Existing project (added and changed models only)
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/warehouse \
  --changed-from "$(git merge-base HEAD <release branch>)"
```

Fix every `error` finding in the generated models without renaming or moving anything that already existed. List warnings in the summary with a reason.

### Step 7: Create Summary Document

**File:** `.wire/<project_id>/dev/dbt_warehouse_summary.md`

Include: whether the project is new or existing, the convention file and any `form_choices:` rulings applied, the test key used, dimensions, facts and extended aggregates created with their grain, any column where `not_null` was dropped (with the reason), the convention lint result, and, for an existing project, the `dbt_project.yml` / `packages.yml` suggestions.

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
- <count> extended aggregate (_xa) tables in dbt/models/warehouse/wh_<group>/

Next steps:
1. /wire:dbt-warehouse-validate <project_id>
2. /wire:semantic_layer-generate <project_id>
```
