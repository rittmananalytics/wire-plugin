---
wire_schema: "1.0"
command: validate
artifact: looker_studio_audit
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
    path: "audit/looker_studio_audit.md"
    description: "Validation section appended to the audit with a per-check PASS/FAIL table"
preconditions:
  - artifact: looker_studio_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate the Looker Studio audit: every report captured and extracted, every component and data source classified, gaps and access requests listed, captures git-ignored, no secrets committed, counts match status.md"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Studio Audit: Validate

## Purpose

> **Experimental.** The `looker_studio_to_omni` pair is experimental in 4.2.2. It reads undocumented Looker Studio endpoints and has not yet been run end to end into Omni on a client estate. The same steps serve `looker_studio_to_looker` (experimental), which has run end to end once into Looker on two reports, not on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Checks the Looker Studio audit for completeness and safety before the metric catalogue and the plan are built on it. Produces a PASS/FAIL report with the gaps to fix.

## Prerequisites

- `audit/looker_studio_audit.md` exists (looker_studio_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/content_catalog.csv` and `datasource_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/reports/*/report.json`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/captures/*/meta.json` (local only)
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read the report, both catalogs and every `report.json`. Confirm both CSVs parse with exactly the columns `looker_studio_catalog.py` writes, in order.

### Step 2: Run validation checks

**Check 1: Every report in scope was captured and extracted**
Every URL in `bi_migration.looker_studio_reports` has a `report.json` whose `report.id` matches, or is listed in the audit as failed with a cause.
PASS/FAIL with the missing reports.

**Check 2: Extraction is reproducible**
For one report, re-run `looker_studio_extract.py` on its capture into a temporary folder and compare `report.json` byte for byte. Skip with a note if the captures are not on this machine.
PASS/FAIL/SKIPPED.

**Check 3: Every component and data source has a class**
Every `component` row has `translation_class` in `mechanical`, `assisted`, `redesign`, `drop`; every data source row in `map`, `assisted`, `pipeline`, `blocked`; every non-`mechanical` row has a `reason`.
PASS/FAIL.

**Check 4: Coverage gaps are reported**
Every data source with class `blocked`, every page in `coverage.pages_failed`, and every data source in `coverage.datasources_without_fields` appears in the audit's Coverage gaps section; every `blocked` data source and every billing project Route A could not read appears under Access requests.
PASS/FAIL.

**Check 5: Pipeline needs are listed**
Every `pipeline` data source appears under Pipeline needs with what would have to land in the warehouse.
PASS/FAIL.

**Check 6: Usage is real or unknown**
Component rows carry `jobs` and `last_run` from Route A, or the literal `unknown` with `usage_source: unavailable`. No other source of usage is used.
PASS/FAIL.

**Check 7: Captures are not tracked and secrets are not committed**
`git check-ignore` reports the captures folder as ignored. No tracked file under the release folder contains a value from a connector setting the extractor redacted (search tracked files for each `report.json` param shown as `<redacted>` in its capture). `looker_studio_capture_consent` is recorded.
PASS/FAIL.

**Check 8: Counts match status.md**
`report_count`, `page_count`, `hidden_page_count`, `component_count`, `datasource_count`, `datasources_blocked`, `datasources_pipeline`, `chart_recordings` equal the catalog and report counts.
PASS/FAIL with the mismatches.

### Step 3: Write validation report

Append a `## Validation` section to `audit/looker_studio_audit.md` with a per-check table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  looker_studio_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:looker-studio-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:looker-studio-audit-validate $ARGUMENTS
```

## Output Files

- Updated `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md` (Validation section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact_id, `Looker Studio Audit` as artifact_name, and the `file` value from `artifacts.looker_studio_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_studio_audit` as artifact, `validate` as action.
