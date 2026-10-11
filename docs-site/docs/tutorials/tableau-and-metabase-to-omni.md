---
sidebar_position: 13
title: "Tutorial: Tableau and Metabase to Omni (experimental)"
---

# Tutorial: Tableau and Metabase to Omni (experimental)

:::caution[Experimental]

The Tableau to Omni and Metabase to Omni pairs are experimental.

:::

This tutorial runs `bi_migration` releases with the `tableau_to_omni` and `metabase_to_omni` pairs. The client is a fictional retailer, Halcyon Outdoor, moving its Tableau Cloud and Metabase reporting to Omni on the same BigQuery warehouse. The audits are the same as in the [Tableau to Looker](./tableau-to-looker) and [Metabase to Looker](./metabase-to-looker) tutorials; this page covers what changes when the target is Omni.

## How these pairs work

The audit snapshots the source tool and classes every construct. For the model, the same reader works out what each table, column, calculation, join and tile becomes, and `bi_to_omni.py` writes Omni files from that directly. No LookML is written on the way.

| Step | Script | Output |
|---|---|---|
| Snapshot | `tableau_export.py` or `metabase_export.py` | The pinned snapshot |
| Audit | `twb_to_lookml.py audit` or `mb_to_lookml.py audit` | Catalogs with a class per construct, the tool-neutral IR |
| Convert | `bi_to_omni.py convert --source tableau` or `--source metabase` | Omni views, topics, `relationships.yaml`, one document body per dashboard, `needs_human.json`, `parity_map.json` |
| Lint | `bi_to_omni.py lint` | Fails on `${TABLE}`, Liquid, an unknown timeframe or aggregate type, a bare-scalar measure filter, a duplicate name or a field that refers to itself |

## Step 1: Create the releases

| You say | Wire replies |
|---|---|
| "Start two BI migration releases for Halcyon, to Omni: Tableau Cloud (site halcyon) and Metabase (halcyon.metabaseapp.com). Omni model id from the model IDE." | Asks for the target of each (Looker or Omni), records `bi_pair: tableau_to_omni` and `bi_pair: metabase_to_omni`, and says both pairs are experimental. |

Ran: `new` (x2).

## Step 2: Audit and plan

The audits run as in the Looker tutorials. The plan adds one ruling for these pairs: the **view prefix** and **binding**. A prefix keeps the batch's views and topics apart from names already on the Omni model. Query-view binding (the default) files each view as `SELECT * FROM` its table, because on a git-connected Omni model the schema view's file already belongs to Omni's own generated view.

Ran: `tableau-audit-generate`, `metabase-source-audit-generate`, their validate and review, `bi-migration-plan-generate`.

## Step 3: Model on a branch

`omni-target-setup-generate` checks the Omni connection reads the same warehouse and creates the model branch. `omni-model-generate` runs the converter for each batch and writes the files to the branch:

- each view and topic file through `omni models yaml-create` with the branch id;
- the model's `relationships` file, which every topic shares, read from the branch and appended to, never replaced;
- `omni models validate` on the branch.

What the converter writes:

| Source | Omni |
|---|---|
| A table | A query view; each column a dimension named after the column, with the source caption as its label |
| A Metabase cast (a seconds column read as a timestamp) | The raw column, hidden, and a cast dimension with its own name |
| A calculation, a metric, an aggregation | A dimension or measure; a name that would collide with a column is suffixed |
| A join | A relationship and the topic's `joins` |
| A parameter, an LOD expression, a table calculation, a field inside a record column | Not emitted, listed in `needs_human.json` |

Ran: `omni-target-setup-generate`, `omni-model-generate`, `omni-model-lint`, `omni-model-validate`.

## Step 4: Dashboards

The converter has already written one document body per dashboard: tiles with Omni filter objects and sorts, controls with a map naming every tile, and the layout. `omni-content-generate` reviews the skipped tiles and fidelity notes, then creates each document on the shared model and patches its draft with the body and the branch. The draft runs against the branch; the published document stays empty until the branch merges.

## Step 5: Parity

`bi-equivalency-validate` takes the source rows as in the Looker pairs (Tableau Query View Data, Metabase card data) and runs each tile's query from the document draft against the branch, with raw values. `parity_map.json` gives each source field's Omni field.

## What the live run found

In October 2026 the pairs ran against a Tableau Cloud site and a Metabase Cloud instance, both on BigQuery, into an Omni model branch.

| Tile | Source | Rows | Result |
|---|---|---|---|
| Revenue by Company | Tableau published data source (5 tables) | 34 | PASS (rounding) |
| Bounced Session Rate by Channel | Metabase native SQL | 7 | PASS |
| Sessions by Month | Metabase native SQL | 12 | PASS |
| Bounce rate by channel | Metabase query builder | 8 | PASS |
| Sessions by month | Metabase query builder | 12 | PASS |

Omni's validator found one fault the fixtures had missed: Tableau shows a field inside a BigQuery record as `parent.child`, and the converters wrote it as one quoted column name. Such fields are now listed, not emitted, for both the Looker and the Omni target. Omni's API also showed that its number filters have no "or equal" kinds: `>=` is `GREATER_THAN` with `is_inclusive`.

## Limitations

| Limitation | Effect | What to do |
|---|---|---|
| Experimental | Outputs are drafts | Review them before presenting them to a client |
| Parameters and templated filters | Not emitted | An Omni templated filter or a dashboard control, by hand |
| Text cards | Not created | Recreate in the document |
| Tile heights | Rows scaled by 6 | Hand-finish the layout |
| Documents on a branch | Published documents are empty until the branch merges | Review the drafts; merge on the director's ruling |

## See also

- [BI Tool Migration](../release-types/bi-migration#tableau-to-omni-and-metabase-to-omni)
- [Tutorial: Tableau to Looker](./tableau-to-looker), [Tutorial: Metabase to Looker](./metabase-to-looker)
- [Tutorial: Looker to Omni Migration](./looker-to-omni-migration)
- Pair files: `bi_pairs/tableau_to_omni/`, `bi_pairs/metabase_to_omni/`
