---
wire_schema: "1.0"
command: validate
artifact: dbtcharts
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--no-warehouse records the warehouse check as unverified instead of running dct validate --warehouse"
preconditions:
  - artifact: dbtcharts
    action: generate
    outcome: complete
produces:
  - type: report
    path: "dev/dbtcharts_validation_report.md"
    description: "PASS/FAIL report over the eleven checks"
delegates_to:
  - utils/precondition_gate
  - utils/jira_sync
description: Validate dbt Charts boards — dct structure and warehouse dry-run, ref()-only queries, no inline data, labels and notes present, subject-area coverage, needs_human resolved, renders without warnings, design convention lint clean
argument-hint: <release-folder> [--no-warehouse]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbtcharts Validation Command

## Purpose

Check the boards `dbtcharts-generate` wrote against the things that make them safe to hand to a reviewer: they compile, their queries are real against the warehouse, they read models only through `ref()`, they carry the metadata dbt Charts and its AI search depend on, and every model the scaffold saw was either charted or a person decided otherwise.

## Usage

```bash
/wire:dbtcharts-validate 01-dbt-foundation
/wire:dbtcharts-validate 01-dbt-foundation --no-warehouse
```

## Prerequisites

- `dbtcharts.generate == complete` in `status.md` (enforced by the precondition gate)
- The `dct` CLI. If `dct --version` fails, every dct-backed check is `unverified`, and `unverified` is not a pass.

## Workflow

### Step 1: Read what was generated

From `status.md`: `charts_dir`, `boards`, `needs_human`, `needs_human_resolved`, `catalog_rows`, `catalog_unmapped`, `warehouse_validated`. From disk: `<charts_dir>/scaffold_summary.json`, `<charts_dir>/needs_human.json`, `dbt_charts.yml`, and `dev/dbtcharts_generation_report.md`. Ground truth is the files, not the status entry: a board listed in `status.md` but absent on disk is a Critical failure in Check 1.

### Step 2: Run the checks

**Check 1 — Boards exist and `dct validate` passes.** Every path in `status.md` `boards` exists. `dct validate <charts_dir>/ --json` reports `success: true` for every board and zero errors. Warnings are listed by code, not failed on.
Severity: **Critical**. If `dct` is not installed, record `unverified`.

**Check 2 — The warehouse dry-run passes.** `dct validate <charts_dir>/ --warehouse --json` reports zero errors: every query is valid against the warehouse and every chart channel names a column its query returns. Skipped, and recorded as `unverified` with the reason, under `--no-warehouse` or `budget.warehouse_spend: none`.
Severity: **Critical**. `unverified` is not a pass; the report says which check it was and why.

**Check 3 — Queries read models through `ref()` only.** Every `sql:` in every board references tables only as `{{ ref('<model>') }}` (or `{{ source(...) }}` for a declared dbt source). A hard-coded `project.dataset.table`, or a bare table name, is reported with the board, query and text.
Severity: **Major**. A hard-coded name survives a schema move that `ref()` would have followed.

**Check 4 — No inline or external data.** No query is `type: values`, has `columns:`/`values:`/`rows:` blocks, or is `type: http`. The boards read the warehouse; anything else is mock data in the dashboard layer, the same rule `semantic_layer-generate` and `dashboards-generate` apply.
Severity: **Critical**.

**Check 5 — Metadata present.** Every `type: kpi` chart has `label:`; every other chart has `title:`; every query and every chart has a non-empty `notes:`.
Severity: **Major**. Report each missing field with board and chart name.

**Check 6 — Coverage and decisions.** Every fact or dimension model under the warehouse layer, in each subject area that was scaffolded, is either charted in its board or appears in `needs_human.json`; and every `needs_human` item has a decision recorded in the generation report's needs_human table. `needs_human_resolved` in `status.md` must equal `needs_human`.
Severity: **Major**. A model nobody decided about is the gap this check exists for.

**Check 7 — The anchor holds no credentials.** `dbt_charts.yml` sources are `type: dbt_profile` or use `env_var()` for every secret-bearing field; no literal password, key or token appears in it or in any board.
Severity: **Critical**.

**Check 8 — Viz catalog mapping (`dashboard_first`, or wherever a catalog exists).** Every catalog row maps to a chart or is listed as unmapped in the report with the reason from the generate Step 5 table. `catalog_rows` equals mapped plus unmapped.
Severity: **Critical** where a catalog exists; not applicable otherwise.

**Check 9 — One board per subject area, plus the project files.** The board files under `charts/` match the subject areas in `scaffold_summary.json` (plus any the consultant added, which are listed). `charts/meta.yml` sets the theme and `charts/index.yml` links every board (the landing page dct serves at `/`). `dbt_charts.yml` holds only `sources:` (dct 0.8 rejects `serve:`, `theme:` and `style:` there). Extra or missing files are reported.
Severity: **Info**.

**Check 10 — Renders are clean.** `dct render <charts_dir>/<board>.yml --format png` for every board prints no `WARN-*` code other than `WARN-DBT-MODEL-COLUMNS-UNRESOLVED`. The codes this catches are what a reviewer would see first: truncated KPI labels, titles and series labels; money or percent fields with no `$`/`%` format; a mostly-null measure; a zero-row query; a one-point time axis. Skipped, and recorded as `unverified` with the reason, under `--no-warehouse` or `budget.warehouse_spend: none`, since renders run the queries.
Severity: **Major**. Report each code with board and chart.

**Check 11 — Design convention lint.** Resolve the convention as generate does (`.wire/conventions/dbtcharts.yml` in the engagement, else `wire/conventions/dbtcharts.yml`) and run `lint_conventions.py --domain dbtcharts --convention <file> --path <charts_dir>/` plus the anchor. Zero `error` findings (titles, labels and notes present; the anchor holds `sources:` only; no raw-string regex). Warnings are listed by rule id, not failed on. Record which convention file resolved.
Severity: **Major**. If the linter cannot run (no PyYAML), record `unverified`.

### Step 3: Write the validation report

`.wire/releases/<release>/dev/dbtcharts_validation_report.md`:

```
## dbt Charts Validation: [PROJECT_NAME]

**Boards:** N · **dct:** <version> · **Warehouse check:** PASS | FAIL | unverified (<reason>)

### Results
| # | Check | Severity | Result | Detail |
|---|---|---|---|---|
| 1 | dct validate (structure) | Critical | PASS / FAIL / unverified | errors by board; warnings by code |
| 2 | dct validate --warehouse | Critical | ... | |
| 3 | ref()-only queries | Major | ... | |
| 4 | No inline or external data | Critical | ... | |
| 5 | Labels, titles and notes | Major | ... | |
| 6 | Coverage and needs_human decisions | Major | ... | |
| 7 | No credentials in the anchor | Critical | ... | |
| 8 | Viz catalog mapping | Critical / n/a | ... | |
| 9 | One board per subject area, meta and index present | Info | ... | |
| 10 | Renders clean (dct render warnings) | Major | ... | codes by board and chart |
| 11 | Design convention lint | Major | ... | errors by rule id; warnings listed; convention file |

### Verdict
PASS | PASS WITH WARNINGS | FAIL
```

Verdict rule: any Critical failure is **FAIL**; `unverified` on a Critical check is **FAIL** unless the reason is a recorded budget setting, in which case the verdict is **PASS WITH WARNINGS** and the warehouse check stays `unverified` in `status.md`; Major failures alone are **PASS WITH WARNINGS**; Info never changes the verdict. A render warning is a Major failure because it names something the reviewer will see; clear it in the board rather than argue it.

### Step 4: Update Status

```yaml
dbtcharts:
  validate: pass | fail
  validated_date: "{{TODAY}}"
  validation_report: "dev/dbtcharts_validation_report.md"
  validation_verdict: "PASS | PASS WITH WARNINGS | FAIL"
  warehouse_validated: true | false | unverified
  render_warnings: N         # Check 10, excluding WARN-DBT-MODEL-COLUMNS-UNRESOLVED
  convention: "<resolved convention path>"
  convention_lint_errors: N  # Check 11
  checks_failed: []          # check numbers
```

`pass` covers PASS and PASS WITH WARNINGS; `fail` is FAIL.

### Step 5: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` with artifact `dbtcharts`, action `validate`, and the verdict.

## Edge Cases

### `dct` is not installed on this machine

Checks 1, 2 and 10 are `unverified`, the verdict is FAIL, and the report gives the install line (`uv tool install dbt-charts --with dbt-<adapter>`). Nothing else is guessed.

### The boards were edited by hand since generate

Expected: curation is hand editing. The checks run against the files as they are. If `scaffold_summary.json` names a board that no longer exists, Check 9 reports it and Check 6 checks the models it covered against the remaining boards.

## Output

The report file, the `status.md` update, and the verdict on screen, followed by:

```
Ran: /wire:dbtcharts-validate <release>
Next: /wire:dbtcharts-review <release>            # on PASS
      /wire:dbtcharts-generate <release> --force  # on FAIL, after fixing the cause
```
