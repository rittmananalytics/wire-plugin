---
wire_schema: "1.0"
command: utility
artifact: lookml_model
domain: migration
release_types:
  - bi_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> lints one batch (default: the most recently written)"
produces:
  - type: report
    path: "migration/lookml_model/lint_<batch_id>.md"
    description: "Per-rule PASS/FAIL table with the offending file and line"
preconditions:
  - artifact: lookml_model
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Offline lint of emitted LookML for one batch: no Tableau, Metabase, Looker Studio or Omni syntax left, Wire LookML conventions, primary keys on joined views"
argument-hint: <release-folder> [--batch <id>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# LookML Model: Lint

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Catches translations that Looker's validator would accept and that still return the wrong answer, before validate runs against Looker.

## Pair: metabase_to_looker

**Rule 1** is `python3 <plugin-root>/scripts/mb_to_lookml.py lint migration/lookml_model/<batch_id>` (and on `hand/`). It fails on Metabase template tags (`{{...}}`), optional clauses (`[[...]]`), snippets, `card__` references, MBQL fragments, or a folder with no LookML. Rules 2 to 4 are unchanged.

## Pair: looker_studio_to_looker

**Rule 1** is `python3 <plugin-root>/scripts/ls_to_lookml.py lint migration/lookml_model/<batch_id>` (and on `hand/`). It fails on Looker Studio field references (`t0.`), chart field ids (`qt_...`), record count fields, Looker Studio-only functions (`COUNT_DISTINCT(`, `NARY_MAX(`), a field defined twice, or a folder with no LookML. Rules 2 to 4 are unchanged.

## Pair: omni_to_looker

**Rule 1** is `python3 <plugin-root>/scripts/omni_to_lookml.py lint migration/lookml_model/<batch_id>` (and on `hand/`). It fails on Omni timeframe references (`${field[month]}`, `view.field[date]`), Mustache templates (`{{ filters... }}`), Omni model keys (`aggregate_type:`, `base_view:`, `on_sql:` and others), a dimension that references a measure (Looker: "Field references an aggregate"), a field defined twice (counting the fields a dimension group generates), or a folder with no LookML. Rules 2 to 4 are unchanged.

## Workflow

**Rule 1: No Tableau expression left.** `python3 <plugin-root>/scripts/twb_to_lookml.py lint migration/lookml_model/<batch_id>` (and on `hand/`). Fails on LOD braces, Tableau-only functions (`ZN`, `IIF`, `COUNTD`, `DATETRUNC`, `ATTR`, `WINDOW_*`, `RUNNING_*`), `[Parameters].` and `[field]` references in any `sql:`. PASS/FAIL.

**Rule 2: Wire LookML conventions.** `python3 <plugin-root>/scripts/lint_conventions.py --domain lookml` over the batch. PASS/FAIL.

**Rule 3: Joined views have a primary key.** Every view joined with `many_to_one` or `one_to_many` has a `primary_key: yes` dimension (symmetric aggregates need it). PASS/FAIL.

**Rule 4: Every needs_human item has a resolution or a parked decision.** PASS/FAIL.

Write `migration/lookml_model/lint_<batch_id>.md` and output `/wire:lookml-model-validate $ARGUMENTS --batch <batch_id>` when every rule passes.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact, `lint` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact_id, `LookML Model` as artifact_name, and the `file` value from `artifacts.lookml_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `lookml_model` as artifact, `lint` as action.
