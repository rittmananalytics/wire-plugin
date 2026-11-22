---
wire_schema: "1.0"
command: validate
artifact: bi_migration_plan
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
    path: "migration/bi_migration_plan.md"
    description: "Validation section appended with a per-check PASS/FAIL table"
preconditions:
  - artifact: bi_migration_plan
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Validate the BI migration plan: every in-scope object in exactly one batch or the drop list, dependencies resolve, register rows match scope, rulings made or parked"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# BI Migration Plan: Validate

## Purpose

Checks the plan is complete and self-consistent before the director reviews it and before any Omni work starts: every audited object is placed once, every drop has a reason, every content batch waits on a model batch that carries its explores, the register matches the scope, and every ruling is either recorded or parked. Produces a PASS/FAIL report.

## Prerequisites

- `migration/bi_migration_plan.md` exists (bi_migration_plan generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md`
- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv`
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv`
- `.wire/releases/$ARGUMENTS/decisions.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the plan

Read the plan, the batches CSV, the register and the two audit catalogs. Confirm the plan has the sections from generate Step 7 and the batches CSV carries the contract columns.

### Step 2: Run validation checks

**Check 1: Every content object is placed exactly once**
Every `dashboard`, `look`, `schedule` and `alert` row in the content catalog appears in the batches CSV exactly once, either with a `batch_id` or with `ruling: drop` and an empty `batch_id`.
PASS/FAIL with objects missing or duplicated.

**Check 2: Every in-scope model object is placed exactly once**
Every view and explore the plan lists as carried appears in exactly one model batch. Every view listed under "Model not carried" has a reason.
PASS/FAIL.

**Check 3: Every drop has a reason**
Every row with `ruling: drop` has a non-empty reason in the plan's drop list (stale, text tile, director ruling, no in-scope references).
PASS/FAIL.

**Check 4: Content batches depend on the right model batch**
For every content batch, every explore in its dashboards' `explore_refs` is carried by a model batch with an id less than or equal to `depends_on_batch`.
PASS/FAIL with the batches whose explores arrive later than they are needed.

**Check 5: Model batch order respects view dependencies**
No topic is placed in a batch earlier than any view it joins. No batch id is repeated with a different `batch_kind`.
PASS/FAIL.

**Check 6: Register rows match scope**
The register holds exactly one row per in-scope object (view, topic, dashboard, tile, look, schedule, group), all `state: pending` or later; no row for a dropped object; `register_rows` in `status.md` equals the count.
PASS/FAIL with the mismatches.

**Check 7: Every ruling is made or parked**
Each of the seven rulings in generate Step 3 has either a recorded decision (with a name and date from `decisions.md`) or a `parked_decisions` entry in `status.md`. No ruling is silently defaulted except the two with stated defaults (topic architecture, permission map proposal).
PASS/FAIL with the rulings that are neither.

**Check 8: PDT dispositions**
Every PDT in the audit's redesign register has a disposition (`dbt`, `omni_query_view`, `drop`) or is parked.
PASS/FAIL.

**Check 9: Reference key**
Every batch id and ruling id cited in the plan appears in its Reference key table, per `specs/utils/reference_legibility.md`.
PASS/FAIL.

### Step 3: Write validation report

Append a `## Validation` section to `migration/bi_migration_plan.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  bi_migration_plan:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:bi-migration-plan-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:bi-migration-plan-validate $ARGUMENTS
```

## Output Files

- Updated `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (Validation section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact_id, `BI Migration Plan` as artifact_name, and the `file` value from `artifacts.bi_migration_plan` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bi_migration_plan` as artifact, `validate` as action.
