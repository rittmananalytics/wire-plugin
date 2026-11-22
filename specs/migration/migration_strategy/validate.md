---
wire_schema: "1.0"
command: validate
artifact: migration_strategy
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
  - artifact: migration_strategy
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate migration strategy completeness

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Strategy — Validate

## Validation Checks

**Check 1 — All platform-specific features have translation approaches**
Every feature tag appearing in the dbt and db_object audits has a corresponding translation pattern in the strategy.
PASS: All features covered.
FAIL: List uncovered features.

**Check 2 — All phases have rollback procedures**
Every migration phase in the strategy has a documented rollback procedure.
PASS: All phases have rollback.
FAIL: List phases without rollback.

**Check 3 — Equivalency criteria defined for all in-scope tables**
The strategy defines equivalency checks for every table flagged `include_in_migration: true` in the inventory.
PASS: All in-scope tables have criteria.
FAIL: Report how many are missing criteria.

**Check 4 — Data type mapping covers all source types**
Every distinct data type found in the db_object audit appears in the type mapping section.
PASS: All types mapped.
FAIL: List unmapped types.

**Check 5 — Risk register present**
The strategy includes a risk register with at least 3 risks, each having likelihood, impact, and mitigation.
PASS: Risk register present and populated.
FAIL: Risk register missing or fewer than 3 risks.

**Check 6 — Go/no-go checklist present**
The strategy includes a go/no-go checklist for cutover authorisation.
PASS: Checklist present.
FAIL: Checklist missing.

**Check 7 — Phase durations consistent with inventory estimates**
The phase timelines in the strategy are consistent with the effort estimates in the migration inventory (within ±20%).
PASS: Consistent.
FAIL: Report discrepancies.

**Check 8 — Every snapshot has a migration strategy; `rebuild_from_T` is signed off**
If the inventory lists any snapshots, the strategy's "Snapshot migration" section assigns each one a strategy of exactly `copy_and_continue` or `rebuild_from_T`. Every `rebuild_from_T` snapshot carries a recorded data-owner sign-off (name + date) — a `rebuild_from_T` with no sign-off is a FAIL, since it silently discards SCD-2 history. The default for any snapshot the section does not explicitly override must be `copy_and_continue`.
PASS: every snapshot has a valid strategy and every `rebuild_from_T` is signed off. FAIL: list snapshots with no strategy, an invalid strategy value, or a `rebuild_from_T` lacking a sign-off. Note "no snapshots in scope" when the inventory lists none.

### Update status

```yaml
artifacts:
  migration_strategy:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_strategy` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_strategy` as artifact_id, `Migration Strategy` as artifact_name, and the `file` value from `artifacts.migration_strategy` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_strategy` as artifact, `validate` as action.
