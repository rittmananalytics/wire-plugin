---
wire_schema: "1.0"
command: validate
artifact: orchestration
domain: development
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
preconditions:
  - artifact: orchestration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the orchestration layer — checks Dagster asset graph or dbt Cloud job configs against the pipeline design
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Orchestration Validate Command

## Purpose

Validate the generated orchestration layer. The validation checks differ by tool:

- **Dagster**: verifies the asset graph loads cleanly, covers all dbt models, and the schedule cadences match the pipeline design
- **dbt Cloud**: verifies job configurations reference valid environments, selectors match existing dbt models, and schedules reflect the pipeline design cadences

## Prerequisites

- `orchestration` generate must be complete
- For Dagster: `dagster_orchestration/` directory must exist with a valid `Definitions` object

## Workflow

### Step 1: Read Configuration

1. Read `.wire/<project_id>/status.md` to determine `orchestration_tool`
2. If `orchestration_tool` is not set, stop with: "Run `/wire:orchestration-generate <project>` first to set up the orchestration layer."

### Step 2a: Validate Dagster (if tool = dagster)

#### 2a.1 — Check defs load

Run from the `dagster_orchestration/` directory:

```bash
cd dagster_orchestration
dg check defs
```

This verifies:
- All Python imports resolve
- All `@dg.asset` and `@dg.multi_asset` decorators are valid
- The `Definitions` object loads without errors
- No circular asset dependencies
- All referenced resources are defined

If `dg check defs` fails, report the full error and stop.

#### 2a.2 — Verify dbt model coverage

Run:
```bash
cd dagster_orchestration
dg list defs --select "kind:dbt"
```

Compare the listed dbt-kind assets against the models in the dbt project (`dbt ls --select "*" --output name`). Every dbt model should have a corresponding Dagster asset.

Report any missing models as validation findings.

#### 2a.3 — Verify schedule cadences

List all defined schedules:
```bash
dg list defs --select "type:schedule"
```

For each schedule, verify:
- The cron expression is valid (parseable)
- It matches a run cadence specified in `pipeline_design.md`
- It targets at least one asset or job

Report any cadences in the pipeline design that have no corresponding schedule.

#### 2a.4 — Check asset group completeness

Verify that every source system in `pipeline_design.md` has at least one ingestion asset defined in `assets/`.

#### 2a.5 — Compile validation report

Write `.wire/<project_id>/development/orchestration/.orchestration_validation.md`:

```markdown
# Orchestration Validation Report

**Date**: <date>
**Tool**: Dagster
**Result**: PASS | FAIL

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| dg check defs | PASS/FAIL | [error if failed] |
| dbt model coverage | PASS/FAIL | [N of M models covered] |
| Schedule cadence coverage | PASS/FAIL | [missing cadences if any] |
| Source ingestion coverage | PASS/FAIL | [missing sources if any] |

## Findings

[List any warnings or required fixes]
```

### Step 2b: Validate dbt Cloud (if tool = dbt_cloud)

#### 2b.1 — Check config file completeness

Read `.wire/<project_id>/development/orchestration/dbt_cloud_config.md` and verify it contains:
- At least one Production environment definition
- At least one job per run cadence identified in `pipeline_design.md`
- A CI/PR job for pull request validation
- Notification configuration on each job

#### 2b.2 — Verify model selectors

For each job, verify the `dbt run --select <selector>` expression is valid by running:

```bash
dbt ls --select <selector>
```

If the selector returns 0 models, flag as a warning. If the command errors, flag as a failure.

#### 2b.3 — Verify cron expressions

For each scheduled job, confirm the cron expression is syntactically valid and matches the stated cadence description.

#### 2b.4 — Compile validation report

Write `.wire/<project_id>/development/orchestration/.orchestration_validation.md`:

```markdown
# Orchestration Validation Report

**Date**: <date>
**Tool**: dbt Cloud
**Result**: PASS | FAIL

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| Config file completeness | PASS/FAIL | |
| Model selectors valid | PASS/FAIL | [any selectors matching 0 models] |
| Cron expressions valid | PASS/FAIL | |
| Cadence coverage | PASS/FAIL | [cadences from pipeline_design not covered] |

## Findings

[List any warnings or required fixes]
```

### Step 2c: Validate Airflow (if tool = airflow)

**Existing Airflow estate mode** (`orchestration_mode: existing_airflow_estate`): run the two local checks of `wire/specs/development/pipeline/airflow/validate.md` (rule lint on the changed files, and a `DagBag` parse in safe mode of each changed DAG file) in place of 2c.1 to 2c.3, then 2c.4 on each changed schedule and 2c.6. Skip 2c.5 unless the change added a connection. No live Airflow call is made; whether the change ran in dev is answered by `/wire:utils-dev-test-evidence`.

#### 2c.1 — DAG parse check

Run from the repo root:

```bash
python -c "from dags.<project_name>_pipeline import dag; print('DAG tasks:', dag.task_ids)"
```

If the import raises any error, report it in full and stop. A clean parse is a hard requirement before proceeding.

#### 2c.2 — Verify dbt model task coverage

List dbt models:
```bash
cd <dbt_project_path> && dbt ls --select "*" --output name
```

Inspect the DAG file and confirm every model has either:
- A corresponding `BashOperator` or `PythonOperator` task running `dbt run --select <model>`, or
- Is covered by a `DbtTaskGroup` that runs all models

Report any models not covered as validation findings.

#### 2c.3 — Verify source sensor coverage

Read `pipeline_design.md` source system list. Confirm there is at least one sensor task per source (e.g. `BigQueryTableExistenceSensor`, `HttpSensor`, or equivalent). Report any source systems with no upstream sensor.

#### 2c.4 — Verify cron expression

Extract the `schedule_interval` from the DAG file. Confirm:
- The cron expression is syntactically valid (parseable by a standard cron library)
- It matches the run cadence stated in `pipeline_design.md`

#### 2c.5 — Verify connection IDs documented

Check that `airflow_connections.md` exists and lists at least one connection per source system and one for the warehouse target.

#### 2c.6 — Compile validation report

Write `.wire/<project_id>/development/orchestration/.orchestration_validation.md`:

```markdown
# Orchestration Validation Report

**Date**: <date>
**Tool**: Airflow
**Result**: PASS | FAIL

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| DAG parse check | PASS/FAIL | [error if failed] |
| dbt model task coverage | PASS/FAIL | [N of M models covered] |
| Source sensor coverage | PASS/FAIL | [missing sources if any] |
| Cron expression valid | PASS/FAIL | [expression and matched cadence] |
| Connection IDs documented | PASS/FAIL | |

## Findings

[List any warnings or required fixes]
```

### Step 3: Update Status

Update `.wire/<project_id>/status.md`:

```yaml
orchestration:
  validate: complete   # or failed
```

If any FAIL check was found, set `validate: failed` and include findings in the notes.

### Step 4: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `orchestration`
- Action: `validate`
- Status: `complete` or `failed`

### Step 5: Report Results

If PASS:
```
## Orchestration Validation: PASS

All checks passed. Ready for review.

Next step: `/wire:orchestration-review <project>`
```

If FAIL:
```
## Orchestration Validation: FAIL

[List failing checks and required fixes]

Fix the issues above and re-run: `/wire:orchestration-validate <project>`
```
