---
wire_schema: "1.0"
command: validate
artifact: orchestration_audit
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
  - artifact: orchestration_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate orchestration audit completeness

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Orchestration Audit — Validate

## Validation Checks

**Check 1 — All jobs classified**
Every job has a `migration_approach` value.
PASS/FAIL with gap list.

**Check 2 — All jobs have criticality assigned**
Every job has a `criticality` value (critical / standard / low).
PASS/FAIL.

**Check 3 — Scheduled jobs have cron expressions**
Every job of type `scheduled` has the cron expression or schedule interval recorded.
PASS/FAIL with gaps.

**Check 4 — Connections and credentials inventoried**
The audit includes a list of connection names used by jobs (even if credential values are not stored).
PASS: Connection inventory present.
FAIL: No connection inventory found.

**Check 5 — Evaluate jobs have notes**
Every job with `migration_approach: evaluate` has a note.
PASS/FAIL.

**Check 6 — Dependency graph is acyclic**
For tools that support DAG structures (Airflow, Dagster), the captured dependency graph has no cycles.
PASS: No cycles detected.
FAIL: Report cyclic dependencies.

### Update status

```yaml
artifacts:
  orchestration_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_audit` as artifact_id, `Orchestration Audit` as artifact_name, and the `file` value from `artifacts.orchestration_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `orchestration_audit` as artifact, `validate` as action.
