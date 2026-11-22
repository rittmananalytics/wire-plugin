---
wire_schema: "1.0"
command: generate
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
mcp_contextual:
  - bigquery
produces:
  - type: document
    path: "audit/looker_studio_audit.md"
    description: "Looker Studio estate audit: reports, pages, components, data sources, blends and calculated fields, each with a translation class, plus coverage gaps and access requests"
  - type: report
    path: "audit/looker_studio/content_catalog.csv"
    description: "One row per report, page, component and blend with translation_class, grid position and usage"
  - type: report
    path: "audit/looker_studio/datasource_catalog.csv"
    description: "One row per data source with connector, location, access and translation_class"
  - type: report
    path: "audit/looker_studio/reports/<report_id>/report.json"
    description: "Extracted report definition per report (looker_studio_extract.py)"
preconditions: []
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Experimental: Capture and catalog the Looker Studio estate (report definitions, layout, data sources, calculated fields, chart data and BigQuery job history) and classify every component and data source for the move to Omni"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: looker_studio_audit` and `artifact_file_path: audit/looker_studio_audit.md` before proceeding.

---

# Looker Studio Audit: Generate

## Purpose

> **Experimental.** The `looker_studio_to_omni` pair is experimental in 4.2.2. It reads undocumented Looker Studio endpoints and has not yet been run end to end into Omni on a client estate. The same steps serve `looker_studio_to_looker` (experimental), which has run end to end once into Looker on two reports, not on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Catalogs the client's Looker Studio (formerly Data Studio) reports so the metric catalogue and the migration plan can decide what moves to Omni and how. Looker Studio has no supported API for report definitions, so the audit reads them from the editor itself through three evidence routes:

| Route | What it gives | Source | Access needed |
|---|---|---|---|
| B | Report definition: pages, layout, components, fields, chart-level formulas, filters, blends, parameters; each data source's connection and calculated fields | Looker Studio editor calls (`getReport`, `getSchema`, `getBlockDatasource`), recorded in a headed Chrome session | View on each report; Edit on each data source |
| C | Each chart's query specification and the values it displayed, for every connector, plus the BigQuery job link for BigQuery charts | Looker Studio chart data calls (`batchedDataV2`), recorded on the same page visits | View on each report |
| A | The SQL each BigQuery chart ran, and usage over the last 180 days | `INFORMATION_SCHEMA.JOBS` in the billing project, jobs labelled `looker_studio_report_id` | BigQuery Resource Viewer on the billing project |

Routes B and C use undocumented endpoints that Google can change without notice. Route A is supported and is the fallback for SQL and usage. Every script is deterministic and makes no AI call; the agent runs them, reads their output and writes the audit report. It never hand-writes what a script emits.

This is a **BI-tool** audit. It does not change the warehouse, and it changes nothing in Looker Studio: the capture script navigates only and never clicks, types or saves.

## Prerequisites

- Release folder with `project_type: bi_migration` and `bi_pair: looker_studio_to_omni` or `looker_studio_to_looker` in `status.md`
- `bi_migration.looker_studio_reports`: the report URLs in scope, one per line
- `bi_migration.looker_studio_namespace`: a short client slug used in object identities (`lookerstudio:<namespace>:...`)
- `bi_migration.looker_studio_capture_consent`: who approved automated read-only access to the reports, and when. Required before the first capture. Routes B and C use the consultant's own Google sign-in to read the editor's internal calls; the client must agree to that in writing
- Python 3.10 or later with Playwright (`python3 -m pip install playwright`) and Google Chrome, on the consultant's machine
- Access as listed above. Without Edit on a data source, its connection and formulas are not readable; the audit records the gap and continues

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- The reports listed in `bi_migration.looker_studio_reports`
- `wire/bi_pairs/looker_studio_to_omni/translation_guide.md` (classes and normalisation rules)
- `wire/bi_pairs/looker_studio_to_omni/feature_detection.md` (what each response field means)
- `wire/bi_pairs/looker_studio_to_omni/tooling.md` (setup, access requests, data handling)
- `.wire/engagement/bi_pair_overrides/looker_studio_to_omni/` (optional engagement overrides)

## Workflow

### Step 1: Locate the release and check the gates

Confirm `project_type: bi_migration` and `bi_pair: looker_studio_to_omni` or `looker_studio_to_looker` (the audit is the same for both targets; where this spec says Omni, read Looker for `looker_studio_to_looker`). Read the report list and the namespace. If `looker_studio_capture_consent` is empty, stop and output:

```
Looker Studio capture needs recorded client consent for automated, read-only access
to the reports with your own Google account. Record it in status.md as
bi_migration.looker_studio_capture_consent (approved_by, date), then re-run:
/wire:looker-studio-audit-generate $ARGUMENTS
```

Make sure `.wire/releases/*/audit/looker_studio/captures/` is in the repository's `.gitignore`; add the line if it is missing. Captures hold chart values and can hold credentials stored in connector settings, so they are never committed. The capture script refuses to write into a tracked folder.

If `audit/looker_studio_audit.md` already exists, ask whether to re-generate (overwrite) or update (re-capture only the reports named).

### Step 2: Capture (Routes B and C)

Run, from the repository root:

```bash
python3 <plugin-root>/scripts/looker_studio_capture.py \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio/captures \
  --screenshots <report_url> [<report_url> ...]
```

The first run opens Chrome on a separate profile under `~/.wire/looker_studio/` and waits up to 5 minutes for the consultant to sign in. Tell the consultant to sign in with the account that has the access listed above, and that the window will move between pages and data sources on its own. Later runs reuse the profile.

The script visits every page (hidden pages included) so every data source's field list is requested, then opens each data source's editor. It writes `meta.json` per report with the capture time, the Looker Studio app version, the revision read (published or draft), the pages that failed to open and the data sources visited. A report that returns no definition is reported as `FAILED` and the script exits non-zero; record the failure and the likely cause (no access, wrong account) and continue with the others.

### Step 3: Extract each report

```bash
python3 <plugin-root>/scripts/looker_studio_extract.py \
  --capture .wire/releases/$ARGUMENTS/audit/looker_studio/captures/<report_id> \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>
```

Writes `report.json` and `report.md`. The extractor redacts connector settings whose names look like secrets (password, token, API key) and keeps every unconfirmed enum code as a raw number. If it stops with `ERROR`, the capture's structure is not one it knows (an endpoint changed): record the app version from `meta.json`, stop, and raise it as a blocking issue. Do not hand-edit `report.json`.

### Step 4: Record chart data (Route C)

```bash
python3 <plugin-root>/scripts/looker_studio_parity.py \
  --capture .wire/releases/$ARGUMENTS/audit/looker_studio/captures/<report_id> \
  --report .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json \
  --out .wire/releases/$ARGUMENTS/migration/parity/looker_studio/<report_id> \
  --namespace <looker_studio_namespace>
```

Writes one folder per chart result (`source.csv`, optional `compare.csv` and `totals.csv`, `contract.yaml`) and `recordings.json`. These are the expected results `bi-equivalency-validate` compares Omni against. They hold aggregated values as users saw them on the dashboards; if the engagement's data handling rules do not allow those in the repository, add the folder to `.gitignore` and record that in `status.md` as `bi_migration.chart_recordings_tracked: false`.

### Step 5: Read BigQuery job history (Route A, when access allows)

`recordings.json` names the billing project and location of every BigQuery chart's job. For each distinct pair:

```bash
python3 <plugin-root>/scripts/looker_studio_jobs.py fetch --billing-project <project> --location <location> \
  --report-id <report_id> --out .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>
python3 <plugin-root>/scripts/looker_studio_jobs.py link \
  --jobs .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>/jobs_raw.json \
  --report .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>
```

If `fetch` fails for lack of `bigquery.jobs.listAll`, record the billing project under "Access requests" and continue: usage is then `unknown` for that report. Never infer usage from anything else.

### Step 6: Build the catalogs

```bash
python3 <plugin-root>/scripts/looker_studio_catalog.py \
  --reports .wire/releases/$ARGUMENTS/audit/looker_studio/reports/*/report.json \
  --chart-sql .wire/releases/$ARGUMENTS/audit/looker_studio/jobs/*/chart_sql.json \
  --namespace <looker_studio_namespace> \
  --out .wire/releases/$ARGUMENTS/audit/looker_studio
```

Writes `content_catalog.csv` and `datasource_catalog.csv`. The classes are the rule in `translation_guide.md`, applied by the script:

| Data source class | Meaning |
|---|---|
| `map` | BigQuery table or view; the Omni model can read the same table |
| `assisted` | BigQuery custom SQL (read from `connectorConfig.sql`); becomes a dbt model or a view on the SQL |
| `map` (Looker connector) | A Looker Studio data source on Looker's Looker connector: `report.json` records the instance, model and explore; the charts read an existing Looker model |
| `pipeline` | Community connector, Google product connector or Sheets; no known warehouse copy, so the plan raises a pipeline task |
| `blocked` | Definition not read (Edit refused, or not captured) |

| Component class | Meaning |
|---|---|
| `mechanical` | Supported chart type, no chart-level formula, no comparison period, not on a blend |
| `assisted` | Needs a decision: chart-level formula, comparison period, blend, combo or bullet chart, or a control |
| `redesign` | No Omni equivalent (community visualisations and other types) |
| `drop` | Decorative shapes and images; text boxes (recreated by hand) |

### Step 7: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md`

Include:
- Capture record: per report, the capture time, app version, revision read (published or draft, and whether unpublished changes exist), pages that failed to open
- Summary table: reports, pages (visible and hidden), components by kind, report-level components, blends, parameters, filters, data sources by connector, data-source and chart-level calculated fields
- Classification breakdown: components and data sources by class
- Report families: reports whose visible page names match are copies of one template (for example one per client); list each family. The plan merges a family into one Omni template with filters
- Data source register: every data source with connector, location (project, dataset, table, or the connector and its non-secret settings), class, and which reports and blends use it
- Pipeline needs: every `pipeline` data source, with what would have to land in the warehouse
- Blends: inputs, join type (named only where confirmed) and keys
- Usage: from Route A, components and data sources by last run; `unknown` where Route A did not run
- Coverage gaps: refused and uncaptured data sources, data sources without a field list, pages that failed, charts with no recording
- Access requests: a ready-to-send list naming each missing permission and the object it is for (Edit on data source X; BigQuery Resource Viewer on billing project Y)

### Step 8: Update status

```yaml
artifacts:
  looker_studio_audit:
    generate: complete
    file: audit/looker_studio_audit.md
    generated_date: "{{TODAY}}"
    report_count: N
    page_count: N
    hidden_page_count: N
    component_count: N
    datasource_count: N
    datasources_blocked: N
    datasources_pipeline: N
    chart_recordings: N
    usage_source: bigquery_jobs | partial | unavailable
    app_versions: [<from meta.json>]
    generated_files:
      - audit/looker_studio_audit.md
      - audit/looker_studio/content_catalog.csv
      - audit/looker_studio/datasource_catalog.csv
```

### Step 9: Output summary

Print the totals, the class breakdown, the access requests, and the next command:

```
/wire:looker-studio-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/content_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/datasource_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json` and `report.md`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/jobs/<report_id>/chart_sql.json` (when Route A ran)
- `.wire/releases/$ARGUMENTS/migration/parity/looker_studio/<report_id>/` (Route C recordings)
- `.wire/releases/$ARGUMENTS/audit/looker_studio/captures/` (git-ignored, never committed)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact_id, `Looker Studio Audit` as artifact_name, and the `file` value from `artifacts.looker_studio_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_studio_audit` as artifact, `generate` as action.
