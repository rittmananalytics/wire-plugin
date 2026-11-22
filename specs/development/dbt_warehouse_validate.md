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
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Validate dbt warehouse models — compile, test referential integrity, and check dimensional conventions (_dim/_fact/_agg/_xa)
argument-hint: <project-folder> [--slice <slice>]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Warehouse Models — Validate

## Purpose

Validate the warehouse layer: compile all `_dim`/`_fact`/`_xa`/`_agg` models, verify referential integrity (FK → dim PK), check materialization settings, and ensure full schema documentation coverage.

Scope and severity follow `specs/development/dbt_validate.md` (**Scope and Severity**): carried rules apply to every model, both accepted forms pass, and rules new in 4.1.2 apply to changed models only. A naming finding on a name approved in the data model specification is Accepted, as `dbt_validate.md` Step 2.5 says. Wire never renames or moves an existing model, column or schema.

## Prerequisites

- `dbt_warehouse: generate: complete` in status.md

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and checks the slice's warehouse models only
(`specs/utils/ticket_delivery.md`, "The `--slice` option"). Without
`--slice`, the workflow below runs as written.

1. The slice must be in `tickets.yaml`. If it is not, stop and list the valid
   slices.
2. Run every check below against the slice's part. A check that needs the
   whole release (a cross-model consistency check) runs against the slice and
   the parts it depends on, and says so in the report.
3. On a ticket branch, write the result (`pass` or `fail`) to the ticket
   record's front matter (`results:`) and the log row to the ticket run log
   (`iterations/<ticket>.execution_log.md`), not to `status.md` and
   `execution_log.md`.

## Workflow

### Step 1: Read Warehouse Models

List and read all files in `dbt/models/warehouse/`.

### Step 1.5: Resolve Conventions and the Changed Set

1. Resolve the convention file as in `dbt_validate.md` Step 1.5: `.wire/conventions/dbt.yml` in the project (with any `form_choices:` ruling), else `<plugin>/conventions/dbt.yml`. Read a project prose document (`docs/development_reference_dbt.md` or the older `docs/dbt_coding_conventions.md`) for context if present.
2. Work out the changed set as in `dbt_validate.md` Step 1.6 (`git merge-base` against the release branch's base). Without git history, rules new in 4.1.2 report as warnings.
3. Run the convention lint:
   ```bash
   python3 <plugin>/scripts/lint_conventions.py --domain dbt \
     --convention <resolved convention file> \
     --path <dbt project dir>/models/warehouse \
     --changed-from <base commit> --format json
   ```
   Drop `--changed-from` when git is unavailable. Fold its findings into Steps 2 to 5 and the report.

### Step 2: Dependency Check

For each warehouse model verify:
- [ ] Only `{{ ref() }}` calls, no `{{ source() }}`
- [ ] Dimensions and facts reference `int_<group>__*` models, or `stg_*` models where no integration model is needed
- [ ] Facts may also reference `_dim` models
- [ ] Changed models: no `{{ ref() }}` to a base model (`base_*`)
- [ ] Extended aggregate (`_xa`) models reference `_fact` and `_dim` models (an `int_*` reference passes, but may mean a dimension or fact is missing). Existing `_xa` models built as bridge or cross-attribute tables pass
- [ ] No circular dependencies

### Step 3: Naming Convention Checks

- [ ] Dimension files match `wh_<group>__<entity>_dim.sql`
- [ ] Fact files match `wh_<group>__<entity>_fact.sql` (note: `_fact`, not `_fct`)
- [ ] Extended aggregate files match `wh_<group>__<entity>_xa.sql`. An extended aggregate is a denormalised table built from fact and dimension models, either aggregated to a summary grain or combining several facts at a shared grain
- [ ] Existing aggregate files match `wh_<group>__<entity>_agg.sql`. `_agg` is accepted beside `_dim`/`_fact`/`_xa`; new models use `_xa`
- [ ] Warehouse entity names are singular (`wh_core__user_dim`)
- [ ] Primary keys named `<entity>_pk`, generated via `dbt_utils.generate_surrogate_key(...)`
- [ ] Foreign keys named `<referenced_entity>_fk`, generated via `dbt_utils.generate_surrogate_key(...)`
- [ ] Dates end in `_dt`; timestamps end in `_ts` (UTC) or `_<tz>_ts` (non-UTC, timezone before `_ts`)
- [ ] Booleans use `is_`, `has_` or `was_`, at the start or after the entity prefix (`user_is_active` or `is_active`)
- [ ] Revenue / money columns use the `_amount` suffix (`_amount_<currency>` for a non-base currency, changed models)
- [ ] Changed models: `_count`, `_rank`, `_<measure>_<unit>`, `_pct` (0 to 100) and `_ratio` (0 to 1) suffixes used where they apply
- [ ] Type casts use `{{ dbt.type_*() }}` macros, and `{{ ra_type_date() }}` or the project's existing date macro (`{{ type_date() }}`), not raw SQL types
- [ ] Materialized as `table`, or `incremental` where the client chose it for that model
- [ ] Changed models: the last CTE is `final` and the model ends with `select * from final`

Advisory only (Nice-to-have, never a failure):
- Entity prefix on every output column (`user_name`; unprefixed `name` passes)
- Aggregated columns lead with the function (`sum_invoice_line_item_amount`)
- Field ordering in eight groups with Jinja comments: `{# primary key #}`, `{# foreign keys #}`, `{# natural keys #}`, `{# attributes #}`, `{# indexes and ranks #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal #}`. The older six-group order passes
- Lines up to 120 characters; Jinja delimiters with inner spaces (`{{ this }}`)

### Step 4: Referential Integrity

For each `_fk` in fact tables, verify a corresponding `relationships` test exists in the schema file pointing to the correct `_dim`.

### Step 5: Schema File Coverage

- [ ] Every `_dim`, `_fact`, `_xa` and `_agg` model has an entry in a schema file: `_schema.yml` (new form), the existing `wh_<group>.yml`, or `droughty_schema.yml` (100% documentation required)
- [ ] Primary keys have `unique` + `not_null` tests. `dbt_utils.at_least_one` is accepted as an addition, never in place of `not_null` on a primary key
- [ ] Foreign keys have `relationships` tests where applicable
- [ ] `data_tests:` and `tests:` both pass. A resource that uses both is a finding
- [ ] Changed models: `config()` description opens `Grain: One row per ...`; column descriptions held as doc blocks in `models/field_descriptions.md`
- [ ] Where `packages.yml` includes `dbt_meta_testing`: run `dbt run-operation required_tests` and `dbt run-operation required_docs` and record the results. Skip `required_docs` where the project uses droughty (it sets `required_docs: false`)

### Step 6: Produce Validation Report

**File:** `.wire/<project_id>/dev/.dbt_warehouse_validation_report.md`

```markdown
# dbt Warehouse Models — Validation Report

**Status:** PASS / FAIL
**Date:** <date>

## Models Checked: <count>

**Convention source:** <resolved file>
**Changed set:** <base ref and commit> / unknown (new rules reported as warnings)
**Models in scope for new rules:** <added and modified models>
**dbt_meta_testing:** required_tests <result>, required_docs <result / skipped: droughty / not installed>

| Model | Type | Changed | Compile | FK Tests | Docs | Status |
|-------|------|---------|---------|----------|------|--------|
| wh_core__customer_dim | dimension | no | ✓ | ✓ | ✓ | PASS |
| wh_sales__order_fact | fact | modified | ✓ | ✓ | ✓ | PASS |

## Issues Found
<list any failures>

## Next Steps
- /wire:semantic_layer-generate <project_id>
```

### Step 7: Update Status

```
dbt_warehouse:
  validate: complete  (or: failed)
```
