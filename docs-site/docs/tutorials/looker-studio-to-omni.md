---
sidebar_position: 13
title: "Tutorial: Looker Studio to Omni (experimental)"
---

# Tutorial: Looker Studio to Omni (experimental)

:::caution[Experimental]

The Looker Studio to Omni pair is experimental. It reads undocumented Looker Studio endpoints, which Google can change without notice. Capture, extraction, cataloguing and the metric catalogue have been run on real client reports. The model, dashboard and parity steps have been tested on synthetic fixtures only and have not yet been run end to end into Omni on a client estate. Review every output before presenting it to a client, and read the [limitations](#limitations) first.

:::

This tutorial runs a `bi_migration` release with the `looker_studio_to_omni` pair, added in Wire 4.2.2. The client is a fictional marketing agency, Larkspur Media, that reports to its own clients through Looker Studio. It shows what Wire captures from Looker Studio, how the metric catalogue turns many report-level definitions into one agreed set, how the plan decides where the Omni model comes from, and how parity works when Looker Studio has no query API. The [limitations](#limitations) are at the end.

The release is directed in prose, as in the [Looker to Omni tutorial](./looker-to-omni-migration). At each step we name the command Wire runs. Everything can also be typed.

## Why this pair is different

Looker has a semantic model (LookML) that Wire converts with a script. Looker Studio has none. Each report has its own data sources, each data source has its own calculated fields, and each chart can add more. In the reports this pair was tested on, three reports held 1,886 calculated field definitions; 105 metric names had more than one formula, and CTR, CPC, CVR and ROAS each had at least three.

So the pair does not convert reports one for one. It:

1. **Captures** each report's definition from the Looker Studio editor, since there is no supported API for it.
2. **Builds a metric catalogue** and asks the client to rule on one definition per metric.
3. **Builds the Omni model from the warehouse**, using existing modelled tables or a linked dbt release, with one measure per ruled metric.
4. **Proves parity** against the values each Looker Studio chart showed when it was captured.

## Statement of work

```
Rittman Analytics x Larkspur Media
Engagement: Looker Studio to Omni
Type: Fixed price

Larkspur Media runs paid media and SEO for 14 clients. Each client has a copy of the
"Client Performance V2" Looker Studio report (20 to 45 pages each), reading BigQuery
tables loaded by Funnel.io, plus GA4 and a budgets Google Sheet. Larkspur is moving
client reporting to Omni.

In scope
- Audit of the 14 reports and their data sources
- Metric catalogue and definition rulings with Larkspur's head of analytics
- Omni model built from the BigQuery warehouse, one dashboard template with a client
  filter in place of 14 copies
- Parity for every visible page, against the values the reports showed at capture
- 30-day parallel run, then Looker Studio reports set to view-only
```

## Before you start

| Need | How |
|---|---|
| Python 3.10 or later, Playwright, Google Chrome | `python3 -m pip install playwright` on the consultant's machine |
| View on each report | From the report owner |
| Edit on each data source | From each data source's Share menu. Edit on the report is not enough |
| BigQuery Resource Viewer on the billing projects | Optional at first; Wire tells you which projects after the first capture |
| Client consent | Written agreement to automated, read-only access to the reports with your Google account |

## Step 1: Create the release

| You say | Wire replies |
|---|---|
| "Start a BI migration release for Larkspur: Looker Studio to Omni. These are the 14 report links. Their head of analytics approved read-only automated access on 2 October." | Creates the release with `bi_pair: looker_studio_to_omni`, the report list, the client slug `larkspur` and the consent record. The Looker audit phase is switched off for this pair; the Looker Studio audit and the metric catalogue are switched on. |

Ran: `new`.

## Step 2: Capture and audit

| You say | Wire replies |
|---|---|
| "Audit the reports." | "A Chrome window will open. Sign in with the account that has access to the reports; the window then moves between pages and data sources on its own and changes nothing." |

Wire runs `looker-studio-audit-generate`, which runs six scripts in turn:

| Script | What it did for one report |
|---|---|
| `looker_studio_capture.py` | Opened 21 pages and 13 data source editors; recorded the definitions and 107 chart data responses; saved a screenshot per page |
| `looker_studio_extract.py` | Wrote `report.json`: 21 pages (8 hidden), 1,014 components, 13 data sources, 26 chart-level formulas, 1 blend |
| `looker_studio_parity.py` | Wrote 107 chart recordings, each with the rows the chart showed and a parity contract; 102 linked to their BigQuery job |
| `looker_studio_jobs.py` | Read job history from the billing project named in those links; skipped where access was missing |
| `looker_studio_catalog.py` | Classified every component and data source |
| `looker_studio_metrics.py` | (run in the next step) |

The audit report lists, for the 14 reports:

- **Report families.** All 14 share the same visible page names, so they are one family: one template, copied per client and filtered by a client ID.
- **Data sources by class.** `map` (BigQuery tables), `pipeline` (6 Funnel.io connectors, a Snowflake connector with its own SQL, a budgets Sheet: no warehouse copy known), `blocked` (4 with Edit access refused).
- **Access requests.** Ready to send: Edit on the 4 refused data sources; Resource Viewer on one billing project.

The raw captures stay in a git-ignored folder, because they hold chart values and, in one case, a Funnel API key stored in a connector's settings. `report.json` shows that key as `<redacted>`.

| You say | Wire replies |
|---|---|
| "The Funnel data also lands in BigQuery, in `funnel_export`. Hidden pages are retired. Approve the audit." | Records the warehouse copy for the Funnel sources, marks hidden pages out of scope, and records the review. |

Ran: `looker-studio-audit-generate`, `looker-studio-audit-validate`, `looker-studio-audit-review`.

## Step 3: The metric catalogue

Wire runs `metric-catalogue-generate`. The script groups every calculated field by name, after normalising the formulas (namespaces removed, case and spacing made consistent, `IFNULL(x, 0)` inside `SUM` treated as `x`):

| Class | Example | Count |
|---|---|---|
| Same definition, copied | `Row CPC` in 9 data sources, one formula | 247 groups |
| Same shape, different fields | CPC as `SUM(_cost_)/SUM(_clicks_)` and `SUM(cost)/SUM(link_clicks)` | 12 groups |
| Conflict | CTR as clicks over impressions, and as link clicks over reach times 100 | 30 groups |
| Finding: sum of ratio | A "CPC (Display)" scorecard adding up per-row CPC values | 5 charts |

Wire proposes a ruling for each group and parks each conflict as a decision for the client.

| You say | Wire replies |
|---|---|
| "Go through the conflicts with me." | Shows each conflict with its formulas, where each is used, and the proposal. For CTR: "Paid search and paid social use different denominators. Proposal: two measures, `search_ctr` (clicks over impressions) and `social_ctr` (link clicks over reach)." |
| "Agreed for CTR. For ROAS use platform revenue over cost everywhere. Fix the sum-of-ratio scorecards." | Records each ruling in `decisions.md`, fills the catalogue's `ruling`, `canonical_formula` and `target_name` columns, and notes that the five corrected scorecards will show different numbers. |

Ran: `metric-catalogue-generate`, `metric-catalogue-validate`, `metric-catalogue-review`.

## Step 4: The plan and the model route

Wire runs `bi-migration-plan-generate`. For this pair the plan decides, per subject area, where the Omni model comes from:

| Subject area | Model route | Why |
|---|---|---|
| Web analytics (GA4 tables) | map | Modelled warehouse tables exist; the ruled metrics can be written over them |
| Paid media (Funnel export tables) | build | One wide table per channel template, with a column per source and metric; needs reshaping into one table with a channel column |
| Budgets (Google Sheet) | pipeline task | No warehouse copy; load into a managed table first |

For the `build` route the plan spawns a linked `dbt_development` release, scoped to paid media, with the metric catalogue as its business rules. The Omni model batch for paid media waits for that release's models to pass validation. The plan also rules that the 14 copied reports become one Omni dashboard with a client filter.

Ran: `bi-migration-plan-generate`, `bi-migration-plan-validate`, `bi-migration-plan-review`, `release-spawn`.

## Step 5: Model, content and parity

These phases use the same commands as the Looker pair, with these differences:

- **Model.** `omni-model-generate` writes the Omni views and topics from the warehouse tables, with one measure per ruled metric (for example `search_ctr` as total clicks over total impressions). There is no converter, so every file goes through `omni-model-lint` and `omni-model-validate`.
- **Content.** `omni-content-generate` builds the dashboard from `report.json`: pages become tabs, components land on a 24-column grid scaled from their pixel positions, text boxes become text items, shapes are dropped, and report-level components appear once. Each tile's metric uses the measure named by the catalogue.
- **Parity.** `bi-equivalency-validate` runs each Omni tile over the same fixed dates and time zone as its recording, and compares the rows with the values the Looker Studio chart showed, using the standard comparator. The five corrected scorecards are accepted differences, citing the ruling. Charts on the budgets Sheet are `BLOCKED` until the pipeline task lands the data.

If a tile fails because data arrived after the capture, Wire re-captures that report and runs the check again before investigating.

## Step 6: Cutover

`cutover` runs as for the Looker pair: a parallel run, then Looker Studio reports set to view-only and links redirected. The capture does not read Looker Studio's scheduled email deliveries, so ask each report owner for theirs and recreate them in Omni.

## Limitations

| Limitation | Effect | What to do |
|---|---|---|
| The pair is experimental | Not yet run end to end into Omni on a client estate | Treat outputs as drafts for consultant review; report problems on wire#278 |
| Routes B and C read undocumented Looker Studio endpoints | Google can change them without notice; a capture or extraction then fails | Each capture records the app version; the extractor stops on structure it does not know. Route A (BigQuery job history) is supported and remains for SQL and usage |
| The capture needs an interactive Google sign-in in a desktop Chrome window | It cannot run unattended or in CI | Run it during the audit, on the consultant's machine |
| Client consent is required | The audit refuses to capture without a recorded approval | Record `looker_studio_capture_consent` in the status file |
| Edit access is needed on every data source | Without it, connections and data source formulas are missing and the data source is `blocked` | Send the access list the audit writes, then re-capture |
| Route A covers BigQuery only, the last 180 days, and not cached results | No SQL or usage for other connectors; some charts show no jobs | Usage is recorded as `unknown`, never guessed; Route C still gives expected values |
| Recorded values reflect the data at capture time | Late-arriving data can cause a parity failure that is not a logic error | Re-capture and re-run; recorded as a vintage difference when that resolves it |
| No deterministic Looker Studio to Omni converter | The Omni model and dashboards are agent-written | Every file is linted and validated, and every tile goes through parity |
| Data with no warehouse copy (community connectors, GA4 or Ads direct, Sheets) | Omni cannot query it | The plan raises a pipeline task; affected charts are `BLOCKED` until it closes |
| Not seen in a real capture when 4.2.2 shipped: parameters, custom SQL data sources, extracted data sources, community visualisations | Handled generically and kept raw; custom SQL is detected by its SQL text | Check these by hand in the audit review the first time they appear |
| Enum codes are only named when confirmed | Most aggregation and join codes appear as numbers | `bi_pairs/looker_studio_to_omni/property_mapping.md` lists what is confirmed |
| Drift | There is no source repository to diff | Re-capture and compare each report's `report.json` and modified date |
| Scheduled email deliveries are not captured | Schedules are not in the audit | Ask report owners for their schedules and recreate them at cutover |
| Brownfield Omni target | `omni_audit` is not in this pair's graph in 4.2.2 | Review existing Omni content by hand before the plan |
| Captures hold sensitive data | Chart values, and any credential stored in a connector's settings | Captures are git-ignored and the script refuses a tracked folder; `report.json` redacts secret settings |

## See also

- [BI Tool Migration](../release-types/bi-migration)
- [Tutorial: Looker to Omni Migration](./looker-to-omni-migration)
- Pair files: `bi_pairs/looker_studio_to_omni/` (translation guide, property mapping, feature detection, content mapping, tooling, worked examples)
