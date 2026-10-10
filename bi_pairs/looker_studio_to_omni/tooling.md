# Looker Studio to Omni: tooling

## Setup on the consultant's machine

| Need | How |
|---|---|
| Python 3.10 or later | |
| Playwright | `python3 -m pip install playwright` |
| Google Chrome | The capture uses the installed Chrome (`channel="chrome"`), not a bundled browser |
| `bq` CLI, signed in | Route A only: `gcloud auth login` |

The capture opens Chrome on its own profile under `~/.wire/looker_studio/profile`. Sign in once with the Google account that has access to the reports; later runs reuse it. To switch account, delete that folder.

## Access to request

Send this to the report owner, per report:

| For | Request |
|---|---|
| Report definition and layout | View on the report |
| Data source connection and formulas | Edit on every data source the report uses, from each data source's own Share menu (Resource, Manage added data sources). Edit on the report does not grant it |
| Per-chart SQL and usage | BigQuery Resource Viewer on each billing project the data sources use. The billing project is in Route C's `recordings.json` once the report is captured |
| Parity runs | BigQuery Data Viewer on the datasets, and BigQuery Job User on one project to run queries from |
| Community connector and Google product sources | Read access to the warehouse copy of that data (for example the Funnel.io or GA4 BigQuery export) |

Route C needs only View on the report: the expected values can be recorded before any other access is granted.

## Consent and terms of use

Routes B and C read the Looker Studio editor's internal calls with the consultant's own sign-in. They are read-only and navigate only. Before the first capture on a client's reports, record the client's written agreement in `status.md` as `bi_migration.looker_studio_capture_consent` (who approved, date). The audit refuses to run without it.

## Data handling

| Output | Holds | Where | In git |
|---|---|---|---|
| Captures | Raw responses, including chart values and any credential stored in connector settings | `audit/looker_studio/captures/` | Never. Git-ignored; the capture script refuses a tracked folder |
| `report.json`, `report.md` | Definitions; secret settings redacted | `audit/looker_studio/reports/` | Yes |
| Route C recordings | Aggregated values as shown on the dashboards | `migration/parity/looker_studio/` | Yes, unless `chart_recordings_tracked: false` |
| `jobs_raw.json` | SQL text and user emails from job history | `audit/looker_studio/jobs/` | Engagement's choice; ignore it if user emails must not be stored |

## Scripts

```bash
# Routes B and C
python3 scripts/looker_studio_capture.py --out <captures> --screenshots <report_url> [...]
# Extract one report
python3 scripts/looker_studio_extract.py --capture <captures>/<id> --out <reports>/<id>
# Route C contracts
python3 scripts/looker_studio_parity.py --capture <captures>/<id> --report <reports>/<id>/report.json --out <parity>/<id> --namespace <slug>
# Route A
python3 scripts/looker_studio_jobs.py fetch --billing-project <p> --location <loc> --report-id <id> --out <jobs>/<id>
python3 scripts/looker_studio_jobs.py link --jobs <jobs>/<id>/jobs_raw.json --report <reports>/<id>/report.json --out <jobs>/<id>
# Catalogs and metric catalogue
python3 scripts/looker_studio_catalog.py --reports <reports>/*/report.json --chart-sql <jobs>/*/chart_sql.json --namespace <slug> --out <audit>/looker_studio
python3 scripts/looker_studio_metrics.py --reports <reports>/*/report.json --out <audit>
```

## Known behaviour of the editor

| Behaviour | Handling |
|---|---|
| `lookerstudio.google.com` redirects to `datastudio.google.com` with content type `application/binary`, which Chrome treats as a download | The capture navigates to `datastudio.google.com` directly |
| A few page URLs still come back as downloads | The capture retries in a new tab and lists failed pages in `meta.json`; the report definition is unaffected |
| `getSchema` only fires for data sources on opened pages | The capture opens every page; the extractor falls back to `getBlockDatasource` fields |
| Published reports keep their pages in `publishedReportRevision` | The extractor reads it and records `revision: published` and `unpublished_changes` |

## Limitations

- Routes B and C use undocumented endpoints. Google can change them without notice. Each capture records the app version; the extractor fails loudly on structure it does not know.
- The capture needs an interactive Google sign-in and a desktop session. It cannot run unattended or in CI.
- Route A covers BigQuery only, charts that ran in the last 180 days, and not results served from Looker Studio's cache.
- Route C values reflect the data at capture time and the date range in force then. Parity runs Omni over the same fixed dates.
- There is no deterministic Looker Studio to Omni converter. The Omni model and dashboards are written by the agent from the warehouse model and the ruled catalogue, and are checked by `omni-model-lint`, `omni-model-validate`, `omni-content-validate` and parity.
- Not yet seen in a real capture, so handled generically and kept raw: parameters, BigQuery custom SQL data sources (detected by SQL text), extracted data sources, community visualisations, populated report-level parameter values.
- `migration-drift-generate` has no source repository to diff for this pair; drift is a re-capture and a comparison of `report.json`.
- Scheduled email deliveries are not captured; ask report owners for them before cutover.
- A brownfield Omni target audit (`omni_audit`) is not part of this profile's graph in 4.2.2.
