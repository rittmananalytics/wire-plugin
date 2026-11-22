---
wire_schema: "1.0"
command: validate
artifact: omni_model
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> validates one model batch (default: the most recently linted batch); --all validates every written batch"
produces:
  - type: report
    path: "migration/omni_model/omni_model.md"
    description: "Validation section appended to the batch summary: per-check PASS/FAIL for the batch and the overall result"
preconditions:
  - artifact: omni_model
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Validate one batch of the emitted Omni model on the branch: lint passed, the Omni validator reports no blocking issue, every in-scope field exists, and one smoke query per topic returns rows"
argument-hint: <release-folder> [--batch <id> | --all]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding. The gate reads `artifacts.omni_model.generate`; while batches are still being written that field is `in_progress`. Treat a batch present in `batches_complete` as meeting the gate for that batch.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

Omni: reads and validates the MODEL BRANCH only. No merge, no edit to the
  published model.

Warehouse: one smoke query per topic runs through the branch, LIMIT 10.
  Record the count of queries run; they count against the release budget's
  warehouse_spend line under the release director model.
```

---

# Omni Model: Validate

## Purpose

Proves that a batch of emitted Omni YAML is not only well formed but usable: Omni's own validator reports nothing blocking, every field the plan says is in scope exists on the branch, and every topic answers a query. Lint (`/wire:omni-model-lint`) runs first and offline; this command is the first step that spends CLI and warehouse calls, so it refuses to start while lint is absent or failing.

## Prerequisites

- `migration/omni_model/lint_<batch_id>.md` exists for the batch with overall PASS
- Omni CLI configured against the target profile (`omni whoami whoami` succeeds)
- `bi_migration.omni_branch` set in status.md

## Inputs

- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/**`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/needs_human.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/lint_<batch_id>.md`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv` (in-scope fields: rows for this batch's views with `translation_class` `mechanical` or `assisted`)
- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Resolve the batch and confirm lint

`--batch <id>`, or `--all` for every batch in `batches_complete`, or the batch named in `artifacts.omni_model.lint_batch`. For each batch, read `migration/omni_model/lint_<batch_id>.md`. If the file is missing or its overall result is FAIL, stop:

```
Lint has not passed for batch <batch_id>. Run /wire:omni-model-lint $ARGUMENTS --batch <batch_id> first.
```

### Step 2: Run validation checks

**Check 1: Omni validator, no blocking issues**
```bash
omni models validate <bi_migration.omni_model_id> --branch-id <bi_migration.omni_branch>
```
PASS when no returned issue has `is_warning: false`. FAIL listing each blocking issue with its file and message. Warnings are recorded in the report but do not fail the check.

**Check 2: Every emitted file is on the branch, once**
For each emitted `.view`, `.topic` and the `relationships.yaml`, `omni models yaml-get ... --branch-id ... --mode extension` returns content matching the local file, and `omni models get-views <modelId>` lists each view exactly once. FAIL names any file missing, different, or duplicated.

**Check 3: Every in-scope field exists**
From `audit/looker_model_catalog.csv`, take every dimension, dimension_group and measure row whose view is in this batch and whose `translation_class` is `mechanical` or `assisted`. Each must exist on the branch as a field of the emitted view (a dimension group becomes one dimension with timeframes; a `tier` becomes a dimension with `bin_boundaries`). A `redesign` row is not expected and its absence is correct. FAIL names each missing field with its class.

**Check 4: Assisted emissions confirmed**
Every `needs_human.json` item with `emitted: true` is confirmed one of three ways and the item's `status` is updated: `confirmed` (the field validated in Check 1 and answers in Check 5), `changed` (the consultant edited the YAML and re-wrote it to the branch, recorded on the item), or `parked` (turned into a parked decision). An item still `open` after this step is FAIL.

**Check 5: One smoke query per topic**
For each emitted topic, run one query through the branch: the topic's base view count measure (or its first measure) grouped by its first dimension, `limit: 10`:
```bash
omni query run --body '{"query": {"table": "<base_view>", "fields": ["<view>.<dimension>", "<view>.<measure>"], "limit": 10, "sorts": [], "filters": {}, "pivots": [], "calculations": [], "column_totals": {}, "row_totals": {}, "fill_fields": [], "userEditedSQL": "", "join_paths_from_topic_name": "<topic>"}, "branchId": "<bi_migration.omni_branch>"}'
omni query wait --job-ids <jobId>
```
PASS when the job completes, returns at least one row, and `missing_fields` is empty. A topic returning zero rows is a FAIL with reason `empty_topic` unless the plan records the source table as empty. Record the number of queries run.

**Check 6: needs_human open count matches**
`artifacts.omni_model.needs_human_open` in status.md equals the number of `open` items across the batch's `needs_human.json` after Check 4. FAIL on mismatch.

### Step 3: Write the validation section

Append to `migration/omni_model/omni_model.md`:

```markdown
## Validation: batch b01

| Check | Result | Detail |
|---|---|---|
| 1 Omni validator | PASS | 0 blocking, 3 warnings |
| 2 Files on branch | PASS | 18/18 |
| 3 In-scope fields | FAIL | 2 missing: orders.margin_pct (assisted), customers.tenure_band (mechanical) |
| 4 Assisted confirmed | PASS | 5 confirmed, 1 changed, 0 parked |
| 5 Topic smoke queries | PASS | 3/3 topics, 3 queries run |
| 6 needs_human count | PASS | 2 |

Gaps to address: ...
```

### Step 4: Update status

```yaml
artifacts:
  omni_model:
    validate: pass | fail        # overall: pass only when every batch in batches_complete has passed
    validated_date: "{{TODAY}}"
    batches_validated: [b01]     # batches with a PASS on their latest run
    smoke_queries_run: N         # cumulative this release, for the budget line
```

Overall `validate: pass` requires every batch in `batches_complete` to appear in `batches_validated`. When `--batch` validates one batch of several, set `validate: in_progress` unless that condition holds.

### Step 5: Output next command

If PASS (overall):
```
/wire:omni-model-review $ARGUMENTS
```

If the batch passed but others remain:
```
Batch <batch_id> validated. Batches still to validate: <ids>.
Content for this batch may start: /wire:omni-content-generate $ARGUMENTS --batch <content batch id>
```

If FAIL:
```
Validation failed for batch <batch_id>. Address the gaps listed above, rewrite the changed files to the branch, then re-run:
/wire:omni-model-lint $ARGUMENTS --batch <batch_id>
/wire:omni-model-validate $ARGUMENTS --batch <batch_id>
```

## Output Files

- Updated `.wire/releases/$ARGUMENTS/migration/omni_model/omni_model.md`
- Updated `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/needs_human.json` (item statuses)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact_id, `Omni Model` as artifact_name, and the `file` value from `artifacts.omni_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_model` as artifact, `validate` as action.
