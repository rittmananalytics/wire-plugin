---
sidebar_position: 16
title: "Tutorial: Looker Studio to Looker (experimental)"
---

# Tutorial: Looker Studio to Looker (experimental)

:::caution[Experimental]

The Looker Studio to Looker pair is experimental. Review every output before presenting it to a client, and read the [limitations](#limitations) first.

:::

This tutorial runs a `bi_migration` release with the `looker_studio_to_looker` pair. The client is a fictional retailer, Halcyon Outdoor, moving its Looker Studio reports to Looker on the same BigQuery warehouse. The first half of the release, the capture, the audit and the metric catalogue, is the same as in the [Looker Studio to Omni tutorial](./looker-studio-to-omni); this page covers what changes when the target is Looker.

## How this pair works

Looker Studio keeps no shared model: each report has its own data sources and formulas. So the capture reads each report from the editor, the metric catalogue rules one definition per metric, and the converter writes LookML from the result.

![Each source item and the LookML it becomes: tables to typed views with primary keys, joins to the model's explores, calculations to measures and dimensions, SQL to derived-table views, dashboards and pages to LookML dashboards, filters and controls to dashboard filters with listen; every step also writes needs_human.json for plan rulings and review, and the output passes lint, Looker's validator and parity in that order](/img/bi-migration/source-items-to-lookml.png)

| Step | Script | Output |
|---|---|---|
| Capture | `looker_studio_capture.py` | The editor's calls and each chart's data, in a git-ignored folder |
| Extract | `looker_studio_extract.py` | `report.json` per report |
| Audit and catalogue | `looker_studio_catalog.py`, `looker_studio_metrics.py` | Catalogs with a class per construct; the metric catalogue |
| Convert | `ls_to_lookml.py convert` | LookML views, explores and dashboards; `needs_human.json`; `parity_map.json` |
| Lint | `ls_to_lookml.py lint` | Fails on Looker Studio syntax left in the LookML or a field defined twice |
| Parity | `looker_studio_parity.py`, `bi_parity.py` | Each chart's recorded rows against the Looker element's |

## Three kinds of data source

| Data source | What the converter does |
|---|---|
| BigQuery table | A view on the table: dimensions from the columns, measures for the charts' aggregations, calculated fields translated to BigQuery SQL |
| BigQuery custom SQL | A view on the SQL, listed for a person (remodel or keep) |
| Looker Studio's Looker connector | No new LookML. Each field's formula names the Looker field (`t0.deals_fact.deal_closed_month`), so the charts point at the existing explore. The dashboard goes in `dashboards/<model>/`, and a person adds its include to that model |
| Search Console, GA4, Sheets, Funnel.io | Listed: a pipeline task in the plan, or a drop |

## Step 1: Create the release, capture and audit

| You say | Wire replies |
|---|---|
| "Start a BI migration release for Halcyon: Looker Studio to Looker. These two reports; Looker project halcyon_retail." | Asks for the target (Omni or Looker) and records `bi_pair: looker_studio_to_looker`, saying the pair is experimental. Asks who approved automated read-only access to the reports. |
| "Approved by the head of analytics today. Capture them." | Opens Chrome for the sign-in, captures both reports, extracts `report.json`, builds the catalogs and the metric catalogue. |

Ran: `new`, `looker-studio-audit-generate`, `metric-catalogue-generate`. The audit and the catalogue are validated and reviewed as in the Omni tutorial.

## Step 2: Convert

`lookml-model-generate` runs the converter on the reports in the batch and the ruled catalogue. Into a project that already has views, it writes to its own folder (`--include-root`) under a new model.

| Construct | What happens |
|---|---|
| A row-level calculated field (`margin / revenue`) | A dimension, `SAFE_DIVIDE(${margin}, ${revenue})`: Looker Studio's division returns null on zero, BigQuery's `/` raises an error |
| An aggregate calculated field (`SUM(revenue) / SUM(orders)`) | A `type: number` measure |
| Record Count | A `type: count` measure |
| A chart with a breakdown dimension | A pivot on the second dimension |
| A chart with its own date range ("start of the month 12 months back to today") | An element filter `13 months`; the chart does not listen to the dashboard's date filter |
| A text date field used as the date range | A date dimension group on `DATE(SAFE_CAST(col AS TIMESTAMP))`, as Looker Studio casts it |
| The date range control | A dashboard filter with `listen` on each chart's date field; its default is not in the capture, so a person sets it |
| A dimension filter control | A dashboard filter that every chart on its data source listens to |
| A blend | Listed: the plan rules the join keys and grain |

Ran: `lookml-model-generate`, `lookml-model-lint`, `lookml-model-validate`, then `looker-content-generate`.

## Step 3: Parity

The capture recorded what every chart showed. `bi-equivalency-validate` fills each recording's contract from `parity_map.json` (the element, and each recording column's Looker field), runs the element with the recorded date range, and compares the rows.

## What the live run found

In October 2026 the pair ran on two Rittman Analytics reports. "Monthly Snapshot Report" reads Looker through Looker Studio's Looker connector; "Example Report" reads two BigQuery tables and a custom SQL query.

| Report | Charts | Result |
|---|---|---|
| Monthly Snapshot Report (Looker connector) | 7 | 6 identical. Invoices by month: 12 of 13 months identical; the current month differs, because the chart's range ends today and Looker's nearest filter takes in invoices dated later this month. Deals by month and company: Looker Studio drew the top 15 companies; Looker's rows for those 15 are the same 37, with the same values |
| Example Report (BigQuery table and custom SQL) | 4 of 5 | All 4 identical (scorecards, cost of delivery by month in the same order, sessions by channel). The fifth chart is on a blend and was listed, not converted |

The run found faults in the Looker Studio scripts the Omni pair shares, fixed for both pairs:
- the extractor missed custom SQL, which the editor now sends beside the BigQuery configuration;
- the extractor did not read the Looker connector's model and explore, or a chart's own date range;
- the chart recordings treated Record Count, and measures from the Looker connector, as key columns.

Looker's validator also warned that a dashboard on the existing `analytics` model was included by the new model: such dashboards now go in a folder of their own.

## Limitations

| Limitation | Effect | What to do |
|---|---|---|
| Experimental | Outputs are drafts | Review them before presenting them to a client |
| Undocumented endpoints | As for the Omni pair: the capture reads the editor's internal calls | See the [Looker Studio to Omni limitations](./looker-studio-to-omni#limitations) |
| Blends | Not converted | Rule the join in the plan |
| Unreachable connectors | Search Console, GA4, Sheets and community connectors are not converted | A pipeline task, or drop |
| Date range control default | Not in the capture | Set it by hand; the recordings show the range at capture time |
| Ranges ending today | Looker's nearest filter also takes in the rest of the current month ("to now" generates SQL BigQuery rejects) | Accept the difference, or add a date filter |
| Breakdown charts | Looker Studio draws only its top series; Looker draws every series | Set a series limit or a filter |
| Unknown codes and functions | Data type, aggregation and date codes not yet seen, and functions outside the map, are listed | Each is a needs-human item |

## See also

- [BI Tool Migration](../release-types/bi-migration#migrating-to-looker)
- [A session at the terminal: Tableau, Metabase and Looker Studio to Looker](./bi-to-looker-session)
- Pair files: `bi_pairs/looker_studio_to_looker/`; the capture side: `bi_pairs/looker_studio_to_omni/`
