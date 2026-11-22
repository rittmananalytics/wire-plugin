---
wire_schema: "1.0"
command: validate
artifact: omni_content
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
      description: "--batch <id> validates one content batch (default: the most recently planned or written batch)"
produces:
  - type: report
    path: "migration/omni_content/omni_content.md"
    description: "Validation section appended to the batch summary: pre-write plan checks and post-write document checks, PASS/FAIL per check"
preconditions:
  - artifact: omni_content
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate a content batch twice, before the write (every planned field, control and chart type resolves on the branch) and after it (every created document reads back with the planned tiles)
argument-hint: <release-folder> [--batch <id>]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding. The gate reads `artifacts.omni_content.generate`; while content batches are still being planned that field is `in_progress`. Treat a batch with a `plan.json` on disk as meeting the gate for the pre-write checks, and a batch in `batches_complete` as meeting it for the post-write checks.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

Omni: reads only. Field existence is checked with yaml-get and get-views on the
  branch; created documents are read with v2-get. No document is created,
  patched or published here.

Warehouse: no queries.
```

---

# Omni Content: Validate

## Purpose

Two passes over one batch. The **pre-write pass** proves the plan is buildable: every field a tile names exists on the branch, every control maps to a field, every tile has a chart type, every skipped tile has a reason from the closed set. It is the gate `omni-content-generate --write` reads. The **post-write pass** proves the write did what the plan said: every manifest row marked `created` resolves in Omni and carries the planned tiles and controls. The ground truth for both is the branch and the instance, never the plan's own claims about itself.

## Prerequisites

- `migration/omni_content/<batch_id>/plan.json` exists
- Omni CLI configured against the target profile

## Inputs

- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/plan.json`
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/manifest.csv`
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/source/*.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<model batch>/**`
- `wire/bi_pairs/looker_to_omni/content_mapping.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Resolve the batch and the pass

`--batch <id>` or the batch named last in `artifacts.omni_content.batches_complete` or, failing that, the most recently written `plan.json`. Run the pre-write checks always. Run the post-write checks when `manifest.csv` has any row with `state: created`.

### Step 2: Pre-write checks

**Check 1: Plan current**
`plan.json` is newer than every `source/<dashboard_id>.json` it was derived from, and newer than the model batch's `omni_model.md` validation entry. A plan older than either is FAIL, reason `plan_stale`.

**Check 2: Every field resolves on the branch**
Re-derive the field set from each dashboard's body (every `query.fields` entry, every `sorts[].column_name`, every filter key, every control field). Each must exist on the branch: `omni models get-views <modelId>` lists the view, and `omni models yaml-get` for the view file contains the dimension or measure (a timeframe suffix `[month]` resolves against the dimension's `timeframes`). FAIL names each unresolved field and the tile.

**Check 3: Every control maps to a field, every map key to a tile**
Each `controls.data` entry has a field that resolves (Check 2), and every key in its `map` is a tile key in `queryPresentations.order` (or `false` for an exclusion). FAIL names the control and the dangling key.

**Check 3b: Every control reaches every tile, and no quarter-grained date key**
Every tile key in `queryPresentations.order` has an entry in every control's `map` (a value, or `false` for a deliberate exclusion); a tile absent from a control's map is a silent non-filter, not an exclusion. No date control uses a `[fiscal_quarter]` or `[quarter]` field key (Omni's own migration guide records that these return 0 rows; use `[date]` or `[month]`). FAIL names the control and the tile, or the offending key.

**Check 4: Every tile has a chart type in the mapping table**
Each tile's `visConfig.chartType` and `visType` pair appears in `wire/bi_pairs/looker_to_omni/content_mapping.md`, the spec is nested under `visConfig.visConfig.config`, and `prefersChart` is `true` for charts. A `table` fallback is PASS only when the tile is listed under `fidelity` with `table_fallback`.

**Check 5: Query collections complete**
Every tile query carries every required key (`table`, `fields`, `join_paths_from_topic_name`, `limit`, `sorts`, `filters`, `pivots`, `calculations`, `column_totals`, `row_totals`, `fill_fields`, `userEditedSQL`), `join_paths_from_topic_name` names an emitted topic, `limit` is set, and no query carries `modelId` or `model_extension_id`. Every `filters` value is an object, never a string.

**Check 6: Skipped tiles accounted for**
Re-derive the tile list from each `source/<dashboard_id>.json`. Every source element is either a planned tile or a skipped entry with a reason from `text_tile`, `liquid`, `unsupported_calc`, `unmapped_field`, `unmapped_filter`. A source element in neither list is FAIL, reason `tile_unaccounted`. A reason outside the set is FAIL.

**Check 7: Layout covers every tile**
Every tile key and every inline-text item appears exactly once in the `containers` tree. FAIL names tiles that would be stored but rendered nowhere.

**Check 8: No unresolved collisions**
No dashboard has `collision: true` without a recorded ruling (`rename` with the new title, `replace` with the identifier to supersede, or `skip`).

If every pre-write check passes, add the batch to `artifacts.omni_content.plan_validated`.

### Step 3: Post-write checks (when any manifest row is `created`)

**Check 9: Every created document resolves**
`omni documents v2-get <target_identifier>` succeeds for each `created` row. FAIL names rows that 404.

**Check 10: Tile and control counts match the plan**
The read-back's `queryPresentations.order` length equals `tiles_planned`, and its `controls.order` length equals the planned control count (allowing for controls Omni materialised from inline tile filters, which are recorded and excluded from the count). FAIL names each mismatch.

**Check 11: Folder placement**
Each created document sits in the plan's folder (`omni documents list` for the folder). FAIL names misplaced documents.

**Check 12: Register agreement**
Every `created` dashboard has a register row at `state: migrated`; every skipped tile a row at `state: deferred`. FAIL names disagreements.

### Step 4: Write the validation section

Append to `migration/omni_content/omni_content.md`:

```markdown
## Validation: batch b05

| Check | Pass | Result | Detail |
|---|---|---|---|
| 1 Plan current | pre-write | PASS | |
| 2 Fields resolve | pre-write | FAIL | 1 unresolved: orders.margin_pct (tile 9, Store Performance) |
| ... | | | |
| 9 Documents resolve | post-write | PASS | 6/6 |
```

### Step 5: Update status

```yaml
artifacts:
  omni_content:
    validate: pass | fail | in_progress   # pass only when every content batch passes both passes
    validated_date: "{{TODAY}}"
    plan_validated: [b05]                 # batches whose pre-write pass PASSED
    batches_validated: [b05]              # batches whose post-write pass PASSED
```

### Step 6: Output next command

Pre-write PASS, not yet written:
```
/wire:omni-content-generate $ARGUMENTS --batch <batch_id> --write
```

Post-write PASS:
```
/wire:bi-equivalency-validate $ARGUMENTS --batch <batch_id>
```
and, when every batch has passed both passes:
```
/wire:omni-content-review $ARGUMENTS
```

FAIL:
```
Validation failed for batch <batch_id>. Address the gaps listed above, then re-run:
/wire:omni-content-generate $ARGUMENTS --batch <batch_id>      (re-plan, for pre-write failures)
/wire:omni-content-validate $ARGUMENTS --batch <batch_id>
```

## Output Files

- Updated `.wire/releases/$ARGUMENTS/migration/omni_content/omni_content.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact_id, `Omni Content` as artifact_name, and the `file` value from `artifacts.omni_content` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_content` as artifact, `validate` as action.
