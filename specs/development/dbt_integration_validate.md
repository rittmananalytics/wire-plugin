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
description: Validate dbt integration-layer models — compile, test, and check business logic
argument-hint: <project-folder> [--slice <slice>]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Integration Models — Validate

## Purpose

Validate the integration layer: compile all `int_<group>__*` models, verify they only reference staging models or other integration models (no `{{ source() }}`), and check business logic correctness.

Scope and severity follow `specs/development/dbt_validate.md` (**Scope and Severity**): carried rules apply to every model, both accepted forms pass, and rules new in 4.1.2 apply to changed models only. A naming finding on a name approved in the data model specification is Accepted, as `dbt_validate.md` Step 2.5 says. Wire never renames or moves an existing model, column or schema.

## Prerequisites

- `dbt_integration: generate: complete` in status.md

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and checks the slice's integration models only
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

### Step 1: Read Integration Models

List and read all files in `dbt/models/integration/`.

### Step 1.5: Resolve Conventions and the Changed Set

1. Resolve the convention file as in `dbt_validate.md` Step 1.5: `.wire/conventions/dbt.yml` in the project (with any `form_choices:` ruling), else `<plugin>/conventions/dbt.yml`. Read a project prose document (`docs/development_reference_dbt.md` or the older `docs/dbt_coding_conventions.md`) for context if present.
2. Work out the changed set as in `dbt_validate.md` Step 1.6 (`git merge-base` against the release branch's base). Without git history, rules new in 4.1.2 report as warnings.
3. Run the convention lint:
   ```bash
   python3 <plugin>/scripts/lint_conventions.py --domain dbt \
     --convention <resolved convention file> \
     --path <dbt project dir>/models/integration \
     --changed-from <base commit> --format json
   ```
   Drop `--changed-from` when git is unavailable. Fold its findings into Steps 2 and 3 and the report.

### Step 2: Dependency Check

For each `int_<group>__` model verify:
- [ ] No `{{ source() }}` calls, only `{{ ref() }}`
- [ ] All `{{ ref() }}` targets are `stg_*` or `int_<group>__*` models (not warehouse)
- [ ] Changed models: no `{{ ref() }}` to a base model (`base_*`). Later layers read the staging model, not its base models
- [ ] CTEs at top with `s_` prefix for refs
- [ ] `final` CTE exists and is selected from. Changed models end with `select * from final`

### Step 3: Naming Convention Checks

- [ ] Filename matches `int_<group>__<entity>.sql` or `int_<group>__<entity>__<verb>.sql` (verb in past tense). The entity may be plural (new form) or singular. Both pass
- [ ] File is in `dbt/models/integration/int_<group>/` (or `int_<group>/intermediate/`)
- [ ] Intermediate models are materialized as `view` (new form, set by the folder) or `ephemeral`. Both pass
- [ ] Key: the natural key, `<entity>_natural_key` (new form, PK and FK are created in the warehouse layer). An older model with `<entity>_pk` generated via `dbt_utils.generate_surrogate_key(...)` passes
- [ ] Dates end in `_dt`; timestamps end in `_ts` (UTC) or `_<tz>_ts` (non-UTC, timezone before `_ts`)
- [ ] Booleans use `is_`, `has_` or `was_`, at the start or after the entity prefix (`user_is_active` or `is_active`)
- [ ] Revenue / money columns use the `_amount` suffix (`_amount_<currency>` for a non-base currency, changed models)
- [ ] Changed models: `_count`, `_rank`, `_<measure>_<unit>`, `_pct` (0 to 100) and `_ratio` (0 to 1) suffixes used where they apply
- [ ] Type casts use `{{ dbt.type_*() }}` macros, and `{{ ra_type_date() }}` or the project's existing date macro (`{{ type_date() }}`), not raw SQL types

Advisory only (Nice-to-have, never a failure):
- Entity prefix on every output column (`user_name`; unprefixed `name` passes)
- Aggregated columns lead with the function (`sum_invoice_line_item_amount`)
- Field ordering in eight groups with Jinja comments: `{# primary key #}`, `{# foreign keys #}`, `{# natural keys #}`, `{# attributes #}`, `{# indexes and ranks #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal #}`. The older six-group order passes
- Lines up to 120 characters; Jinja delimiters with inner spaces (`{{ this }}`)

### Step 4: Schema File Coverage

- [ ] Each `int_<group>/` directory has a schema file with at least one model entry: `_schema.yml` (new form), the existing `integration.yml` / `intermediate.yml`, or `droughty_schema.yml`
- [ ] Complex transformation models are documented
- [ ] Key has `unique` and `not_null` tests. `dbt_utils.at_least_one` is accepted as an addition, never in place of `not_null` on the key
- [ ] `data_tests:` and `tests:` both pass. A resource that uses both is a finding
- [ ] Changed models (integration and intermediate): `config()` description opens `Grain: One row per ...`; every column documented, through doc blocks in `models/field_descriptions.md`

### Step 5: Produce Validation Report

**File:** `.wire/<project_id>/dev/.dbt_integration_validation_report.md`

```markdown
# dbt Integration Models — Validation Report

**Status:** PASS / FAIL
**Date:** <date>

## Models Checked: <count>

**Convention source:** <resolved file>
**Changed set:** <base ref and commit> / unknown (new rules reported as warnings)
**Models in scope for new rules:** <added and modified models>

| Model | Changed | Compile | No Sources | Naming | Status |
|-------|---------|---------|------------|--------|--------|
| int_core__... | added / modified / no | ✓ | ✓ | ✓ | PASS |

## Issues Found
<list any failures>

## Next Steps
- /wire:dbt-warehouse-generate <project_id>
```

### Step 6: Update Status

```
dbt_integration:
  validate: complete  (or: failed)
```
