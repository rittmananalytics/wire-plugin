---
wire_schema: "1.0"
command: validate
artifact: lookml_views
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: lookml_views
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify LookML view files are valid, every canonical model is covered, and no orphaned column references exist
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — LookML Views Validate

## Purpose

Confirm that the generated and updated view files are syntactically valid, structurally complete, and correctly wired into the Looker project before the semantic layer step adds metrics on top.

## Usage

```bash
/wire:ads_lookml-views-validate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `lookml_views.generate: complete` or `skipped`

## Skip Condition

If `lookml_views.generate: skipped` in status.md, output:

```
LookML Views — Validate Skipped (bi_tool is not looker)
```

Update status and stop.

---

## Validation Checks

### Check 1 — LookML Syntax

Run the LookML linter against all modified files:

```bash
# Option A — lookml-lint (open source)
lookml-lint <lookml_project_path>/views/<model_name>.view.lkml

# Option B — Looker CLI (if configured)
looker lookml-test --project <project_name>

# Option C — if neither is available, perform a manual syntax check:
# Scan each generated file for:
#   - Balanced braces {}
#   - Valid parameter names (no unknown keys)
#   - sql_table_name ends with ;;
#   - All sql: parameters end with ;;
```

- [ ] All generated/updated view files pass linting with 0 errors

---

### Check 2 — Every Canonical Model Has a View

Cross-reference the new/modified model list from `canonical_models_lineage.md` against the LookML project scan:

- [ ] Every **new** canonical model has exactly one view file with a matching `sql_table_name`
- [ ] No new canonical model is referenced by zero views
- [ ] No duplicate views reference the same `sql_table_name`

---

### Check 3 — Column References

For each view file generated or updated in this phase, check that every `${TABLE}.<column>` reference exists in the underlying dbt model's schema.yml:

```bash
# Extract column names from schema.yml for each model
grep "name:" <dbt_project_path>/models/marts/<domain>/<model>.yml | awk '{print $2}'

# Compare against ${TABLE}. references in the view file
grep -o '\${TABLE}\.[a-z_]*' <lookml_project_path>/views/<view>.view.lkml | \
  sed 's/${TABLE}\.//'
```

- [ ] Every `${TABLE}.<column>` in generated views maps to a column in the dbt schema.yml
- [ ] No orphaned references from modified views (columns removed from the canonical model but still referenced in the view)

---

### Check 4 — Primary Keys

For each generated view:

- [ ] Exactly one dimension has `primary_key: yes`
- [ ] That dimension references a column with `unique` + `not_null` tests in schema.yml
- [ ] No `# TODO: confirm primary_key` comments remain unresolved

---

### Check 5 — Explore Wiring

Read `lookml_views_notes.md` — check the "Explores Needing Manual Review" section:

- [ ] No new views are in the "needs manual wiring" list (all have been added to an explore, either in this step or by the team)

If views remain unwired, **block progression** with:

```
VALIDATION FAIL — N view(s) not yet added to any explore.
Metrics added by ads_semantic-layer-generate on unwired views will be
unreachable in Looker. Resolve before proceeding:

  <view_name> — add to an explore in <lookml_project_path>/models/<model>.model.lkml

Re-run ads_lookml-views-validate after resolving.
```

---

### Check 6 — No Accidental Measure Changes

Diff each modified view file against its pre-modification state (via git diff):

- [ ] No measures were added or removed in existing view files (measures are `ads_semantic-layer-generate`'s responsibility)
- [ ] No existing `measure:` blocks were altered in any way

---

## Status Update

On pass:

```yaml
lookml_views:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
  lint_errors: 0
  coverage_gaps: 0
  orphaned_references: 0
```

On fail, record the specific checks that failed and leave `validate: failed`. Do not proceed to review until all checks pass.
