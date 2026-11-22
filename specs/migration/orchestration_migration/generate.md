---
wire_schema: "1.0"
command: generate
artifact: orchestration_migration
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: dbt_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate orchestration job migration runbook
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: orchestration_migration` and `artifact_file_path: migration/orchestration_migration_runbook.md` before proceeding.

---

# Orchestration Migration — Generate

## Purpose

Generates a runbook for recreating all in-scope orchestration jobs on the target platform configuration. Covers connection profile updates, job reconfiguration, and the parallel-run period where both source and target orchestration run simultaneously.

## Prerequisites

- Without `--wave`: all dbt migration batches reviewed and approved
- With `--wave <id>`: only that wave's dbt models reviewed and approved (`dbt_migration.waves_complete` includes the wave) — a job that depends on a model outside this wave is not yet migratable and is deferred, not included
- `orchestration_audit review: approved`
- `migration/migration_batching.csv` exists — required only when running with `--wave`

## Flags

- `--wave <id>` — restrict this run to the orchestration jobs `migration/migration_batching.csv` assigns to this wave. Resolution is identical to `dbt-migration-generate`'s Step 1w: normalise the wave id, load `migration_batching. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative).csv` (abort if missing), filter to rows where `batch_id` matches **and** `object_type == "job"`, then cross-reference each matched `object_id` against `orchestration_audit.md`'s job identifiers for the full per-job detail. Print the mandatory resolved-job preview before proceeding. If rows match the wave but none are `job` rows, print `[wire] Wave <id> has no orchestration job objects — nothing to migrate for this command.` and stop cleanly.
- No flag — process every job with `migration_approach` in (`recreate`, `translate`) (today's behaviour, unchanged) — requires every dbt batch approved, since an unscoped runbook can reference any model.

When `--wave` is supplied, the runbook is wave-labelled (`migration/orchestration_migration_runbook_{wave_id}.md`) and status.md tracks the wave under `wave` / `waves_complete`.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/orchestration_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — consumed only by `--wave` mode

## Workflow

### Step 1: Confirm prerequisites

Without `--wave`: confirm all dbt batches are approved (check `dbt_migration.batches_complete` covers all batches in status.md). With `--wave <id>`: confirm `dbt_migration.waves_complete` includes `<id>` in status.md — only this wave's models need to be on target, not the whole estate.

### Step 1w: Resolve `--wave` (only when `--wave` is used)

Resolve the in-scope job set per the **Flags** section above. This replaces "every job in the orchestration audit with `migration_approach` in (`recreate`, `translate`)" in Step 2 with the wave-resolved subset.

### Step 2: Generate per-job migration steps

For each job in scope (Step 1w's resolved set under `--wave`, otherwise every job in the orchestration audit with `migration_approach` in (`recreate`, `translate`)):

**If Dagster**:
- Update asset/op definitions to use target warehouse connection resource
- Update partition definitions if partition scheme changes between platforms
- Update schedule definitions
- Document config changes needed

**If dbt Cloud**:
- Document new environment creation on target platform connection
- Per job: copy job configuration, update environment reference, update target profile
- Document API trigger changes

**If Airflow**:
- Document connection creation for target platform
- Per DAG: document operator parameter changes (connection_id, etc.)
- Document variable updates

### Step 3: Generate parallel-run plan

Document the parallel-run period:
- Source jobs continue to run unchanged
- New target jobs are created but set to manual trigger initially
- After first successful target run, compare output to source run output
- Once target runs consistently pass equivalency checks, schedule can be activated

### Step 4: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/orchestration_migration_runbook.md` — or `migration/orchestration_migration_runbook_{wave_id}.md` when run with `--wave`.

Include:
- Pre-flight checklist
- Per-job migration steps
- Connection configuration changes
- Parallel-run plan
- Job cutover procedure (set target jobs to scheduled, pause source jobs — deferred to cutover phase)

### Step 5: Update status

```yaml
artifacts:
  orchestration_migration:
    generate: complete
    file: migration/orchestration_migration_runbook.md
    generated_date: "{{TODAY}}"
    jobs_in_runbook: N
    wave: "B01"                  # set only when run with --wave; the wave id just processed
    waves_complete: ["B01"]      # set only when run with --wave; accumulates across runs
```

### Step 6: Output next command

```
/wire:orchestration-migration-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_migration` as artifact_id, `Orchestration Migration` as artifact_name, and the `file` value from `artifacts.orchestration_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `orchestration_migration` as artifact, `generate` as action.
