---
wire_schema: "1.0"
command: validate
artifact: looker_audit
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: report
    path: "audit/looker_audit.md"
    description: "Validation section appended to the audit with a per-check PASS/FAIL table"
preconditions:
  - artifact: looker_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Validate the Looker audit: every construct classified, every redesign row reasoned, usage recorded or marked unknown, catalogs parse, counts match status.md"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Audit: Validate

## Purpose

Checks the Looker audit for completeness and internal consistency before the plan is built on it: every model construct has one of the four classes, every `redesign` row says why, every content row has usage or an explicit `unknown`, no `${TABLE}` reference has been left in a row that claims `mechanical` without a target field, the two catalogs parse with the contract columns, and the counts match `status.md`. Produces a PASS/FAIL report with the gaps to fix.

## Prerequisites

- `audit/looker_audit.md` exists (looker_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/looker_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv`
- `.wire/releases/$ARGUMENTS/status.md`
- `wire/bi_pairs/looker_to_omni/feature_detection.md`

## Workflow

### Step 1: Load the audit

Read the report and both catalogs. Confirm the report has the expected sections (Summary, Classification breakdown, Usage distribution, Redesign register, Explore to content map, Unresolved references, Text and markdown tiles, Usage source). Confirm both CSVs parse and carry exactly the contract columns in the contract order.

### Step 2: Run validation checks

**Check 1: Every model row has a class**
Every row in `looker_model_catalog.csv` has `translation_class` in `mechanical`, `assisted`, `redesign`. (`drop` is not valid for model rows.)
PASS/FAIL with the rows missing or misusing a class.

**Check 2: Every model row has a complexity consistent with its class**
`mechanical` rows are `Low`, `assisted` rows are `Medium`, `redesign` rows are `High`. A row with `reason` starting `unresolved reference` is `High` whatever its class.
PASS/FAIL with the inconsistent rows.

**Check 3: Every redesign row has a reason**
`reason` is non-empty on every `redesign` row and names the construct that triggered it (Liquid, parameter, filter field, PDT, html, unmapped timeframe, symmetric aggregate without primary key, native derived table).
PASS/FAIL.

**Check 4: Feature detection agrees with the class**
Re-run the `feature_detection.md` regexes over the LookML source cited by each row's `lkml_file` and `line`. A row whose source matches a `redesign` pattern (Liquid, `parameter`, PDT keys, `html`) must be classified `redesign`. A row whose source matches none of the `redesign` or `assisted` patterns must not be classified `redesign`.
PASS/FAIL with the disagreeing rows.

**Check 5: Every content row has usage or an explicit unknown**
Every `dashboard` and `look` row has `last_viewed` and `views_90d` populated, either with values or with the literal `unknown`. If any row is `unknown`, `status.md` must carry `usage_source: unavailable`.
PASS/FAIL.

**Check 6: Text tiles recorded**
Every dashboard with `has_text_tile: true` has at least one `tile` row with `translation_class: drop` and `reason: text tile, recreate by hand`. No `tile` row is `drop` for any other reason at audit stage.
PASS/FAIL.

**Check 7: Content references resolve to the model**
Every explore named in `explore_refs` exists as an `explore` row in the model catalog. Every field in `fields_refs` exists as a field row, or the content row carries `reason: references field outside the parsed repo`.
PASS/FAIL with the unresolved references.

**Check 8: Counts match status.md**
`view_count`, `explore_count`, `field_count`, `dashboard_count`, `look_count`, `tile_count`, `mechanical_count`, `assisted_count`, `redesign_count`, `drop_count` in `status.md` equal the catalog counts.
PASS/FAIL with the mismatches.

### Step 3: Write validation report

Append a `## Validation` section to `audit/looker_audit.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  looker_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:looker-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:looker-audit-validate $ARGUMENTS
```

## Output Files

- Updated `.wire/releases/$ARGUMENTS/audit/looker_audit.md` (Validation section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_audit` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_audit` as artifact_id, `Looker Audit` as artifact_name, and the `file` value from `artifacts.looker_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_audit` as artifact, `validate` as action.
