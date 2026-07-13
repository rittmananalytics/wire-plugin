---
description: Human adjudication gate for relocated carve-out dbt models
argument-hint: <release-folder> [--wave id \
---

# Human adjudication gate for relocated carve-out dbt models

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Human adjudication gate for relocated carve-out dbt models — approve the manifest, spot-check injected predicates, resolve any manual-review-required models
argument-hint: <release-folder> [--wave id | --batch N | --select selector]
---

# dbt Carveout Relocate — Review

## Purpose

Human approval gate before a batch/wave of relocated carve-out models is considered done. Presents the relocation manifest, a diff sample of injected predicates, and the manual-review-required list — the reviewer either signs off the manual-review entries by hand (then re-runs generate/validate on just those models) or resolves them here with an explicit note.

## Flags

- `--wave <id>` / `--batch N` / `--select <selector>` — which manifest to review, mirroring the scope `dbt-carveout-relocate-generate` was run with. Under `--wave`, load `dbt_carveout_relocate_manifest_{wave_id}.md`; otherwise, load the unscoped `dbt_carveout_relocate_manifest.md`. `--batch` and `--select` runs write the unscoped filename today (only `--wave` output is filename-suffixed), so both read the unscoped manifest.

## Prerequisites

- `migration/dbt_carveout_relocate_manifest.md` (or `_{wave_id}.md` under `--wave`) with `validate: pass`

## Workflow

### Step 1: Present the manifest summary

Display: scope resolved (wave/batch/selector), source and target project paths, target project/dataset, and the per-bucket counts (confident-region relocated unchanged, shared-row-level with predicate injected, manual-review-required).

### Step 2: Present a diff sample of injected predicates

For a representative sample of `shared-row-level` models (or all of them, if the set is small), show the before/after diff around the injected `WHERE` clause, so the reviewer can confirm the predicate landed on the outermost `SELECT` and reads correctly — not just that a check passed.

### Step 3: Resolve the manual-review-required list

If non-empty, this blocks approval until every entry is resolved one of two ways:
- **Hand-fix and re-run** — the reviewer (or a consultant) edits the model's injection point directly, then re-runs `dbt-carveout-relocate-generate`/`-validate` scoped to just that model (`--select <model>`) so it clears the flag on its own merits.
- **Explicit sign-off here** — the reviewer records why the model is correct as relocated despite the flag (e.g. it's `confident-region` in disguise and doesn't need a predicate at all, or the ambiguous structure was checked by hand and found safe). This is the sign-off `dbt-carveout-relocate-validate`'s Check 4 looks for.

If any entry has neither a clean re-run nor an explicit sign-off, stop: `[wire] N manual-review-required model(s) unresolved. Address each before approving.`

### Step 4: Record decision

```markdown
## Review — dbt Carveout Relocate

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Scope**: {{WAVE_OR_BATCH_OR_SELECTOR}}
**Decision**: approved | changes_requested

### Manual-review-required sign-offs
[Per entry: model, reason it was flagged, resolution (hand-fixed and re-validated / signed off), rationale if signed off]
```

### Step 5: Update status

```yaml
artifacts:
  dbt_carveout_relocate:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    wave_review:                 # set only when run with --wave, keyed by wave id
      B01: approved | changes_requested
    manual_review_signoffs:      # one entry per manual-review-required model resolved by explicit sign-off (not by hand-fix + re-run)
      - model: "<model_name>"
        rationale: "<reason>"
```

### Step 6: Output next command

If approved, and more waves/batches remain in the carve-out plan:
```
/wire:dbt-carveout-relocate-generate $ARGUMENTS --wave <next>
```

If this was the last wave/batch, and this run targeted the playground:
```
Re-run against production once playground equivalency passes:
/wire:dbt-carveout-relocate-generate $ARGUMENTS --wave <id> --target-project <production-project>
```

## Review Gate

This review is the point where a relocated batch/wave is considered done. Re-running `dbt-carveout-relocate-generate` for the same scope after this gate overwrites the relocated files and requires re-validation and re-review.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact_id, `dbt Carveout Relocate` as artifact_name, and the `file` value from `artifacts.dbt_carveout_relocate` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_carveout_relocate` as artifact, `review` as action.

Execute the complete workflow as specified above.
