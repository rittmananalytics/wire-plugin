---
wire_schema: "1.0"
command: validate
artifact: migration_inventory
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
  - artifact: migration_inventory
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate migration inventory object counts and dependency graph

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Inventory — Validate

## Validation Checks

**Check 1 — Object counts match audit totals**
The inventory object count for each type matches the corresponding audit:
- Connectors match `ingestion_audit.connector_count`
- DB objects match `db_object_audit.total_objects`
- dbt models match `dbt_audit.model_count`
- Orchestration jobs match `orchestration_audit.job_count`
PASS: All counts match.
FAIL: List discrepancies.

**Check 2 — All objects have migration approach**
Every object in the inventory has a `migration_approach` value.
PASS/FAIL with gaps.

**Check 3 — Dependency graph is acyclic**
The constructed dependency graph contains no cycles.
PASS: No cycles detected.
FAIL: List cyclic paths.

**Check 4 — Effort estimate is present**
The inventory contains a non-null total effort estimate with phase breakdown.
PASS: Effort estimate populated.
FAIL: Effort estimate missing or zero.

**Check 5 — All evaluate objects have remediation notes**
Every object with `migration_approach: evaluate` has a note in the inventory explaining the open question.
PASS: All evaluate objects noted.
FAIL: List objects without notes.

**Check 6 — Cross-references are valid**
Spot-check 10 dbt models in the inventory — confirm each one's referenced source tables appear in the db_object_audit.
PASS: All spot-checked refs found.
FAIL: List missing references.

**Check 7 — Snapshots inventoried as their own object type with graph edges**
If `dbt_snapshots.csv` from the dbt audit lists any snapshots, every one appears in the inventory as a `snapshot` object type (not folded into `dbt_model`), carrying its strategy, `unique_key`, `target_schema`, upstream ref/source, and downstream dependents. Confirm the dependency graph contains, for each snapshot, an **upstream→snapshot** edge and a **snapshot→dependent** edge to each downstream model.
PASS: every audited snapshot is present as a `snapshot` object with both edge directions. FAIL: list snapshots missing from the inventory, mistyped as `dbt_model`, or missing upstream/downstream edges. Note "no snapshots defined" when the audit lists none.

### Update status

```yaml
artifacts:
  migration_inventory:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_inventory` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_inventory` as artifact_id, `Migration Inventory` as artifact_name, and the `file` value from `artifacts.migration_inventory` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_inventory` as artifact, `validate` as action.
