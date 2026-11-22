---
wire_schema: "1.0"
command: validate
artifact: db_object_audit
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
  - artifact: db_object_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate db object audit classification completeness

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# DB Object Audit — Validate

## Purpose

Checks that every cataloged object has been classified, that object counts are internally consistent, and that platform-specific feature tags have been applied where expected. Produces a PASS/FAIL report.

## Prerequisites

- `audit/db_object_audit.md` exists (db_object_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/db_object_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Validation Checks

**Check 1 — All objects classified**
Every row in the object catalog has a non-null `migration_approach` value.
PASS: All rows classified.
FAIL: List objects missing classification.

**Check 2 — All objects have volume tier**
Every table and materialized view has a `row_volume_tier` assigned.
PASS: All tables/MVs have volume tier.
FAIL: List objects missing volume tier.

**Check 3 — Views have SQL captured**
Every view and materialized view has the full DDL/SQL definition stored in the audit (or noted as "unavailable" with a reason).
PASS: All views have SQL or explicit unavailability note.
FAIL: List views with no SQL and no note.

**Check 4 — Feature detection applied to views**
Views with migration_approach: translate_view have been scanned and feature tags applied (even if the tag list is empty).
PASS: Feature detection run for all translate_view objects.
FAIL: List views missing feature detection scan.

**Check 5 — Object count matches status.md**
The total count in the audit table matches `total_objects` in `status.md`.
PASS: Counts match.
FAIL: Report discrepancy.

**Check 6 — Evaluate objects have notes**
Every object with `migration_approach: evaluate` has a `migration_notes` entry explaining why manual assessment is needed.
PASS: All evaluate objects have notes.
FAIL: List evaluate objects without notes.

**Check 7 — Schema inventory present**
The audit includes a distinct list of all databases/projects and schemas/datasets found.
PASS: Schema inventory section present and populated.
FAIL: Schema inventory missing or empty.

### Write validation report

Append `## Validation` to `audit/db_object_audit.md` with the check results table and gap list, following the same format as the ingestion audit validation.

### Update status

```yaml
artifacts:
  db_object_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `db_object_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `db_object_audit` as artifact_id, `DB Object Audit` as artifact_name, and the `file` value from `artifacts.db_object_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `db_object_audit` as artifact, `validate` as action.
