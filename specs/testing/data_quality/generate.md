---
wire_schema: "1.0"
command: generate
artifact: data_quality
domain: testing
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
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
description: Generate data quality from design and requirements
argument-hint: <project-folder> [--slice <slice>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# data quality Generate Command

Follow `specs/utils/data_quality_engineer_delegate.md` before executing the workflow below.

## Purpose

Generate a data quality test plan for the release: confirm the baseline dbt schema-test coverage required by `wire/skills/dbt-development/testing-reference.md` is in place for every model, then propose supplemental statistical and distributional tests (using the `dbt_expectations` package) for business-critical models where uniqueness/not-null/relationships tests alone aren't enough to catch a bad refresh — a KPI silently going to zero, a distribution drifting, a date range with a gap.

## Usage

```bash
/wire:data_quality-generate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must be approved
- `dbt.generate` should be complete (this command reads the actual dbt project's models and `schema.yml` files — see Edge Cases if dbt isn't generated yet)

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and reads and writes the tests for the slice's tables only
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

### Step 1: Read Inputs

**Process**:
1. Read `requirements/requirements_specification.md` — extract any named KPIs, metrics, or data quality expectations (e.g. "revenue should never be negative", "daily active users refreshed every day with no gaps")
2. Read `design/data_model.md` — expected entities, relationships, and grain
3. Read the dbt project's models and existing `schema.yml` files (`dbt/models/staging/`, `dbt/models/integration/`, `dbt/models/warehouse/`)
4. Read `dbt/packages.yml` (or equivalent) to check what test packages are already installed

### Step 2: Apply Baseline Test Coverage

Apply the minimum testing requirements from `wire/skills/dbt-development/testing-reference.md` as the floor for every model — this step never invents new test types, it only confirms the baseline is actually present:

| Layer | Primary key tests | Other required tests |
|-------|-------------------|----------------------|
| Staging | `unique` + `not_null` | `accepted_values` on enum/status fields |
| Integration | `unique` + `not_null` (or `dbt_utils.unique_combination_of_columns` for multi-source models) | `relationships` on foreign keys |
| Warehouse | `unique` + `not_null` | `relationships` on foreign keys, `accepted_values` on enum/status fields |

For every model missing baseline coverage, record it as a gap in the output document (Step 5) rather than silently fixing `schema.yml` — schema changes belong to `/wire:dbt-generate`/`/wire:dbt-validate`, not this command.

### Step 2.5: Confirm Unit Test Coverage

Unit tests are a distinct category from the schema tests in Step 2 and the dbt_expectations tests in Step 3 — they validate **transformation logic in isolation** (mock inputs → expected outputs), not production data quality. See `wire/skills/dbt-unit-testing/SKILL.md` for the Model-Inputs-Outputs pattern and format guidance.

Which models need a unit test is set by the "Unit test rule" section of `wire/skills/dbt-development/testing-reference.md`. That section is the only statement of the rule, the business logic signals and the outcome per model. Do not restate or change the rule here.

Scan every model in the dbt project, in every layer:

1. Find the model's layer from its name prefix, else its folder, as the rule says. A model in no recognised layer is listed as **Classify by hand**.
2. Read the model's SQL (compiled SQL where `target/compiled/` exists, else the model file) with comments removed, and record each business logic signal it shows.
3. Record whether the model has a `unit_tests:` block (in any YAML file in the project that names it as `model:`).
4. Apply the rule's outcome table. List every model whose outcome is Required, Recommended, Check by hand or Classify by hand and that has no `unit_tests:` block, in the Unit Test Coverage Gaps table (Step 5), with its layer, the signals found and the gap type:
   - **Required**: integration and warehouse models with business logic. These must be resolved or tracked before `/wire:data_quality-validate` passes.
   - **Advisory**: staging models with non-trivial logic. Reported, never blocking.
   - **Check by hand** and **Classify by hand**: the consultant decides and records the decision in the Notes column.

This command documents gaps; it does not write unit tests (that is a dbt-development task).

### Step 3: Propose Supplemental dbt-expectations Tests

For models that are **business-critical** — referenced by a named KPI/metric in `requirements/requirements_specification.md`, or a warehouse-layer fact table — baseline schema tests don't catch a bad refresh where the data is technically valid (unique, not null, in range) but wrong (a KPI collapsed to near-zero, a distribution shifted, a day's data never arrived). Propose tests from the [`dbt_expectations`](https://github.com/calogica/dbt-expectations) package, modeled on Great Expectations, to cover that gap:

| Category | Test | Use it for |
|----------|------|-------------|
| Table shape | `dbt_expectations.expect_table_row_count_to_be_between` | Sanity-check that a model's row count didn't collapse or explode between runs |
| Aggregate | `dbt_expectations.expect_column_mean_to_be_between` / `expect_column_sum_to_be_between` | KPI value sanity ranges (e.g. daily revenue sum stays within a plausible band) |
| Distributional | `dbt_expectations.expect_column_values_to_be_within_n_stdevs` | Anomaly detection on numeric KPI columns — flags a value that's statistically implausible even if in-range |
| Distributional | `dbt_expectations.expect_row_values_to_have_data_for_every_n_datepart` | Catches missing days/weeks in a time series — a silent gap that `not_null` tests can't see |
| Sets/ranges | `dbt_expectations.expect_column_values_to_be_between` | Numeric bounds beyond what a single `accepted_values` list can express (e.g. percentages must be 0–100) |
| String matching | `dbt_expectations.expect_column_values_to_match_regex` | Format validation on IDs, emails, or other structured string fields |

Only propose a supplemental test where there's a concrete signal to justify it (a named KPI, a known time-series grain, a documented format) — don't add statistical tests to every column indiscriminately. For each proposed test, record: model, column, test, package, purpose, and severity (`error` for KPIs named directly in requirements, `warn` for exploratory/nice-to-have checks — matching `testing-reference.md`'s severity conventions).

### Step 4: Check Package Prerequisites

If any test proposed in Step 3 uses `dbt_expectations` and the package isn't already declared in `dbt/packages.yml`:

```yaml
packages:
  - package: calogica/dbt_expectations
    version: [">=0.10.0", "<0.11.0"]
```

Record this as a setup prerequisite in the output document — this command documents the requirement, it does not run `dbt deps` or edit `packages.yml` itself (that's a dbt-development task, done via `/wire:dbt-generate` or directly by the data team).

### Step 5: Generate Data Quality Test Plan

**File**: `.wire/releases/[release_folder]/test/data_quality.md`

```markdown
# Data Quality Test Plan: [Project Name]

**Generated**: [Date]
**dbt_expectations package required**: Yes | No
**dbt_expectations already installed**: Yes | No | N/A

## Baseline Coverage Gaps

Models missing required tests per `wire/skills/dbt-development/testing-reference.md` (to be fixed via `/wire:dbt-generate`/`/wire:dbt-validate`, not this document):

| Model | Layer | Missing Test | Required Test |
|-------|-------|---------------|----------------|
| [model_name] | staging | Primary key `unique` | `unique` |

*(Empty table means baseline coverage is already complete.)*

## Baseline Test Coverage (confirmed present)

| Model | Layer | Column | Test | Package | Severity |
|-------|-------|--------|------|---------|----------|
| [model]_pk | staging | [model]_pk | unique, not_null | dbt (native) | error |

## Unit Test Coverage Gaps

Models in any layer that lack a `unit_tests:` block where the unit test rule in `wire/skills/dbt-development/testing-reference.md` gives a gap:

| Model | Layer | Signals found | Gap | Notes |
|-------|-------|---------------|-----|-------|
| [int_group__entities] | integration | deduplication, window | Required | |
| [wh_group__entity_fact] | warehouse | conditional_aggregation, rule_join | Required | |
| [stg_source__entities] | staging | parsing | Advisory | |
| [wh_group__entity_dim] | warehouse | (none; plain aggregation) | Check by hand | [consultant decision] |

*(Empty table means no model the rule covers is missing a unit test.)*

## Supplemental dbt-expectations Tests (proposed)

| Model | Column | Test | Package | Purpose | Severity |
|-------|--------|------|---------|---------|----------|
| [kpi_fact] | [amount_column] | expect_column_values_to_be_within_n_stdevs | dbt_expectations | Anomaly detection on [KPI name] from requirements | warn |
| [kpi_fact] | [date_column] | expect_row_values_to_have_data_for_every_n_datepart | dbt_expectations | No missing days in daily-refreshed [KPI name] | error |

## Setup Prerequisites

- [ ] `dbt_expectations` package added to `packages.yml` and `dbt deps` run (only if any supplemental test above uses it)

## Next Steps

Apply the tests above to the corresponding `schema.yml` files, then run `dbt test` before validating this artifact.
```

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.data_quality section:
   ```yaml
   data_quality:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: 2026-02-13
     tests_count: [baseline tests confirmed + supplemental tests proposed]
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_quality`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `data_quality`
- `artifact_name`: `Data Quality Tests`
- `file_path`: `.wire/releases/[release_folder]/test/data_quality.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

**Output**:
```
## Data Quality Test Plan Generated Successfully

**Baseline coverage gaps found**: [N]
**Unit test coverage gaps found**: [N] required, [N] advisory, [N] check or classify by hand
**Supplemental dbt-expectations tests proposed**: [N]
**dbt_expectations package required**: Yes | No

**File(s):** .wire/releases/[release_folder]/test/data_quality.md

### Next Steps

1. **Apply baseline coverage gaps** (if any) via `/wire:dbt-generate <project>`
2. **Add unit tests** for every Required gap (rule: `wire/skills/dbt-development/testing-reference.md`; how to write them: `wire/skills/dbt-unit-testing/SKILL.md`)
3. **Add proposed schema.yml test entries** for the supplemental tests above
4. **Validate data quality**: `/wire:data_quality-validate <project>`
5. After validation, review: `/wire:data_quality-review <project>`
```

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### dbt Not Yet Generated

If `dbt.generate != complete`:
```
dbt models haven't been generated yet, so this command can't read real schema.yml files or model structure.

You can still generate a test plan from requirements alone (KPIs and expected grain), but baseline coverage confirmation (Step 2) will be skipped and re-run once /wire:dbt-generate completes.

Proceed with a requirements-only test plan? (y/n)
```

### No KPIs or Quality Expectations Named in Requirements

If `requirements_specification.md` names no specific KPIs or quality expectations:
```
No specific KPIs or data quality expectations found in requirements.

Generating baseline test coverage confirmation only (Step 2) — no supplemental dbt_expectations tests proposed, since there's no concrete signal (named KPI, stated grain, documented format) to justify one.

If there are quality expectations that should be added to requirements, note them now:
```

## Output

This command creates:
- `.wire/releases/[release_folder]/test/data_quality.md` — baseline coverage confirmation, gaps, and proposed supplemental dbt_expectations tests
- Updates `status.md`
