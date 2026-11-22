---
wire_schema: "1.0"
command: validate
artifact: migration_drift
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: migration_drift
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the migration drift report — every drifted model classified, downstream syncs and masking changes surfaced, register updated

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Drift — Validate

## Validation Checks

Read `migration/migration_drift_report.md`, `migration/migration_register.csv`, and `audit/lineage/model_sync_map.json`.

**Check 1 — Drift head recorded**
The report records `drift_head` (the live source commit diffed against) and the run timestamp.
PASS/FAIL.

**Check 2 — Every migrated model classified**
Every `state = migrated`/`drifted`/`removed` model in the register appears in the report's per-model diff with a classification (modified / removed / new / unchanged).
PASS/FAIL with unclassified models.

**Check 3 — Register reflects the drift**
Models classified modified are `state = drifted` in the register; removed are `state = removed`; new models have a `pending` row. No drift finding is left only in the report.
PASS/FAIL.

**Check 4 — Downstream syncs flagged**
Every modified/removed model with downstream syncs in `model_sync_map.json` has those syncs flagged in the report, each with a config diff.
PASS/FAIL with models whose downstream syncs were not flagged.

**Check 5 — Masking changes trigger the policy-tag hook**
Every model whose source `meta.masking_policy` changed is listed as a masking change with a required `target-setup` policy-tag regeneration action.
PASS: all masking changes have an action (or none changed). FAIL: a masking change with no regeneration action.

**Check 6 — Stale NULL-pads flagged for restore, never auto-rewritten**
Every model carrying a `-- MARKET GAP:` NULL-pad whose named source column is now present in the live source (Step 5b, pair rule `STALE_NULL_PAD_BRONZE_PRESENT`) is listed in the report as a flag-for-restore finding (model, column, now-present market(s), synthesized type) and its register row is `state = drifted`. Confirm none was silently auto-rewritten in the translated SQL — the NULL-pad must still be present with its marker until a re-translation restores it.
PASS: every now-present MARKET GAP column is flagged for restore and none auto-rewritten (or none apply). FAIL: a now-present MARKET GAP column not flagged, or one rewritten in place without a recorded restore decision.

### Update status

```yaml
artifacts:
  migration_drift:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact_id, `Migration Drift` as artifact_name, and the `file` value from `artifacts.migration_drift` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_drift` as artifact, `validate` as action.
