---
wire_schema: "1.0"
command: validate
artifact: target_setup
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
  - artifact: target_setup
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate target setup scripts

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Target Setup — Validate

## Validation Checks

**Check 1 — All in-scope schemas have DDL**
Every schema from the db_object audit with a non-exclude migration approach has a CREATE statement in `01_schemas.sql`.
PASS/FAIL.

**Check 2 — All recreate_ddl tables have DDL**
Every table with `migration_approach: recreate_ddl` has a CREATE TABLE statement in `02_tables.sql`.
PASS/FAIL with gaps.

**Check 3 — No TODO items in schema/table DDL without tracking notes**
Every `-- TODO` comment in the DDL is also listed in the MANIFEST.md as a known open item.
PASS/FAIL.

**Check 4 — Column type translations are complete**
Every column in the table DDL has a target-platform type (no untranslated source types remain).
PASS/FAIL.

**Check 5 — Security DDL present**
`04_security.sql` is non-empty and contains at least the GRANT statements for critical roles identified in the security audit.
PASS/FAIL.

**Check 6 — MANIFEST.md lists all scripts**
Every SQL script file written is listed in MANIFEST.md with a description — the four core scripts (`01`–`04`), plus `05_udfs.sql` when it was generated.
PASS/FAIL.

**Check 7 — SQL syntax is valid for target platform**
Perform a static syntax check: scan for keywords illegal on the target platform (e.g., BQ-only syntax in Snowflake scripts, or vice versa).
PASS: No illegal syntax found.
FAIL: List lines with illegal syntax.

**Check 8 — UDF layer complete (when a UDF layer exists)**
Read `audit/batch_zero_plan.json`. If it exists and has `layer: udf` entries:
- Every `action: translate` UDF has a `CREATE FUNCTION` statement in `05_udfs.sql`, and the statements are in tier order (a UDF appears after every UDF it depends on, with `create_udfs` last).
- Every `action: redesign` UDF is named in the MANIFEST's **UDF redesign decisions** section — not silently emitted as a `CREATE FUNCTION`.
- No untranslated source-dialect function bodies remain in the emitted UDF DDL (same scan as Check 7, applied to `05_udfs.sql`).
If `batch_zero_plan.json` is absent or has no `layer: udf` entries, this check is **N/A** (not a FAIL) — record "no UDF layer".
PASS/FAIL with gaps and out-of-order or mis-routed UDFs listed.

### Update status

```yaml
artifacts:
  target_setup:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `target_setup` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `target_setup` as artifact_id, `Target Setup` as artifact_name, and the `file` value from `artifacts.target_setup` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `target_setup` as artifact, `validate` as action.
