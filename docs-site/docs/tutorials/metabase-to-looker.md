---
sidebar_position: 15
title: "Tutorial: Metabase to Looker (experimental)"
---

# Tutorial: Metabase to Looker (experimental)

:::caution[Experimental]

The Metabase to Looker pair is experimental. It has run end to end once, on a Metabase Cloud trial instance: four questions on BigQuery, two in native SQL and two built in the query builder, were converted, deployed to Looker and matched row for row. It has not run on a client estate. Review every output before presenting it to a client, and read the [limitations](#limitations) first.

:::

This tutorial runs a `bi_migration` release with the `metabase_to_looker` pair. The client is a fictional retailer, Halcyon Outdoor, moving its Metabase dashboards to Looker on the same BigQuery warehouse. It shows how Wire takes a snapshot of a Metabase instance, what converts to LookML and what needs a person, and how parity works with Metabase as the source.

The release is directed in prose, as in the [Looker to Omni tutorial](./looker-to-omni-migration). At each step we name the command Wire runs.

## How this pair works

Metabase keeps typed metadata for every table it has synced: each field's type, and its primary and foreign keys. Questions built in the query builder refer to fields by id. So the converter knows which column each question reads, which LookML view it belongs to and how the tables join. Native SQL questions carry no such structure; they become views on their own SQL.

![Each source item and the LookML it becomes: tables to typed views with primary keys, joins to the model's explores, calculations to measures and dimensions, SQL to derived-table views, dashboards and pages to LookML dashboards, filters and controls to dashboard filters with listen; every step also writes needs_human.json for plan rulings and review, and the output passes lint, Looker's validator and parity in that order](/img/bi-migration/source-items-to-lookml.png)

| Step | Script | Output |
|---|---|---|
| Snapshot | `metabase_export.py api` | Questions, models, metrics, dashboards, the metadata of every table they read, the SQL Metabase compiles for each query-builder question, view counts |
| Audit | `mb_to_lookml.py audit` | Catalogs with a class per construct, the tool-neutral IR, `needs_human.json` |
| Convert | `mb_to_lookml.py convert` | LookML views, explores, measures and LookML dashboards; `needs_human.json` |
| Lint | `mb_to_lookml.py lint` | Fails if Metabase syntax is left in the LookML or a view defines a field twice |

All four are deterministic and make no AI call.

## Before you start

| Need | How |
|---|---|
| A Metabase API key | Admin settings, Authentication, API keys, in a group that can see the content and its databases. Keep it in a file outside the repository that only you can read, such as `~/.wire/metabase.env` |
| `requests` and, optionally, `sqlglot` | `python3 -m pip install requests sqlglot` |
| The databases synced in Metabase | A table with no synced fields cannot convert. A dataset filter on the connection shortens the first sync |
| The client's LookML repo and Looker API access | For the target |

## Step 1: Create the release

| You say | Wire replies |
|---|---|
| "Start a BI migration release for Halcyon: Metabase to Looker. Instance halcyon.metabaseapp.com, Looker project halcyon_retail." | Creates the release with `bi_pair: metabase_to_looker` and says the pair is experimental. The Looker-to-Omni phases are switched off; the Metabase source audit, Looker target, LookML model and Looker content phases are switched on. |

Ran: `new`.

## Step 2: Snapshot and audit

Wire runs `metabase-source-audit-generate`. On the fixture instance the audit finds:

| Construct | Class | What happens |
|---|---|---|
| Tables (4), with primary and foreign keys | mechanical | One view per table, typed and keyed from the metadata |
| A metric (Revenue, excluding cancelled orders) | mechanical | A measure that keeps its filter |
| A question reading a field through a foreign key | mechanical | An explore join from the metadata, `many_to_one` |
| A ratio of two aggregations | mechanical | A `type: number` measure with `NULLIF` |
| A bin by width, a custom column, a second-stage filter | assisted | A `FLOOR` dimension, a SQL dimension, an element filter |
| A saved model, two native SQL questions | assisted | Views on their SQL; template tags become a parameter and a templated filter; the simple question is also lifted onto the table's view |
| A bin by number of bins, a snippet | redesign | Not converted |
| Two dashboard tabs, a link card, a date-grouping filter | assisted, drop, drop | Two LookML dashboards; the others listed |
| An archived question | drop | Not migrated |

| You say | Wire replies |
|---|---|
| "Approve the audit. Keep the model as a view for now; remodel the two SQL questions onto the orders view." | Records the review and the SQL rulings for the plan. |

Ran: `metabase-source-audit-generate`, `metabase-source-audit-validate`, `metabase-source-audit-review`.

## Step 3: The plan

`bi-migration-plan-generate` adds the pair's rulings: remodel or keep for each native question and model, keep or remove for each lifted field, and a ruling for each question not converted. Model batches are Metabase databases, because one LookML model has one connection; content batches are dashboards by view count.

## Step 4: Target, model and content

- `looker-target-setup-generate` checks the Looker connection reaches the databases the content reads, and creates the migration branch, folders and groups. It never merges.
- `lookml-model-generate` runs the converter for a database and resolves its needs-human items from the rulings. Most client LookML projects already have views, often with the same names, so Wire converts with `--include-root <folder>` and a model name not in use: the output stays in its own folder and the existing models are untouched. A Looker admin configures the new model. `lookml-model-lint` fails on any Metabase syntax left and on a field defined twice; `lookml-model-validate` runs Looker's validator and a query per explore.
- `looker-content-generate` commits the LookML dashboards. Metabase's 24-column grid maps one to one to Looker's newspaper layout; each tab becomes a dashboard; dashboard filters keep their field mappings through `listen`.

## Step 5: Parity and cutover

`bi-equivalency-validate` takes each Metabase question's rows through the API (`metabase_export.py card-data`, run as the question runs on its dashboard) and the Looker element's rows through the Looker API, then compares them with the standard comparator. Metabase returns a date bucket as a timestamp (`2026-10-01T00:00:00Z`) where Looker returns `2026-10`, so contracts declare the grain. `migration-drift-generate` compares a fresh snapshot with the pinned one.

## What the live run found

In October 2026 the pair ran against a Metabase Cloud trial instance (Metabase 1.64) with a BigQuery database: one dashboard of two native SQL questions, and one of two questions built in the query builder (sessions by month for the previous 12 months; bounce rate by channel for the last 12 months including this one, with a Channel filter). The LookML was deployed to Looker as its own model and each tile queried through the Looker API.

| Tile | Rows | Result |
|---|---|---|
| Sessions by Month (native SQL) | 12 | `PASS`, same order |
| Bounced Session Rate by Channel (native SQL) | 7 | `PASS`, same order |
| Sessions by month (query builder) | 12 | `PASS`, same order |
| Bounce rate by channel (query builder) | 8 | `PASS`, same order |

The run confirmed the relative date translation both ways: "previous 12 months" is `12 months ago for 12 months` (October 2025 to September 2026), and "the last 11 months including this one" is `12 months`. Looker's validator caught one fault the fixtures had missed: a field lifted from SQL took the name `session_start_ts_month`, which the `session_start_ts` date group already generates. The converter now avoids every generated name, and lint fails on a field defined twice.

## Limitations

| Limitation | Effect | What to do |
|---|---|---|
| Experimental | Run end to end once on a Metabase Cloud trial: four BigQuery questions. Not on a client estate, another warehouse, large dashboards, or Metabase before version 50 | Treat outputs as drafts for review |
| Native SQL and models | Views on their SQL: exact, not reusable. The lift covers simple single-table SQL, never its `WHERE` clause | Rule remodel or keep per question in the plan |
| Not converted | Binning by number of bins, multi-stage questions (other than a filter on an aggregation or a grouping column), share, offset, snippets, segments, custom columns over two tables | Each is a needs-human item with the reason |
| Unsynced tables | No metadata, so no conversion | Sync first; narrow the connection to the datasets in scope |
| Primary keys | Metabase infers them only where the warehouse declares them or a column is named `id`; BigQuery declares none | Set keys on joined views in the model review |
| Dashboard features | Date-grouping filters, click behaviour, link, iframe and action cards are not migrated; text cards cannot show filter values | Listed for hand finishing |
| Filters on one field | A tile filter and a dashboard filter on the same field: Metabase applies both, Looker's dashboard filter replaces the tile's | Listed per tile |
| Field filters in native SQL | Written table-qualified, as Metabase writes them | SQL that aliases that table needs a hand fix |
| Out of scope | Permissions, sandboxing, subscriptions, alerts, embedding | Handled by hand |

## See also

- [BI Tool Migration](../release-types/bi-migration#migrating-to-looker)
- [A session at the terminal: Tableau, Metabase and Looker Studio to Looker](./bi-to-looker-session)
- Pair files: `bi_pairs/metabase_to_looker/` (translation guide, property mapping, feature detection, content mapping, tooling, worked examples)
- IR schema: `wire/schemas/bi_ir-schema.md`
