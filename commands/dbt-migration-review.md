---
description: Review translated dbt models
argument-hint: <release-folder> [--batch N 
---

# Review translated dbt models

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Review translated dbt models
argument-hint: <release-folder> [--batch N | --wave id]
---

# dbt Migration — Review

## Purpose

Internal RA review of a translated dbt batch. The reviewer confirms translation quality, agrees on manual review items, and approves the batch for deployment to the target dbt project.

## Flags

- `--batch N` — review topological batch N only (the `dbt_audit.batch_number` scheme — `batch_N_summary.md`)
- `--wave <id>` — review execution wave `<id>` only (the `migration_batching.csv` scheme — `batch_{wave_id}_summary.md`, since `dbt-migration-generate` Step 1w substitutes the wave id directly into the same `batch_{N}` filename template). Accepts zero-padded (`B01`) or bare (`1`) forms, normalised identically to `dbt-migration-generate`'s `--wave`. Wave-id form and normalisation are the shared contract in `specs/utils/wave_resolution.md` (normative; accepts `2`, `B02`, `b2`, or the `W02` display form). `--batch` and `--wave` read different numbering schemes and cannot be combined — abort if both are supplied: `[wire] --batch and --wave read different numbering schemes and cannot be combined. Pick one.`

## Workflow

### Step 1: Present batch summary

If `--wave <id>` is supplied, normalise it and use the normalised wave id in place of `N` everywhere below (`batch_{wave_id}_summary.md`, `wave_{wave_id}_review` in status.md).

Display the batch_summary.md (or wave summary) contents:
- Models in this batch/wave, by complexity
- Translation patterns applied
- Manual review items

### Step 2: Gather reviewer feedback

First, read the pre-PR faithfulness review for this batch/wave (`/wire:dbt-migration-pre-pr-review $ARGUMENTS --batch N` — run it now if it hasn't been). It surfaces the deploy-time defect class static parse/lint cannot catch — unrendered dev/incremental branches, unported tests, edge-case runtime failures, deployment-warehouse type mismatch, and dropped column governance — as a structured findings list with `file:line` and a fix per finding. The mechanical findings should already be resolved by `/wire:dbt-migration-fix` (it auto-applies the deterministic fixes and escalates only the judgment calls); what reaches this review is that escalation residue plus any waived items. Do not sign the batch off with unresolved `error`-severity findings; they are exactly the defects that otherwise come back in the client's PR review.

Then:
1. Review the diffs for any Complex models — do the translations look correct?
2. Are the manual review items understood? Who will address each one?
3. Any models where the automated translation should be manually overridden?
4. Are all `error`-severity pre-PR faithfulness findings resolved (or explicitly, defensibly waived and recorded)?

### Step 3: Record decision

Append review block to `batch_{N}_summary.md` (or the wave summary file under `--wave`).

### Step 4: Update status

```yaml
artifacts:
  dbt_migration:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    batch_N_review: approved | changes_requested       # --batch runs
    wave_review:                                        # --wave runs, keyed by wave id
      B01: approved | changes_requested
```

### Step 5: Output next command

If batch N approved and more batches remain:
```
/wire:dbt-migration-generate $ARGUMENTS --batch [N+1]
```

If wave approved and more waves remain:
```
/wire:dbt-migration-generate $ARGUMENTS --wave [next]
```

If all batches/waves approved:
```
/wire:orchestration-migration-generate $ARGUMENTS
```

Execute the complete workflow as specified above.
