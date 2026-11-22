---
wire_schema: "1.0"
command: validate
artifact: region_tagging
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
  - artifact: region_tagging
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate region tags — all three buckets populated, every in-scope item classified exactly once

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Region Tagging — Validate

## Validation Checks

Read `migration/region_tags.csv`, `migration/region_tagging.md`, and the source audits. Read `target_region` from status.md.

**Check 1 — All three buckets are populated**
`region_tags.csv` contains at least one row in each of `confident-region`, `shared-row-level`, and `global-deferred`.
PASS: all three buckets have ≥1 item.
FAIL: list any empty bucket.

**Check 2 — Every in-scope item is classified exactly once**
Build the union of in-scope items from the audits (dbt, reverse_etl/Hightouch, ingestion, security, db_object). Confirm every item appears in `region_tags.csv` exactly once — no item missing, no item in two buckets, no duplicate rows.
PASS: one-to-one match between in-scope items and CSV rows.
FAIL: list missing items, duplicates, and any CSV rows that don't correspond to an in-scope item.

**Check 3 — Every row is complete**
Each row has a non-empty `item_id`, `item_type`, `source_audit`, `bucket`, `signal`, and `confidence_score`.
PASS/FAIL with rows missing fields.

**Check 4 — Bucket and score values are valid**
`bucket` is one of `confident-region | shared-row-level | global-deferred`; `confidence_score` is a number in `[0.0, 1.0]`.
PASS/FAIL with offending rows.

**Check 5 — Candidates only, no decisions**
`region_tags.csv` carries no include/exclude, keep/remove, or deletion column, and no item is marked as excluded or removed. The artifact is candidates for adjudication, not a scope decision.
PASS: no decision/removal columns present.
FAIL: a binary include/exclude or removal field was emitted.

**Check 6 — Adjudication pile present**
The summary lists an adjudication pile, and it contains at least every `shared-row-level` row plus any row below the confidence threshold.
PASS/FAIL.

**Check 7 — Target region recorded**
The summary and status record the `target_region` used (default `de` if no `--region` was passed).
PASS/FAIL.

### Update status

```yaml
artifacts:
  region_tagging:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `region_tagging` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `region_tagging` as artifact_id, `Region Tagging` as artifact_name, and the `file` value from `artifacts.region_tagging` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `region_tagging` as artifact, `validate` as action.
