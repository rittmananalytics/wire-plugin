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
description: Validate dbt staging models — compile, test, and check naming conventions
argument-hint: <project-folder> [--slice <slice>]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbt Staging Models — Validate

## Purpose

Validate the staging layer: compile all `stg_*` and `base_*` models, run their dbt tests, and check naming conventions.

Scope and severity follow `specs/development/dbt_validate.md` (**Scope and Severity**): carried rules apply to every model, both accepted forms pass, and rules new in 4.1.2 apply to changed models only. A naming finding on a name approved in the data model specification is Accepted, as `dbt_validate.md` Step 2.5 says. Wire never renames or moves an existing model, column, seed, snapshot or schema.

## Prerequisites

- `dbt_staging: generate: complete` in status.md

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and checks the slice's staging models only
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

### Step 1: Read Staging Models

Locate and read all files in `dbt/models/staging/` to understand what was generated. Include base models (`base_<source>__<entity>.sql`) and source files (`_sources.yml` or `_<source>__sources.yml`).

### Step 1.5: Resolve Conventions and the Changed Set

1. Resolve the convention file as in `dbt_validate.md` Step 1.5: `.wire/conventions/dbt.yml` in the project (with any `form_choices:` ruling), else `<plugin>/conventions/dbt.yml`. Read a project prose document (`docs/development_reference_dbt.md` or the older `docs/dbt_coding_conventions.md`) for context if present.
2. Work out the changed set as in `dbt_validate.md` Step 1.6 (`git merge-base` against the release branch's base). Base, snapshot and seed file-naming rules apply to added files only. Without git history, rules new in 4.1.2 report as warnings.
3. Run the convention lint:
   ```bash
   python3 <plugin>/scripts/lint_conventions.py --domain dbt \
     --convention <resolved convention file> \
     --path <dbt project dir>/models/staging \
     --changed-from <base commit> --format json
   ```
   Drop `--changed-from` when git is unavailable. Fold its findings into Step 3 and the report.

### Step 2: Compile Check

Run `dbt compile --select tag:staging` (or equivalent) if dbt is available. Otherwise, perform static analysis:
- All `{{ source() }}` calls are in staging or base models only
- All `{{ ref() }}` calls reference existing models
- Every model has a `final` CTE. Changed models end with `select * from final`

### Step 3: Naming Convention Checks

For every staging model, verify:
- [ ] Filename matches `stg_<source>__<entity>.sql`. The entity may be plural (new form) or singular. Both pass
- [ ] Base model filenames match `base_<source>__<entity>.sql` (added files)
- [ ] File is in `dbt/models/staging/<group>/` (new form: `stg_<source>/`)
- [ ] Key: the natural key, `<entity>_natural_key` (new form, PK and FK are created in the warehouse layer). An older model with `<entity>_pk` generated via `dbt_utils.generate_surrogate_key(...)` passes
- [ ] Dates end in `_dt`; timestamps end in `_ts` (UTC) or `_<tz>_ts` (non-UTC, timezone before `_ts`)
- [ ] Booleans use `is_`, `has_` or `was_`, at the start or after the entity prefix (`user_is_active` or `is_active`)
- [ ] Revenue / money columns use the `_amount` suffix (`_amount_<currency>` for a non-base currency, changed models)
- [ ] Changed models: `_count`, `_rank`, `_<measure>_<unit>`, `_pct` (0 to 100) and `_ratio` (0 to 1) suffixes used where they apply
- [ ] Type casts use `{{ dbt.type_*() }}` macros, and `{{ ra_type_date() }}` or the project's existing date macro (`{{ type_date() }}`), not raw SQL types
- [ ] Source refs use `{{ source() }}` not `{{ ref() }}`
- [ ] Staging reads only sources, base models, snapshots and seeds
- [ ] Changed models: no join or union except within one source system; a CTE that removes rows carries a comment saying why
- [ ] Changed models: attribute strings lowercased. Natural keys and source identifiers are never lowercased. A lowercased natural key is a finding

Advisory only (Nice-to-have, never a failure):
- Entity prefix on every output column (`user_name`; unprefixed `name` passes)
- Field ordering in eight groups with Jinja comments: `{# primary key #}`, `{# foreign keys #}`, `{# natural keys #}`, `{# attributes #}`, `{# indexes and ranks #}`, `{# metrics #}`, `{# booleans #}`, `{# temporal #}`. The older six-group order passes
- Lines up to 120 characters; Jinja delimiters with inner spaces (`{{ this }}`)

### Step 4: Schema File Coverage

- Every staging model has an entry in a schema file: `_schema.yml` (new form), the existing `stg_<source>.yml`, or `droughty_schema.yml`
- Key has `unique` and `not_null` tests. `dbt_utils.at_least_one` is accepted as an addition, never in place of `not_null` on the key
- `data_tests:` and `tests:` both pass. A resource that uses both is a finding
- Changed models: `config()` description opens `Grain: One row per ...`; every column documented, through doc blocks in `models/field_descriptions.md`
- Changed source files: `schema` and `loader` set; each table description opens `Grain:`; every column declared under its source name, loader columns included; personal data marked "Personal data."; `freshness` (with `loaded_at_field`) is the only test

### Step 5: Produce Validation Report

**File:** `.wire/<project_id>/dev/.dbt_staging_validation_report.md`

```markdown
# dbt Staging Models — Validation Report

**Status:** PASS / FAIL
**Date:** <date>

## Models Checked: <count>

**Convention source:** <resolved file>
**Changed set:** <base ref and commit> / unknown (new rules reported as warnings)
**Models in scope for new rules:** <added and modified models>

| Model | Changed | Compile | Naming | Schema file | Status |
|-------|---------|---------|--------|-------------|--------|
| stg_... | added / modified / no | ✓ | ✓ | ✓ | PASS |

## Issues Found
<list any failures>

## Next Steps
- /wire:dbt-integration-generate <project_id>
```

### Step 6: Update Status

```
dbt_staging:
  validate: complete  (or: failed)
```
