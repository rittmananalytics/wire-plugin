---
wire_schema: "1.0"
command: validate
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
  - artifact: orchestration_migration
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate orchestration migration runbook
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Orchestration Migration — Validate

## Flags

- `--wave <id>` — validate the wave-labelled runbook (`orchestration_migration_runbook_{wave_id}.md`) against the jobs `migration/migration_batching.csv` assigns to this wave, resolved identically to `orchestration-migration-generate`'s Step 1w. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). Every check below reads "in scope" as this resolved job set instead of every `recreate`/`translate` job.

## Validation Checks

**Check 1 — All recreate/translate jobs in runbook**
Every in-scope job with `migration_approach: recreate` or `translate` appears in the runbook.
PASS/FAIL.

**Check 2 — Connection changes documented**
Every job that uses a platform-specific connection has the connection update documented.
PASS/FAIL.

**Check 3 — Parallel-run plan present**
The runbook includes a parallel-run section.
PASS/FAIL.

**Check 4 — Job cutover deferred to cutover phase**
The runbook explicitly notes that source jobs are NOT paused during orchestration migration — only during cutover.
PASS/FAIL.

**Check 5 — Critical jobs have fallback procedures**
Every job with `criticality: critical` has a fallback procedure in the runbook.
PASS/FAIL.

### Update status

```yaml
artifacts:
  orchestration_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    wave_validate:               # set only when run with --wave, keyed by wave id
      B01: pass | fail
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_migration` as artifact_id, `Orchestration Migration` as artifact_name, and the `file` value from `artifacts.orchestration_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `orchestration_migration` as artifact, `validate` as action.
