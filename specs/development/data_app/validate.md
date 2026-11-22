---
wire_schema: "1.0"
command: validate
artifact: data_app
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: app
      description: "--app <slug>. Validate one app (default: every app in status.md)"
    - name: slice
      description: "--slice <slice>. In a release built from tickets, check one slice of the release only (specs/utils/ticket_delivery.md)"
produces:
  - type: report
    path: "dev/data_app/<slug>/validation.md"
    description: "Per-check PASS/FAIL table for the app: plan coverage, field resolution, rule lint, Google's verify stages, mockup cross-check"
preconditions:
  - artifact: data_app
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate a Looker Data App: every catalog row is a widget, every field resolves, no unmapped chart types, Wire's rules pass, Google's verify stages pass against Looker, titles and filters match the approved mockup"
argument-hint: <release-folder> [--app <slug>] [--slice <slice>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# data_app Validation Command

**Experimental.** See `data_app-generate` for the marker and what it means.

## Purpose

Check the app against the mockup chain the stakeholder approved and against the semantic layer, with Wire's rules and Google's own verification. Ground truth is the catalog, the spec and `fields.json`, not the app's own claims.

## Usage

```bash
/wire:data_app-validate 20260115_acme_dashboards
/wire:data_app-validate 20260115_acme_dashboards --app sales-overview
```

## Prerequisites

- `data_app.generate == complete` in `status.md`

## Sliced runs (`--slice`)

In a release built from tickets, `--slice <slice>` checks the one app the slice names. The slice must be in `tickets.yaml`. On a ticket branch, write `pass` or `fail` to the ticket record's front matter and the log row to the ticket run log, not to `status.md` and `execution_log.md`.

## Workflow

### Step 1: Verify the app exists

For each app in `status.md` `artifacts.data_app.apps` (or the one named by `--app`): the source file, `plan.json` and `fields.json` exist. If not:

```
Error: data_app not generated yet (missing <file>).

Run `/wire:data_app-generate <release>` first.
```

### Step 2: Run the checks

**Check 1: Target and toolkit.** `bi_tool` is `looker`; `python3 <wire>/scripts/data_app_toolkit.py check` finds the toolkit at or above the pinned version and a config file (values never read). If the toolkit is missing, Checks 8 and 9 record `unverified`, which is not a pass.
Severity: **Critical**.

**Check 2: Every catalog row produced a widget.**

```bash
python3 <wire>/scripts/data_app_plan.py check \
  --plan dev/data_app/<slug>/plan.json --app-js <source> --fields dev/data_app/<slug>/fields.json
```

`widgets_found` equals `widgets_expected`, with no `missing` and no `extra` ids. A missing widget is a Critical failure: the stakeholder approved a mockup with that visualization on it.
Severity: **Critical**. Report missing and extra widgets by id and title.

**Check 3: No unmapped chart types.** `plan.json` `counts.unmapped` is 0. Any row that fell through to the table fallback is listed with the `chart_type` the catalog gave.
Severity: **Critical**.

**Check 4: Every field resolves against the semantic layer.** `plan.json` `counts.unresolved_fields` is 0, and every `fields` literal the check script finds in `app.js` is in `fields.json`. A field that does not exist means the widget errors for the first person who opens the app.
Severity: **Critical**.

**Check 5: Model and explore are the ones recorded.** Every `looker-model` and `explore` literal (or `this.lookerModel` and `this.explore`) in `app.js` matches `semantic_layer_model` and `semantic_layer_explore` in `status.md`.
Severity: **Critical**.

**Check 6: Every spec filter is present.** Each filter under `## Filter Dimensions` in `dashboard_spec.md` is in the plan's filter list, resolved, and present in `app.js` as an `<app-select>` or listened to through `this.dashboardFilters` (the check script reports `filters_missing`). An app that does not spread `dashboardFilters` ignores Looker's own filter bar.
Severity: **Major**. Report missing filters and unresolved filter fields separately.

**Check 7: Wire's rules.**

```bash
python3 <wire>/scripts/lint_conventions.py --domain data_apps \
  --convention <.wire/conventions/data_apps.yml if present, else <wire>/conventions/data_apps.yml> \
  --path <data_apps_path>/<slug> --new-project --format json
```

No error. Warnings are listed with the disposition `data_app.md` recorded (`fixed`, `justified`, `acknowledged`); a warning with no disposition is reported.
Severity: **Critical** for an error, **Info** for a warning.

**Check 8: Google's verification, stages 1 to 3.** `python3 <wire>/scripts/data_app_toolkit.py verify --app <slug>` after a fresh `push`: syntax, tile safety and the query dry run against Looker all pass. The dry run is the only check here that reaches Looker; it catches a model that does not exist, a field Looker rejects (HTTP 422) and a query that returns nothing. If the toolkit cannot be run, record `unverified`.
Severity: **Critical**. `unverified` is not a pass.

**Check 9: The toolkit copy is the source.** `python3 <wire>/scripts/data_app_toolkit.py diff --app <slug> --source <data_apps_path>/<slug>` reports no difference other than the publish tags in the header. A toolkit copy that drifted from the repo means someone edited the working copy; the repo is the source of truth.
Severity: **Major**.

**Check 10: No literal data.** No widget carries `.data=${[...]}` rows or a `data="[...]"` attribute standing in for a query (rule DA-011). The same rule `semantic_layer-generate` applies to views applies here.
Severity: **Critical**.

**Check 11: Titles match the catalog.** Each widget's `title` or `label` is its catalog row's `visualization_name` (the check script's `title_mismatches`). Renaming a widget between mockup approval and delivery breaks the audit trail even when the numbers are right.
Severity: **Major**.

**Check 12: The published copy is this source.** Only when `looker_dashboard_id` is set in `status.md`: the source header's `@looker-dashboard-id` tag equals it, and `git log -1 --format=%cI -- <source>` is not later than `published_date`. A later commit means the source changed since the last publish, and the dashboard shows the old app until `/wire:data_app-publish` runs again.
Severity: **Info**.

### Step 3: Write the report

`dev/data_app/<slug>/validation.md`:

```
## Data App Validation: [PROJECT_NAME] · <slug> (experimental)

**Status:** PASS | FAIL
**Toolkit:** <version> (pinned <pin>)  ·  **Widgets checked:** N

| # | Check | Severity | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | Target and toolkit | Critical | PASS/FAIL | |
| 2 | Every catalog row produced a widget | Critical | PASS/FAIL | [N rows, N widgets; missing, extra] |
| 3 | No unmapped chart types | Critical | PASS/FAIL | [list] |
| 4 | Every field resolves | Critical | PASS/FAIL | [list] |
| 5 | Model and explore are the ones recorded | Critical | PASS/FAIL | |
| 6 | Every spec filter is present | Major | PASS/FAIL | [list] |
| 7 | Wire's rules | Critical | PASS/FAIL | [errors; warnings with disposition] |
| 8 | Google's verify, stages 1-3 | Critical | PASS/FAIL/unverified | [hint] |
| 9 | Toolkit copy is the source | Major | PASS/FAIL | |
| 10 | No literal data | Critical | PASS/FAIL | [list] |
| 11 | Titles match the catalog | Major | PASS/FAIL | [list] |
| 12 | Published copy matches the source | Info | PASS/note/n.a. | |

### Verdict

Any Critical failure is a FAIL. A Major failure is a FAIL unless waived in this report with a named reason. Info items never fail the check. `unverified` on Check 8 is a FAIL.

### Next Steps

1. [If FAIL] Fix the listed items and re-run /wire:data_app-validate <release>
2. [If PASS] Review with stakeholders: /wire:data_app-review <release>
```

### Step 4: Update status

```yaml
artifacts:
  data_app:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    apps:
      - slug: <slug>
        verify: pass | fail | unverified
        lint_errors: N
        lint_warnings: N
```

### Step 5: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md`: artifact `data_app`, action `validate`, status as written.

## Edge Cases

### The toolkit is not installed on this machine

Checks 8 and 9 are `unverified` and the verdict is FAIL. Say so plainly, with the install one-liner. A colleague with the toolkit can re-run validate; nothing else changes.

### Validation fails

Set `validate: fail`, list every item with its fix, and stop. The user fixes and re-validates. Do not edit the app from validate.

## Output

- `dev/data_app/<slug>/validation.md`
- `status.md` `artifacts.data_app.validate` and the per-app counts
- one row in `execution_log.md`
