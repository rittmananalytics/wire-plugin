---
wire_schema: "1.0"
command: validate
artifact: migration_report
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
  - artifact: migration_report
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate migration report completeness

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Report — Validate

## Validation Checks

Checks 1–6 validate the default post-migration report. Checks 7–10 apply **only when the defect-provenance lens was generated** (`migration/migration_report_defects.md` exists, from `migration-report-generate --lens defects`); skip them otherwise. The two report modes are validated independently — a defects report is never required for the default report to pass, and vice versa.

**Check 1 — Object counts reconcile**
The total migrated objects in the report match the migration inventory scope.
PASS/FAIL.

**Check 2 — Equivalency section present**
The report includes the final equivalency state and accepted differences table.
PASS/FAIL.

**Check 3 — Lessons learned present**
The report includes a lessons learned section with at least 3 items.
PASS/FAIL.

**Check 4 — Source decommission plan present**
The report includes a source platform decommission plan with a recommended timeline.
PASS/FAIL.

**Check 5 — Effort comparison present**
The report compares estimated vs actual effort.
PASS/FAIL.

**Check 6 — Migration status: complete**
`status.md` has `migration.status: complete`.
PASS/FAIL.

**Check 7 — Stage-of-capture breakdown present and earliest-gate attributed** (defects lens only)
Each wave has a stage-of-capture table over the pipeline order (`generate_inline`, `lint`, `validate`, `equivalency`, `pre_pr_review`), broken down by pattern id / defect class. Each defect is counted once — at the earliest gate that caught it — so no defect is double-counted across gates, and the per-wave total equals the count of distinct defects.
PASS/FAIL.

**Check 8 — Auto-fixed vs escalated split present** (defects lens only)
Each wave reports the `dbt-migration-fix` split (auto-fixed, escalated-propose, escalated-decision).
PASS/FAIL.

**Check 9 — Client-caught leakage explicit** (defects lens only)
Each wave states a client-caught figure that is either an integer (from the `--client-caught` input) or "not tracked" — never a silent 0 standing in for an untracked wave.
PASS/FAIL.

**Check 10 — Wave-over-wave trend present** (defects lens only)
The report includes the wave-ordered trend rollup across the covered waves, and any pattern reaching the client in ≥2 waves is surfaced as a rule candidate (flagged for human review, not auto-actioned).
PASS/FAIL.

### Update status

```yaml
artifacts:
  migration_report:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_report` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_report` as artifact_id, `Migration Report` as artifact_name, and the `file` value from `artifacts.migration_report` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_report` as artifact, `validate` as action.
