---
wire_schema: "1.0"
command: validate
artifact: ingestion_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: report
    path: "audit/ingestion_audit.md"
    description: "PASS/FAIL validation report with gap list, appended to the audit document as a Validation section"
preconditions:
  - artifact: ingestion_audit
    action: generate
    outcome: complete
valid_next:
  - review
delegates_to:
  - utils/precondition_gate
description: Validate ingestion audit completeness and migration flags
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Ingestion Audit — Validate

## Purpose

Checks the ingestion audit for completeness, flag consistency, and that every connector has been assigned a complexity rating and a migration decision. Produces a PASS/FAIL report with specific gaps to address before the audit can proceed to review.

## Prerequisites

- `audit/ingestion_audit.md` exists (ingestion_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/ingestion_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, By-service-type, Migration flags, Recommended order).

### Step 2: Run validation checks

## Validation Checks

**Check 1 — All connectors have a complexity rating**
Every row in the connector table has a value in the `complexity` column (Low / Medium / High).
PASS: All rows populated.
FAIL: List rows missing complexity.

**Check 2 — All connectors have a migration decision**
Every connector has `include_in_migration: true` or `include_in_migration: false` (not blank or "TBD").
PASS: All decisions populated.
FAIL: List connectors missing a decision.

**Check 3 — Broken connectors are addressed**
Any connector with `status: broken` has `migration_notes` explaining whether it will be repaired before migration or excluded.
PASS: All broken connectors have a note.
FAIL: List broken connectors without notes.

**Check 4 — Column exclusions flagged**
If `fivetran_column_selections.csv` was loaded, every connector with exclusions has a note in the audit.
PASS: Exclusions accounted for.
FAIL: List connectors with exclusions not noted in the audit.

**Check 5 — Row volume estimates present**
At least 80% of connectors have a non-null `row_count_estimate`. (Exact counts are not required — an order-of-magnitude estimate suffices.)
PASS: ≥80% populated.
FAIL: Report percentage populated and list connectors missing estimates.

**Check 6 — Recommended migration order is logical**
Low-complexity connectors appear before High-complexity in the recommended order. Any High-complexity connector appearing before a Low one must have a written justification.
PASS: Order is consistent with complexity ratings.
FAIL: List out-of-order entries.

**Check 7 — Connector count matches source**
If data source was Fivetran MCP: the count in `status.md` (`connector_count`) matches the rows in the audit table.
If data source was CSV: the count matches the CSV row count (excluding header).
PASS: Counts match.
FAIL: Report discrepancy.

### Step 3: Write validation report

Append a `## Validation` section to `audit/ingestion_audit.md`:

```markdown
## Validation

**Run date**: {{TODAY}}
**Overall result**: PASS | FAIL

| Check | Result | Detail |
|-------|--------|--------|
| 1. Complexity ratings complete | PASS/FAIL | ... |
| 2. Migration decisions complete | PASS/FAIL | ... |
| 3. Broken connectors addressed | PASS/FAIL | ... |
| 4. Column exclusions flagged | PASS/FAIL | ... |
| 5. Row volume estimates present | PASS/FAIL | ... |
| 6. Migration order logical | PASS/FAIL | ... |
| 7. Connector count matches source | PASS/FAIL | ... |

### Gaps to address
[List any FAIL items with specific connectors/rows to fix]
```

### Step 4: Update status

```yaml
artifacts:
  ingestion_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:ingestion-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:ingestion-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_audit` as artifact_id, `Ingestion Audit` as artifact_name, and the `file` value from `artifacts.ingestion_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_audit` as artifact, `validate` as action.
