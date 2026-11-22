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
description: Generate dbt staging models (stg_) that clean and standardize raw source data
argument-hint: <project-folder> [--slice <slice>]
delegates_to:
  - utils/precondition_gate
---

# dbt Staging Models — Generate

## Purpose

Generate the staging layer of the dbt project: one model per source concept, applying cleaning, renaming, type casting and natural key extraction. Primary and foreign keys are created later, in the warehouse layer. Only staging models may read sources, snapshots and seeds; all other layers use `{{ ref() }}` to models.

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

- `data_model`: dbt model design specification must be complete — read `.wire/<project_id>/design/data_model_specification.md`

This is the first step of the per-layer alternative to the monolithic `/wire:dbt-generate` — it can be run standalone on any project that has an approved data model, without `dbt-generate` having been run first.

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and reads and writes the slice's staging models and their `schema.yml` entries only
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

### Step 1: Read Data Model Design

Read `.wire/<project_id>/design/data_model_specification.md` and extract:
- Source systems and tables
- Column mappings and renames
- Required tests and naming conventions

### Step 2: Load Naming Conventions

Priority order:
1. Rulings: `decisions.md` in the release, and `form_choices:` in the project's `.wire/conventions/dbt.yml`
2. Project-specific: `.wire/conventions/dbt.yml`, `.dbt-conventions.md`, `dbt_coding_conventions.md`, or `docs/dbt_conventions.md` in repo root
3. Embedded conventions below (fallback). The full tables are in `specs/development/dbt_generate.md`, Step 3.

**Naming conventions (staging):**

| Type | Pattern | Example |
|------|---------|---------|
| Model | `stg_<source>__<entities>` (plural) | `stg_salesforce__contacts` |
| Base model | `base_<source>__<entities>` | `base_salesforce__contacts` |
| Natural Key | `<entity>_natural_key`; on another entity it takes this model's prefix. Never lowercased | `contact_natural_key`, `contact_account_natural_key` |
| Attribute | `<entity>_<attribute>`, no suffix | `contact_email` (not `email`) |
| Count | `<entity>_<thing>_count` | `order_line_count` |
| Money | `<entity>_<measure>_amount` (base currency), `_amount_<currency>` otherwise; decimal, converted from cents here | `user_account_balance_amount`, `order_revenue_amount_usd` |
| Measured quantity | `<entity>_<measure>_<unit>` | `package_weight_kg`, `call_duration_seconds` |
| Percentage / ratio | `_pct` (0 to 100), `_ratio` (0 to 1) | `order_discount_pct` |
| Boolean | `<entity>_is_<state>`, `<entity>_has_<thing>`, `<entity>_was_<event>` | `user_is_active` |
| Date | `<entity>_<event>_dt` | `user_created_dt` |
| Timestamp (UTC) | `<entity>_<event>_ts` | `user_created_ts` |
| Timestamp (non-UTC) | `<entity>_<event>_<tz>_ts` | `user_created_cet_ts` |

Primary and foreign keys are not created in staging. They are created in the warehouse layer.

**Lowercasing:** lowercase attribute strings only. Never lowercase natural keys or source identifiers (some are case-sensitive, for example Salesforce 15-character IDs).

**Type Casting:** always use cast macros, never raw SQL types: `{{ dbt.type_string() }}`, `{{ dbt.type_numeric() }}`, `{{ dbt.type_int() }}`, `{{ dbt.type_boolean() }}`, `{{ dbt.type_timestamp() }}`. Dates use `{{ ra_type_date() }}` in new projects; an existing project keeps its date macro (for example `{{ type_date() }}`). Timestamps are cast to UTC.

**SQL style:** 4-space indent, lines up to 120 characters, lowercase, explicit joins, all refs in CTEs prefixed `s_`, last CTE named `final`, model ends with `select * from final`, Jinja delimiters with inner spaces (`{{ this }}`). Every model's `config()` carries a `description` whose first line is `Grain: One row per ...`. A CTE that removes rows carries a plain-English comment saying why.

**Field ordering in `select` lists:** eight groups, each opened by a Jinja comment: `{# primary key #}`, `{# foreign keys #}`, `{# natural keys #}`, `{# attributes #}`, `{# indexes and ranks #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal #}`. Staging models have no primary or foreign key groups.

**Staging design rules:**
- Only staging models read sources, snapshots and seeds.
- Joins are avoided. A join or union is allowed only within one source system, in a base model or base CTE.
- Filtering is limited to correctness (deduplication, rows known to be erroneous). Population and grain are preserved.
- Nested records are flattened. Repeated fields are carried through unchanged unless queried downstream.
- Single-row derivations are allowed. Repeated logic becomes a macro (`macros/macro__<name>.sql`, described in `macros/_schema_macros.yml`).

### Step 3: Determine dbt Project Location

Check for existing dbt project at `dbt/`, `transform/`, or similar. If ambiguous, ask the user. Default to `dbt/`.

### Step 4: Generate Staging Models

For each source concept, create:

**File:** `dbt/models/staging/stg_<source>/stg_<source>__<entities>.sql`

```sql
{{
    config(
        description = """
            Grain: One row per <entity> in <source table>.
            <What the model holds, as received from <source>.>
        """,
        tags = ['staging', '<source>']
    )
}}

with s_<source_table> as (

    select * from {{ source('<source>', '<table_name>') }}

),

-- Keeps the latest copy of each row. The loading tool can write a row more than once.
deduplicated as (

    select * from s_<source_table>
    qualify row_number() over (partition by <id_column> order by <loaded_at_column> desc) = 1

),

rename_and_cast as (

    select

        {# natural keys #}
        cast(<id_column> as {{ dbt.type_string() }}) as <entity>_natural_key,
        {# attributes #}
        lower(trim(cast(<name_column> as {{ dbt.type_string() }}))) as <entity>_name,
        {# metrics #}
        cast(<cents_column> as {{ dbt.type_numeric() }}) / 100 as <entity>_<measure>_amount,
        {# booleans #}
        cast(<status_column> as {{ dbt.type_boolean() }}) as <entity>_is_<state>,
        {# temporal #}
        cast(<date_column> as {{ ra_type_date() }}) as <entity>_<event>_dt,
        cast(<timestamp_column> as {{ dbt.type_timestamp() }}) as <entity>_<event>_ts

    from deduplicated

),

final as (

    select * from rename_and_cast

)

select * from final
```

**Base models (where needed):** `dbt/models/staging/stg_<source>/base_<source>__<entities>.sql` holds a join or union within one source system. Only the staging model of the same concept reads it. It takes its view materialization from the folder config.

**Snapshots (where needed):** `dbt/snapshots/snapshot_<source>/snapshot_<source>__<source_table>.sql`. The `{% snapshot %}` block name equals the file name. `timestamp` strategy by default; `check` with `check_cols` where the source has no reliable modified timestamp. Source columns unchanged; dbt meta columns keep their names. New projects write to the `snapshots` schema; an existing project keeps its snapshot schema. The staging model reads the snapshot as it reads a source.

**Seeds:** in a new project or new release, seed files are `seeds/seed__<description>.csv` in the `seeds` schema, with the CSV's column names. Only staging models read seeds. Dashboard-first mock seeds in a release already under way keep their names, so `data_refactor` still finds them.

**Also create:** `dbt/models/staging/stg_<source>/_sources.yml` (one per source folder; `_<source>__sources.yml` where a `source_file_name` ruling keeps it). Content rules:
- One source, named for the folder without `stg_`. `schema` and `loader` set.
- Table `name` is the business name; `identifier` holds the raw name where different.
- Table description opens `Grain: ...`, then `Source table group:` where relevant, then what it holds and how it is loaded, and ends with a `Use it for ...` sentence.
- Every column of a declared table declared under its source name, including loader columns such as `_fivetran_synced`. Descriptions written inline (no doc blocks): meaning in the source, unit, time zone, null meaning, allowed values. Identifier columns name where the same value is held elsewhere. Personal data columns carry "Personal data.". Profiled figures carry the date measured.
- `freshness` (with `loaded_at_field`) is the only test. `warn_after` and `error_after` are set per client project.

The full template is in `specs/development/dbt_generate.md`, Step 3.

**Also create:** `dbt/models/staging/stg_<source>/_schema.yml` for the staging and base models (not where the project uses droughty, which writes `models/droughty_schema.yml`). An existing project adds entries to its current schema file (for example `stg_<source>.yml`). Every column references a doc block held in `models/field_descriptions.md` (`'{{ doc("<column>") }}'`).

Tests:
- The natural key that identifies a row: `unique` + `not_null`.
- Other columns: `not_null` + `dbt_utils.at_least_one`. `at_least_one` is added alongside `not_null`, never in place of it. Drop `not_null` only where the column can be null, keep `at_least_one`, and note the reason in the summary.
- Test key: `data_tests:` on dbt 1.8 or later, `tests:` before. Find the version from `dbt --version`, `require-dbt-version` in `dbt_project.yml`, or the dbt or adapter version pinned in requirements. A `form_choices: test_key` ruling wins. In a schema file that already uses `tests:`, keep `tests:`. If the version cannot be found, write `tests:`. Never both keys on one resource.

### Step 5: Generate dbt_project.yml (if new project)

New project: create `dbt/dbt_project.yml` and `dbt/packages.yml` from the templates in `specs/development/dbt_generate.md`, Step 8: layer configs under the real project name, `+persist_docs` for relation and columns, staging and integration as views in the `staging` and `integration` schemas, warehouse as tables with `+meta` `required_docs: true` and `required_tests: {"unique": 1, "not_null": 1}`, seeds in `seeds`, snapshots in `snapshots`, and the `dbt_meta_testing` package beside `dbt_utils`. A project that uses droughty sets `required_docs: false`. Also create `dbt/macros/utility/macro__type_date.sql` (defines `ra_type_date()`) and its entry in `dbt/macros/_schema_macros.yml`.

Existing project: do not change `dbt_project.yml` or `packages.yml`. List differences from the templates in the summary as suggestions only. Correcting the project key can change which models build as tables or views.

### Step 5.5: Convention Self-Check

Resolve the convention file: the project's `.wire/conventions/dbt.yml` if present, else the plugin's `conventions/dbt.yml`. Then run:

```bash
# New project
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/staging --new-project

# Existing project (added and changed models only)
python3 <plugin>/scripts/lint_conventions.py --domain dbt \
  --convention <resolved convention> --path <dbt_project_path>/models/staging \
  --changed-from "$(git merge-base HEAD <release branch>)"
```

Fix every `error` finding in the generated models without renaming or moving anything that already existed. List warnings in the summary with a reason.

### Step 6: Create Summary Document

**File:** `.wire/<project_id>/dev/dbt_staging_summary.md`

Include: whether the project is new or existing, the convention file and any `form_choices:` rulings applied, the test key used, staging and base models created with their grain, snapshots, source tables covered, tests configured (and any column where `not_null` was dropped, with the reason), the convention lint result, and, for an existing project, the `dbt_project.yml` / `packages.yml` suggestions.

### Step 7: Update Status

Update `.wire/<project_id>/status.md`:
```
dbt_staging:
  generate: complete
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dbt_staging`
- `artifact_name`: `dbt Staging Summary`
- `file_path`: `.wire/<project_id>/dev/dbt_staging_summary.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Suggest Next Steps

```
## Staging Models Generated

- <count> staging models created in dbt/models/staging/
- Next: /wire:dbt-staging-validate <project_id>
- Then: /wire:dbt-integration-generate <project_id>
```
