---
sidebar_position: 19
title: "Tutorial: dbt Charts Boards"
---

# Tutorial: dbt Charts Boards

This tutorial builds a set of [dbt Charts](https://dbtcharts.com) dashboards over a warehouse with the three `dbtcharts` commands, changes the house style through a convention override, and then publishes the boards to dbt Charts Cloud so people outside the terminal can open them. It follows a fictional `dbt_development` release; the commands, files and checks are the real ones.

:::note
dbt Charts Cloud (dbtcharts.com) is not dbt Labs' dbt Cloud (getdbt.com). The boards run locally with no account; Cloud is only for hosting them.
:::

## Statement of Work

```
**Rittman Analytics × Norbury Coffee Roasters Ltd**
**Engagement**: `02-norbury-dashboards`
**Date**: September 2026
**Type**: Fixed price

### Engagement overview

Norbury's dbt project on BigQuery already has a warehouse layer of 14 models in
three folders: `w_sales` (orders, order lines, customers, products), `w_finance`
(invoices, payments, chart of accounts) and `w_ops` (roasting batches, deliveries,
sites). Nobody outside the data team can see the numbers. Norbury wants one
dashboard per area, kept in the dbt repository next to the models and reviewed
through pull requests like everything else, and a hosted copy the operations
manager can open on a phone.

### In scope

- One dbt Charts board per warehouse folder, plus a landing page
- Norbury's house style: pounds, a light theme, the company logo on the landing page
- Boards validated against BigQuery and rendered for review
- The boards published to dbt Charts Cloud with read access for the operations group

### Out of scope

- New dbt models. The boards read what exists; a gap in the data goes back to the dbt backlog.
- Scheduled refresh. Cloud refresh is manual; a refresh schedule is a later request.
```

## Before you start

The release already has its dbt work done: `dbt` is at `validate: pass` in `.wire/releases/02-norbury-dashboards/status.md`. That is the only artifact `dbtcharts` depends on, and the precondition gate checks it before generate runs.

Install the dct CLI with the BigQuery adapter inside its own tool environment, since the warehouse checks need it:

```bash
uv tool install dbt-charts --with dbt-bigquery
dct --version
```

On an Apple-silicon Mac add `--python cpython-3.12-macos-aarch64-none` to the install line; uv otherwise picks an Intel Python when an Intel Homebrew is on the path, and the `cryptography` package then fails to build.

## How the artifact works

Three commands, in order, each gated on the one before:

| Command | What it does | Gate |
|---|---|---|
| `/wire:dbtcharts-generate <release> [--auto]` | Compiles the project, runs a deterministic scaffold that inventories every fact in each warehouse folder plus the dimensions it joins to, then designs each board into a dashboard | `dbt` validate PASS |
| `/wire:dbtcharts-validate <release>` | Eleven checks: dct structure, BigQuery dry run, `ref()` only, no inline data, labels and notes, coverage, no credentials, viz-catalog mapping, project files, renders clean, convention lint | `dbtcharts` generate complete |
| `/wire:dbtcharts-review <release>` | Shows the renders and the generation report, records approval or change requests | `dbtcharts` validate PASS |

How a board looks is not decided in the commands. It comes from a **convention**, `conventions/dbtcharts.yml`, that ships with Wire and that an engagement overrides by placing its own copy at `.wire/conventions/dbtcharts.yml`. Step 2 below does that.

## Step 1: Generate the boards as Wire ships them

Run generate in auto mode. Auto means one design lane per subject area, all at once, with no pauses; every choice is written to the generation report instead of being asked.

```
/wire:dbtcharts-generate 02-norbury-dashboards --auto
```

The command says what it is about to do before it does it:

```
dbt Charts boards: 3 subject areas under models/warehouse

| Subject area | Models | Facts | Dimensions | Linked dimensions |
|---|---|---|---|---|
| w_sales   | 4 | 2 | 2 | 0 |
| w_finance | 3 | 2 | 1 | wh_customers_dim (ref() in wh_invoices_fact) |
| w_ops     | 3 | 2 | 1 | wh_sites_dim (site_fk in wh_deliveries_fact) |

Convention: wire/conventions/dbtcharts.yml (framework default; no engagement override found)
Catalog: dbt docs generate will run (warehouse_spend not restricted)
```

Two things in that table are worth noticing. The finance board will carry `wh_customers_dim` even though it lives in `w_sales`, because the invoices fact refs it. A subject area's board covers the facts in its folder plus the dimensions those facts join to, wherever they live. And the convention that resolved is the framework default, since Norbury has not overridden it yet.

Then, in order: `dbt compile` (dct reads model columns from compiled SQL, so `dbt parse` is not enough), `dbt docs generate` for column types, the scaffold, three design lanes, validation, renders, and the report. On a live warehouse this takes ten to fifteen minutes; each render runs the board's queries.

The report closes with:

```
## dbt Charts boards generated

**dct:**        0.8.0 · dialect bigquery · source warehouse (profile norbury, target prod)
**Boards:**     3 written under charts/ (one per subject area), 0 skipped (existing)

| Subject area | Models | Charts proposed | Charts kept | needs_human |
|---|---|---|---|---|
| w_sales   | 4 | 14 | 10 | 0 |
| w_finance | 4 | 12 |  9 | 1 |
| w_ops     | 4 | 11 |  9 | 1 |

### Design (auto)
37 charts scaffolded, 6 kept, 18 reshaped, 13 dropped, 4 added, 2 needs_human items decided (1 sent back to dbt)

### Validation
Structure: PASS · Warehouse dry-run: PASS · Renders: 4 PNGs under dev/dbtcharts/, 0 render warnings

⚠ This artifact's validate step runs dct validate --warehouse against BigQuery and does not run automatically.
Run /wire:dbtcharts-validate 02-norbury-dashboards before requesting review.

Ran: /wire:dbtcharts-generate 02-norbury-dashboards --auto
Next: /wire:dbtcharts-validate 02-norbury-dashboards
```

What landed in the repository:

```
charts/
  meta.yml          # theme: vivid, frame width 1440 (from the convention)
  index.yml         # the landing page dct serves at /
  sales.yml
  finance.yml
  ops.yml
  scaffold_summary.json
  needs_human.json
dbt_charts.yml      # sources: only; already existed, left alone
.wire/releases/02-norbury-dashboards/dev/dbtcharts_generation_report.md
.wire/releases/02-norbury-dashboards/dev/dbtcharts/{index,sales,finance,ops}.png
```

Open the generation report before anything else. The curation table shows what the scaffold proposed and what each lane did with it, row by row: `wh_order_lines_fact_records` dropped ("a record count of line items tells nothing; the orders KPI covers volume"), `wh_orders_fact_trend` reshaped ("one measure, last 24 months, stacked by channel"), a `kpis` query added with prior-period deltas. The `needs_human` table records that `wh_roasting_batches_fact` has no date column and was sent back to the dbt backlog rather than charted without a trend.

Walk the boards live:

```bash
dct serve      # prints http://localhost:<port>; the landing page is at /
```

Each board opens with a KPI row comparing the last 12 months to the 12 before, then a 24-month trend, two or three ranked breakdowns and a detail table. Amounts show as `$`, which is the point of the next step.

## Step 2: Override the house style

Norbury bills in pounds, wants the lighter `paper` theme, and wants its logo on the landing page. Those are convention values, so copy the framework convention into the engagement and change them. The whole file is read, so the copy must be complete; the plugin's copy is the starting point:

```bash
mkdir -p .wire/conventions
cp ~/.claude/plugins/cache/rittman-analytics/wire/<version>/conventions/dbtcharts.yml .wire/conventions/dbtcharts.yml
```

Then edit the `presentation` section:

```yaml
presentation:
  theme: paper                    # was vivid
  frame_width: 1440
  currency: "£"                   # was "$"
  landing_page:
    enabled: true
    title: Norbury Coffee Roasters              # was null (the dbt project name)
    logo: docs/images/norbury_logo.svg          # was null; path relative to the dbt project root
    cards_per_row: 3
```

Nothing else needs to change for this engagement, but the same file holds the other knobs: `windows.trend_months` (24), `board_shape.kpis` (4 to 6), `chart_defaults.ranking.limit` (10), `chart_defaults.table.limit` (15), the layout row splits, and the naming and layout rules the linter checks.

Two things follow from `currency: "£"`. dct's currency presets print `$` and its axis tick formats accept no other symbol, so KPIs and table columns take a `£` prefix format and chart axes show plain compact numbers with "GBP" named in the subtitle. The generate command applies that automatically; it is written into the convention's `formats.money_other` section.

Regenerate. The boards were designed once already, so `--force` is needed to rewrite them, and this is the moment to use it: nothing has been hand-edited yet.

```
/wire:dbtcharts-generate 02-norbury-dashboards --auto --force
```

The opening table now reads `Convention: .wire/conventions/dbtcharts.yml (engagement override)`, and `charts/meta.yml` comes out as:

```yaml
theme: paper
style:
  frame:
    width: 1440
```

The landing page carries the heading "Norbury Coffee Roasters" with the logo top-right, embedded as a data URI because dct serves no static files. The finance board's invoiced KPI reads `£1.2M`; its axis reads `1.2 M` under a subtitle "GBP, last 24 months".

One-off changes go on the command line instead and override the convention for that run only: `--theme clarity`, `--currency '€'`, `--title "..."`, `--logo <path>`. The report records which values came from a flag.

## Step 3: Validate

```
/wire:dbtcharts-validate 02-norbury-dashboards
```

```
## dbt Charts Validation: Norbury Coffee Roasters

**Boards:** 3 · **dct:** 0.8.0 · **Warehouse check:** PASS

| # | Check | Severity | Result | Detail |
|---|---|---|---|---|
| 1 | dct validate (structure) | Critical | PASS | 5 × WARN-DBT-MODEL-COLUMNS-UNRESOLVED (select * models) |
| 2 | dct validate --warehouse | Critical | PASS | 21 queries dry-run, 0 errors |
| 3 | ref()-only queries | Major | PASS | |
| 4 | No inline or external data | Critical | PASS | |
| 5 | Labels, titles and notes | Major | PASS | |
| 6 | Coverage and needs_human decisions | Major | PASS | 2 of 2 decided |
| 7 | No credentials in the anchor | Critical | PASS | |
| 8 | Viz catalog mapping | n/a | n/a | no catalog on a dbt_development release |
| 9 | One board per subject area, meta and index present | Info | PASS | |
| 10 | Renders clean (dct render warnings) | Major | PASS | 0 warnings across 4 renders |
| 11 | Design convention lint | Major | PASS | .wire/conventions/dbtcharts.yml; 0 errors, 1 warning (kpi_label_max_words on ops.kpi_avg_delivery_days) |

### Verdict
PASS

Ran: /wire:dbtcharts-validate 02-norbury-dashboards
Next: /wire:dbtcharts-review 02-norbury-dashboards
```

The unresolved-columns warning in Check 1 is expected: those models end in `SELECT *`, so dct cannot list their columns without the warehouse, and Check 2 is what verifies them. The convention lint warning in Check 11 names a five-word KPI label; a warning does not fail validate, but it is one edit in `charts/ops.yml` and the next run is clean.

## Step 4: Review

```
/wire:dbtcharts-review 02-norbury-dashboards
```

Review presents the four PNGs under `dev/dbtcharts/`, the curation table and the `needs_human` decisions, then asks for the outcome. Norbury's operations manager approves the sales and ops boards and asks for one change to finance: the aged-receivables chart should bucket by 30, 60 and 90 days rather than the scaffold's status column. That is recorded as a change request against `charts/finance.yml`, chart `receivables_chart`.

Change requests are applied by editing the board YAML, never by regenerating: `--force` would discard the curation. Edit the query, then:

```bash
dct validate charts/finance.yml --warehouse
dct render charts/finance.yml --output .wire/releases/02-norbury-dashboards/dev/dbtcharts/finance.png
```

Run validate and review again; the second review records `approved`, with the reviewer's name, in `status.md`. Commit the boards with the models:

```
/wire:utils-commit 02-norbury-dashboards
```

## Step 5: Publish to dbt Charts Cloud

Everything so far ran on a laptop. Cloud hosts the same files from the Git repository with a warehouse connection, so the operations manager opens a URL instead of running `dct serve`. The steps below are the dbt Charts Cloud setup sequence, run from the terminal; `dct skills cloud-setup` carries the same sequence for an agent to follow, and every step has a matching screen on dbtcharts.com.

**Prerequisites.** The repository must be on GitHub (public or private; Cloud connects through its GitHub App and supports no other host), with at least one commit pushed, and BigQuery must be reachable from the internet. Cloud connection types are BigQuery, PostgreSQL, Redshift and Snowflake; a `duckdb` or `sqlite` source is local only.

**1. Sign in.** The login is a browser approval; signing in and signing up happen on the same page.

```bash
URL=$(dct cloud login --start)   # open the URL it prints and approve
dct cloud login --wait           # blocks until the approval lands, prints "Logged in"
dct cloud orgs                   # the consent screen leaves at least one organisation
```

**2. Connect the repository.** The Cloud repo picker offers only repositories you administer. For a private repo:

```bash
URL=$(dct cloud project connect --org norbury --start)   # open the URL, install the GitHub App, pick the repo
dct cloud project connect --wait                          # prints "Connected"
```

A public repo connects without the browser hop: `dct cloud project connect --org norbury --git-url https://github.com/norbury/dbt`. A successful connect writes `published_to: "https://<host>/norbury/<project>/"` into `dbt_charts.yml`; commit it. Cloud tracks two branches from here: the upstream branch (`main`), which it never commits to, and a work branch (`dbt-charts/<project>`) where edits made in the Cloud editor land as real commits for your normal merge process.

**3. Grant the warehouse role.** Cloud needs a BigQuery service account with `roles/bigquery.jobUser` on the project and `roles/bigquery.dataViewer` on each dataset the boards read. Mint the key into a temporary file and delete it after the next step; never paste a key on the command line.

```bash
gcloud iam service-accounts create dbt-charts-ro --project norbury-data
gcloud projects add-iam-policy-binding norbury-data \
  --member "serviceAccount:dbt-charts-ro@norbury-data.iam.gserviceaccount.com" \
  --role roles/bigquery.jobUser --condition=None
# grant roles/bigquery.dataViewer on the analytics dataset, then:
gcloud iam service-accounts keys create /tmp/dbt-charts-ro.json \
  --iam-account dbt-charts-ro@norbury-data.iam.gserviceaccount.com
```

**4. Create the connection and map the source.** The create call also tests the credential; a failed test saves nothing and prints BigQuery's own error.

```bash
dct cloud connection create --org norbury --type bigquery \
  --keyfile /tmp/dbt-charts-ro.json --set project=norbury-data --set dataset=analytics
rm /tmp/dbt-charts-ro.json
dct cloud source map warehouse norbury-data --org norbury --project dbt
```

`warehouse` is the source name every board declares (`source: warehouse`) and the key under `sources:` in `dbt_charts.yml`; `norbury-data` is the connection slug, which defaults to the BigQuery project. Cloud never reads credential fields from the committed `dbt_charts.yml`; the mapped connection supplies them.

**5. Publish and check.** Mapping re-renders the boards on its own. A push to `main` syncs within seconds through the GitHub App; `dct cloud project sync` publishes immediately.

```bash
dct cloud status --org norbury      # reports the first incomplete stage, or done
dct cloud project sync --org norbury --project dbt
dct cloud boards --org norbury --project dbt   # RENDERED_AT and COMMIT change once a push is live
```

`dct cloud status` walks the stages in order: `missing_project`, `unsynced`, `untested_connection`, `unmapped_sources`, `missing_boards`, `unrendered_boards`, then `done`. Whatever it names is the next thing to fix.

**6. Give the operations group access.** Organisation membership does not grant dashboard visibility; access is an explicit, path-based grant. Invite members (invitations expire after seven days), then grant the Viewer role on the project or on the `ops` board alone. Editors can also refresh, and refresh in Cloud is manual: a dashboard re-runs its queries when someone with that grant asks it to, from the toolbar.

```bash
dct cloud member invite ops.manager@norbury.co.uk --org norbury --role viewer
```

Record the published URL in the release:

```yaml
dbtcharts:
  published_url: "https://dbtcharts.com/norbury/dbt/"
```

The landing page at that URL is the same `charts/index.yml` the laptop served: the Norbury heading, the logo, three cards. Each board shows the commit it was rendered from, and every edit anyone makes in the Cloud editor arrives as a commit on the work branch for a pull request, so the dashboards keep the review path the models have.

## What this tutorial showed

- The three-command sequence, gated on `dbt` validate PASS: generate (`--auto` for every area at once), validate (eleven checks), review.
- A subject-area board covers the facts in its folder plus the dimensions they join to, wherever those live.
- House style is a convention, overridden per engagement at `.wire/conventions/dbtcharts.yml`: theme, currency, landing-page title and logo, windows, board shape, chart defaults and the rules the linter checks.
- `--force` regenerates and discards curation; after review, change requests are edits to the YAML.
- Publishing to dbt Charts Cloud is a CLI sequence: login, connect the GitHub repo, grant the BigQuery roles, create the connection, map the source, sync, grant access.

## See also

- [dbt Charts Boards](../advanced/dbt-charts) for the artifact's design, the convention's sections and the dct 0.8 notes
- [Business rules](../advanced/business-rules) for where the measure names the boards should use come from
- [dbt Development](./dbt-development) for the release type this tutorial's engagement runs under
