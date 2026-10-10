---
sidebar_position: 13
title: "A session at the terminal: Tableau, Metabase and Looker Studio to Looker"
---

# A session at the terminal: Tableau, Metabase and Looker Studio to Looker

:::caution[Experimental]

The three pairs used here (`tableau_to_looker`, `metabase_to_looker`, `looker_studio_to_looker`) are experimental.

:::

This page follows one working session in Claude Code, as the release director sees it at the terminal. The client is fictional: Halcyon Outdoor, a retailer with a BigQuery warehouse and three reporting tools it wants to retire in favour of the Looker instance it already has. Finance uses Tableau Cloud, marketing uses Metabase, and the leadership team reads Looker Studio reports. The counts, findings and behaviour shown are the kind the three pairs produced on their live test runs (October 2026); the estate itself is invented.

The director never types a command. They say what they want, rule on what Wire cannot decide, and approve at the gates. Wire runs the real commands, and each turn ends with the commands it ran.

![Tableau, Metabase and Looker Studio feed per-tool snapshot and audit scripts; Wire's shared core holds the tool-neutral record, the migration plan, the metric catalogue and the shared Looker target; three converters write LookML to a branch of the client's repo, deployed to Looker under its own model; the parity loop compares each source's rows with Looker's results before cutover](/img/bi-migration/migration-to-looker-architecture.png)

## Before the session

Three things are done once, outside Claude Code.

**Secrets.** Each tool's credential goes in a file under `~/.wire/` that only the director's account can read, never in the repo:

```text
$ ls -l ~/.wire/*.env
-rw-------  tableau.env     TABLEAU_PAT_NAME, TABLEAU_PAT_SECRET  (token creation switched on under Settings, General)
-rw-------  metabase.env    MB_HOST, MB_API_KEY                   (an API key in the Administrators group)
```

Looker Studio has no API for report definitions: its capture opens Chrome and the director signs in when asked.

**Metabase sync.** Metabase must have synced the tables its questions read. The BigQuery connection is narrowed to the `analytics` dataset, so the first sync finishes in minutes, not hours.

**The repos.** An empty engagement repo, `halcyon-bi-to-looker`, with Claude Code open in it and the Wire plugin installed. The LookML project is `halcyon_looker` on GitHub; the Looker connection to the warehouse is `halcyon_bq`.

## Turn 1: three releases, one target

```text
❯ Halcyon is moving all its reporting to Looker. Three sources: Tableau Cloud (site halcyon, the Finance
  project), Metabase at halcyon.metabaseapp.com (the Marketing collection), and the three Looker Studio
  exec reports in this list. Same BigQuery warehouse throughout; the LookML project is halcyon_looker.

● One release has one source tool, so I'll open three releases under this engagement, all writing to
  halcyon_looker. Each pair is experimental.

  .wire/releases/02-tableau-to-looker/        bi_pair: tableau_to_looker
  .wire/releases/03-metabase-to-looker/       bi_pair: metabase_to_looker
  .wire/releases/04-looker-studio-to-looker/  bi_pair: looker_studio_to_looker

  halcyon_looker already has 212 views, so each release writes to its own folder under its own model:
  tableau_migration/, metabase_migration/, looker_studio_migration/. Your existing models are not touched.

  One thing I need before the Looker Studio capture: who approved automated read-only access to the
  three reports, and when?

❯ The CFO approved it this morning.

● Recorded in 04-looker-studio-to-looker/status.md (looker_studio_capture_consent).

  Ran: new (x3)
```

## Turn 2: the audits

```text
❯ Run the audits.

● Tableau: signed in with the token, snapshot of the Finance project.
    6 workbooks, 41 sheets, 9 dashboards, 11 data sources (4 published)
    data source fingerprints: 7 embedded copies collapse into 3 groups
    redesign: 2 LOD expressions, 1 table calculation, 1 extract-only data source
    file sources: 1 workbook reads an Excel file, not the warehouse

  Metabase: snapshot of the Marketing collection through the API.
    23 questions (17 query builder, 6 native SQL), 2 models, 3 metrics, 4 dashboards (one with 3 tabs)
    every query-builder table synced; primary keys from metadata on 9 of 11 tables
    not converted: 2 questions binned by "number of bins", 1 multi-stage question

  Looker Studio: opening Chrome. Sign in when the window asks.

❯ Done.

● Captured 3 reports (14 pages). The data sources are of three kinds:
    BigQuery tables              8   become LookML views
    BigQuery custom SQL          2   become views on their SQL
    Looker Studio's Looker
      connector                  3   the charts already read Looker: they point at the existing explores
    Search Console, GA4          2   Looker cannot query them: listed for the plan
  Metric catalogue: 211 calculated fields in 64 groups; 9 metrics are defined two or more ways
  (conversion rate three ways).

  The three audit reports are written and validated. Every construct has a class; the needs-human
  lists are in each release's audit/needs_human.json.

  Ran: tableau-audit-generate, -validate; metabase-source-audit-generate, -validate;
       looker-studio-audit-generate, -validate; metric-catalogue-generate, -validate
```

![The audit's six steps (connect, snapshot, classify, write the report, validate, review), the files each writes in the repo, secrets kept in ~/.wire outside it, and the metric catalogue and chart recordings that only Looker Studio adds](/img/bi-migration/source-audit-steps.png)

## Turn 3: rulings

Wire stops here, because what remains are decisions, not mechanics.

```text
❯ What do you need from me?

● Eleven rulings across the three releases. The ones that change numbers first:

  R-1  Metabase "Weekly signups by channel" and 5 other native SQL questions: views on their SQL are
       exact but not reusable. I lifted the 2 simple ones onto the sessions view as a proposal.
       Remodel onto shared views, or keep?
  R-2  Tableau "Customer lifetime value" is a FIXED LOD expression. Derived table, or drop?
  R-3  Looker Studio "Conversion rate": three definitions (orders/sessions, orders/users,
       purchases/sessions). Which one is the company's?
  R-4  Looker Studio blend "Orders and sessions" (full outer join, no keys recorded): model the join
       on date and channel, or drop the 2 charts on it?
  R-5  Tableau "Regional targets" reads an Excel file: load it to the warehouse, or drop?
  ...

❯ R-1 keep the 4 complex ones as views for now; take the lifted fields. R-2 derived table. R-3
  orders over sessions. R-4 join on date and channel. R-5 load it as a dbt seed. Accept your
  proposals for the rest.

● Recorded R-1 to R-11 in the three plans and in the metric catalogue review. The plans are ready
  for your approval.

❯ Approved.

  Ran: tableau-audit-review, metabase-source-audit-review, looker-studio-audit-review,
       metric-catalogue-review, bi-migration-plan-generate (x3), bi-migration-plan-review (x3)
```

## Turn 4: LookML on a branch

![Each source item and the LookML it becomes: tables to typed views with primary keys, joins to the model's explores, calculations to measures and dimensions, SQL to derived-table views, dashboards and pages to LookML dashboards, filters and controls to dashboard filters with listen; every step also writes needs_human.json for plan rulings and review, and the output passes lint, Looker's validator and parity in that order](/img/bi-migration/source-items-to-lookml.png)

```text
❯ Build it.

● Branch wire/bi-to-looker in halcyon_looker. Converting:

  Tableau        9 views, 6 explores, 9 dashboards; 3 primary keys proposed from *_pk columns;
                 the LOD as a derived table under hand/ (R-2)
  Metabase       11 views, 8 explores, 6 dashboards (one per tab); joins from Metabase's foreign keys;
                 3 metrics as measures with their filters; 4 views on native SQL (R-1)
  Looker Studio  8 views from BigQuery tables, 2 on custom SQL; "Conversion rate" as SAFE_DIVIDE of
                 orders over sessions (R-3); 14 dashboards. The 4 pages whose charts read the existing
                 analytics model are in dashboards/analytics/: add one include line to that model to
                 show them.

  Lint: 1 problem.
    metabase_migration/views/sessions.view.lkml: field session_start_ts_month is defined twice
  A field lifted from SQL took a name the session_start_ts date group already generates. Renamed it
  session_start_ts_month_from_sql, re-ran: 0 problems.

  Pushed. Validate it in development mode, merge, and configure the three new models with halcyon_bq.

  Ran: looker-target-setup-generate (x3), lookml-model-generate (x3), lookml-model-lint (x3),
       looker-content-generate (x3)
```

The director opens Looker, switches to the branch, runs Validate LookML, merges, deploys, and configures the three models under Admin, Projects.

```text
❯ Deployed, models configured.

● Looker's validator and one query per explore: all 22 explores run.

  Ran: lookml-model-validate (x3), looker-content-validate (x3)
```

## Turn 5: parity

```text
❯ Prove it.

● Each source's rows for each tile, against the Looker element's rows, through the same comparator:

  Source                         Tiles   PASS   accepted difference   FAIL
  Tableau (Query View Data)         41     40                     0      1
  Metabase (card data)              31     31                     0      0
  Looker Studio (recordings)        58     55                     3      0

  Tableau FAIL: "Margin by region" differs on every row. The Tableau calculation was a sum of
  row-level ratios (Tableau sums a row-level field by default); the converter emitted it that way and
  listed it. Sum of ratios or ratio of sums?

  Looker Studio accepted differences, for your approval:
    2 tiles  the chart's range ends today; Looker's nearest filter also counts rows dated later this
             month (forward-dated invoices). Same values for every closed month.
    1 tile   a breakdown chart: Looker Studio drew its top 15 series, Looker draws all 47. The 15 it
             drew match Looker's rows exactly.

❯ Ratio of sums: that was always the intent. Accept the three differences.

● Changed "Margin by region" to a ratio of sums under hand/; re-ran it against Tableau with the old
  number shown beside it, which the finance team should see before cutover. Recorded the three
  accepted differences with you as approver.

  All 130 tiles satisfy the cutover gate.

  Ran: bi-equivalency-validate (x3)
```

## Turn 6: cutover

```text
❯ Plan the cutover. Two weeks of parallel running for finance, one for the others.

● Cutover plans written: Tableau and Metabase in parallel run until 24 and 17 October, Looker Studio
  reports retired after one week. Drift checks are scheduled daily against the pinned snapshots: a
  workbook, question or report edited during the parallel run comes back to you, with the tiles it
  affects.

  Ran: cutover-generate (x3), migration-drift-generate (x3, scheduled)
```

## What the director did, and what Wire did

| The director | Wire |
|---|---|
| Stored three credentials outside the repo, and signed in to Google once | Took three snapshots, extracted 3 reports, classified every construct |
| Made 11 rulings, approved 3 plans and 3 accepted differences | Wrote three LookML batches deterministically, fixed what lint caught, kept rulings in the record |
| Validated, merged and deployed in Looker | Ran 22 explore checks and 130 tile comparisons |
| Approved cutover | Scheduled drift checks for the parallel run |

## See also

- [BI Tool Migration: migrating to Looker](../release-types/bi-migration#migrating-to-looker)
- [Tutorial: Tableau to Looker](./tableau-to-looker), [Tutorial: Metabase to Looker](./metabase-to-looker), [Tutorial: Looker Studio to Looker](./looker-studio-to-looker)
- [The Release Director Model](../advanced/release-director)
