---
sidebar_position: 17
title: "Tutorial: Omni to Looker (experimental)"
---

# Tutorial: Omni to Looker (experimental)

:::caution[Experimental]

The Omni to Looker pair is experimental. Review every output before presenting it to a client, and read the [limitations](#limitations) first.

:::

This tutorial runs a `bi_migration` release with the `omni_to_looker` pair. The client is a fictional retailer, Halcyon Outdoor, moving its Omni dashboards to Looker on the same BigQuery warehouse. It shows how Wire takes a snapshot of an Omni model and its dashboards, what converts to LookML and what needs a person, and how parity works with Omni as the source.

The release is directed in prose, as in the [Looker to Omni tutorial](./looker-to-omni-migration). At each step we name the command Wire runs.

## How this pair works

Omni's model language descends from LookML. A view has dimensions with SQL and measures with an aggregate type; a time field has timeframes; a topic joins views through declared relationships; fields refer to each other as `${view.field}`. Most of it maps one to one, and the converter does that part. What does not map is what Omni added on top: Mustache templating, query views built from a topic query, fields defined only inside a workbook, AI context, field-selection controls and period-over-period comparisons. Those go to a person.

| Step | Script | Output |
|---|---|---|
| Snapshot | `omni_export.py snapshot` | The shared model's files (the views that topics, relationships and tiles reach), Omni's field list for those views, the connection's dialect and project, one file per dashboard |
| Audit | `omni_to_lookml.py audit` | Catalogs with a class per construct, the tool-neutral IR, `needs_human.json` |
| Convert | `omni_to_lookml.py convert` | LookML views, explores and LookML dashboards; `needs_human.json`; `parity_map.json` |
| Lint | `omni_to_lookml.py lint` | Fails if Omni syntax is left in the LookML or a view defines a field twice |

All four are deterministic and make no AI call. The snapshot only reads from Omni.

## Before you start

| Need | How |
|---|---|
| The Omni CLI | Installed, with a profile on the client's instance (`omni config init`) that can read the shared model and the dashboards in scope |
| The shared model's id | `omni models list`; the one with `modelKind: SHARED` |
| SQL access on the model's connection | The snapshot reads column types from the warehouse's `INFORMATION_SCHEMA` through Omni, because Omni's YAML has none |
| The client's LookML repo and Looker API access | For the target |

## Step 1: Create the release

| You say | Wire replies |
|---|---|
| "Start a BI migration release for Halcyon: Omni to Looker. Instance halcyon.omniapp.co, shared model halcyon, Looker project halcyon_retail." | Creates the release with `bi_pair: omni_to_looker` and says the pair is experimental. The Looker-to-Omni phases are switched off; the Omni source audit, Looker target, LookML model and Looker content phases are switched on. |

Ran: `new`.

## Step 2: Snapshot and audit

Wire runs `omni-source-audit-generate`. On the fixture estate the audit finds:

| Construct | Class | What happens |
|---|---|---|
| Schema views on `analytics` tables | mechanical | One view per table, `sql_table_name` with the project |
| A query view that is only `SELECT * FROM` a table | mechanical | A view on the table |
| A query view with its own SQL | mechanical | A derived table |
| A query view built from a topic query | redesign | Not converted: a native derived table or a dbt model |
| `created_at`, declared with no timeframes but listed by Omni with `[date]`, `[month]` | mechanical | A dimension group |
| Measures with filters, a ratio of measures, `sum_distinct_on` | mechanical | Filtered measures, a `type: number` measure, `sum_distinct` with its key |
| A measure filtered with a regular expression | assisted | Withheld: an unfiltered measure would change the number |
| A topic with nested joins and an alias (`referrers`) | mechanical | An explore with flat joins; the alias joins with `from:` |
| The topic's default filter | assisted | Listed, not emitted: Looker's `always_filter` would also change saved tiles |
| Bins, a view with Mustache in its SQL, a nested field | assisted, redesign, redesign | A tier (labels differ); the others listed |
| AI context on the model, a topic and a field | drop | No LookML equivalent |
| Two dashboards, a workbook with no dashboard | mechanical, drop | Two LookML dashboards; the workbook listed as skipped |

| You say | Wire replies |
|---|---|
| "Approve the audit. Move the margin field into the shared model before we snapshot again; rebuild the repeat-customers view as a dbt model." | Records the review and the rulings for the plan. |

Ran: `omni-source-audit-generate`, `omni-source-audit-validate`, `omni-source-audit-review`.

## Step 3: The plan

`bi-migration-plan-generate` adds the pair's rulings: a ruling per tile on a workbook-only field, per topic-built query view and templated view, per topic default filter and per SQL tile. Model batches are groups of topics with the views they join; content batches are dashboards by visits.

## Step 4: Target, model and content

- `looker-target-setup-generate` checks the Looker connection reaches the warehouse the Omni connection reads, and creates the migration branch, folders and groups. It never merges.
- `lookml-model-generate` runs the converter for a batch of topics and resolves its needs-human items from the rulings. Bare column names in Omni field SQL become `${TABLE}.column`; `${created_at[month]}` becomes `${created_at_month}`. Wire converts with `--include-root <folder>` and a model name not in use, so the client's existing LookML is untouched. `lookml-model-lint` fails on any Omni syntax left and on a field defined twice; `lookml-model-validate` runs Looker's validator and a query per explore.
- `looker-content-generate` commits the LookML dashboards. Omni's 24-column grid maps to Looker's newspaper layout; tile heights are scaled. Controls become dashboard filters, and each tile the control was mapped to `listen`s on its field. A safe-divide calculation becomes a Looker table calculation.

## Step 5: Parity and cutover

`bi-equivalency-validate` runs each Omni tile's saved query through the CLI (`omni_export.py tile-data`, raw values, unpivoted) and the Looker element's query through the Looker API, then compares them with the standard comparator. Omni returns a month as `2026-10-01` and Looker as `2026-10`, so contracts declare the grain. Neither side applies dashboard control values. `migration-drift-generate` compares a fresh snapshot with the pinned one: a document edited in Omni, or a model file changed, after the snapshot.

## What the real model showed

In October 2026 the pair ran end to end against Rittman Analytics' own Omni model on BigQuery. Omni was only read. Of nine dashboards requested, seven were on the shared model and two on another model; the snapshot kept 95 of the model's 1,108 files (the rest are schema views nothing reaches) and read column types for 34 tables.

| Result | Count |
|---|---|
| Views converted | 57 |
| Topics converted to explores | 28 of 32 (four sit on views with Mustache in their SQL) |
| LookML dashboards | 7 |
| Lint problems | 0 |

Three dashboards (Organic Leads Analysis, Marketing Attribution and Financial Analytics 2026) were deployed to Looker as their own model, with the 28 explores, and each tile's rows were compared with Omni's.

| Dashboard | Tiles | Result |
|---|---|---|
| Organic Leads Analysis | 14 | 14 `PASS` |
| Marketing Attribution | 13 | 13 `PASS` |
| Financial Analytics 2026 | 12 | 12 `PASS` |

16 tiles matched exactly. 23 matched with a recorded qualification: float rounding below one millionth (18), row order on unsorted tiles (4), or both (1). Four tiles returned exactly their row limit (three top-N tables and one 2,677-row table); they were run on both sides at a parity limit of 5,000 and then matched in full.

The run changed the converter in five places the fixtures had missed:

| Found by | Fault | Fix |
|---|---|---|
| The snapshot | An aliased join's relationship names the view behind the alias, not the alias | Relationships are matched on either |
| Reading the output | A query view that is only `SELECT * FROM` a table was a derived table | It is a plain view on the table |
| The conversion | Omni writes some date windows in mixed units (`1 day ago` for `30 years`) | They convert, with a note, rather than drop the tile |
| Looker's validator | A dimension's `${net_amount}`, where `net_amount` is only a measure, is the column in Omni but the measure in LookML | It is written `${TABLE}.net_amount`; lint fails on any dimension that references a measure |
| BigQuery, at parity | Two tiles compared a DATE column with a timestamp, because Omni's YAML has no column types | The snapshot reads types from `INFORMATION_SCHEMA` through Omni; DATE groups get `datatype: date` |

## Limitations

| Limitation | Effect | What to do |
|---|---|---|
| Experimental | Outputs are drafts | Review them before presenting them to a client |
| No types in Omni's YAML | Types come from `INFORMATION_SCHEMA`; a view on other SQL is typed only from its formats and filters | Check `column_gaps` in the snapshot |
| Workbook-only fields | Fields defined in a document's workbook are not in the shared model; their tiles are listed | Move them into the shared model, or rebuild in Looker |
| Not converted | Mustache templating, topic-built query views, nested fields, markdown, field-selection controls, period over period, SQL tiles, composite OR filters | Each is a needs-human item with the reason |
| Default filters | Not emitted; the proposal carries the translated filter | Rule `always_filter` or nothing in the plan |
| Column qualification | A keyword the converter does not know is treated as a column | Looker's validator catches it in `lookml-model-validate` |
| Out of scope | Permissions, schedules, alerts, embedding | Handled by hand |

## See also

- [BI Tool Migration](../release-types/bi-migration#omni-to-looker)
- [Tutorial: Looker to Omni](./looker-to-omni-migration): the same two tools, the other way round
- Pair files: `bi_pairs/omni_to_looker/` (translation guide, property mapping, feature detection, content mapping, tooling, worked examples)
- IR schema: `wire/schemas/bi_ir-schema.md`
