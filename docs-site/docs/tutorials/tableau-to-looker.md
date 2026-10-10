---
sidebar_position: 14
title: "Tutorial: Tableau to Looker (experimental)"
---

# Tutorial: Tableau to Looker (experimental)

:::caution[Experimental]

The Tableau to Looker pair is experimental. It has run end to end once, on a Tableau Cloud trial site: Tableau's sample workbooks, and one sheet on BigQuery that was converted, deployed to Looker and matched row for row. It has not run on a client estate. Review every output before presenting it to a client, and read the [limitations](#limitations) first.

:::

This tutorial runs a `bi_migration` release with the `tableau_to_looker` pair. The client is a fictional retailer, Halcyon Outdoor, moving its Tableau Cloud reporting to Looker on the same BigQuery warehouse. It shows how Wire takes a snapshot of a Tableau site, which workbook constructs translate to LookML and which need a person, how duplicate data sources become one explore, and how parity works with Tableau as the source.

The release is directed in prose, as in the [Looker to Omni tutorial](./looker-to-omni-migration). At each step we name the command Wire runs.

## How this pair works

Tableau keeps the model and the content together in one XML document per workbook, plus published data sources. There is no git repository, so Wire takes a snapshot through the REST API and pins each object by its `updatedAt` and a SHA-256 of the file. A converter then reads the XML, classifies every construct, translates what it can and lists the rest.

| Step | Script | Output |
|---|---|---|
| Snapshot | `tableau_export.py` | Workbooks and data sources (without extracts), inventory with each workbook's views, usage |
| Audit | `twb_to_lookml.py audit` | Catalogs with a class per construct, data source fingerprints, the tool-neutral IR |
| Convert | `twb_to_lookml.py convert` | LookML views, explores, parameters and LookML dashboards; `needs_human.json` |
| Lint | `twb_to_lookml.py lint` | Fails if any Tableau expression is left in the LookML |

All four are deterministic and make no AI call. The record they write uses the tool-neutral IR (`wire/schemas/bi_ir-schema.md`), the shape later pairs are expected to share.

## Before you start

| Need | How |
|---|---|
| A Tableau personal access token | Created on the site; a site administrator may first need to allow token creation (Settings, General). Keep the name and secret in a file outside the repository that only you can read, such as `~/.wire/tableau.env` |
| `tableauserverclient` | `python3 -m pip install tableauserverclient` |
| Site Role Explorer or higher, with download permission | On every project in scope |
| An Admin Insights export | For usage on Tableau Cloud (otherwise the snapshot uses each view's all-time view count, with no time window) |
| The client's LookML repo and Looker API access | For the target |

A Desktop-only estate (a folder of `.twb` and `.twbx` files) runs in files mode: no network call, no usage, and parity by manual export.

## Step 1: Create the release

| You say | Wire replies |
|---|---|
| "Start a BI migration release for Halcyon: Tableau Cloud to Looker. Site halcyon, Looker project halcyon_retail." | Creates the release with `bi_pair: tableau_to_looker` and says the pair is experimental. The Looker-to-Omni phases are switched off; the Tableau audit, Looker target, LookML model and Looker content phases are switched on. |

Ran: `new`.

## Step 2: Snapshot and audit

Wire runs `tableau-audit-generate`. On the fixture estate the audit finds:

| Construct | Class | What happens |
|---|---|---|
| Columns (17) | mechanical | Dimensions, date dimension groups, sum measures |
| Row-level calculations (5): `IF ... ELSEIF`, `ZN([profit]) / [sales]`, `DATETRUNC`, `DATEDIFF`, a comparison with a parameter | assisted | Translated to SQL; division uses `NULLIF` |
| Aggregate calculations (2): `SUM([profit]) / SUM([sales])`, `SUM([sales]) - [Parameters].[Parameter 1]` | assisted | `type: number` measures over emitted measures |
| A group, a bin | assisted | `CASE` and `FLOOR` dimensions |
| A set | assisted | Listed for a person |
| `{ FIXED [customer_id] : SUM([sales]) }` | redesign | Not emitted; the plan rules a derived table or a drop |
| `RUNNING_SUM(SUM([sales]))` | redesign | Not emitted; a Looker table calculation or a drop |
| A physical join | assisted | `many_to_one` proposed: Tableau never declares cardinality |
| A data source on an extract | redesign | Views read the live tables; the plan rules the extract |
| A blended worksheet, a story, a device layout | redesign, drop, drop | Listed |

**Fingerprints.** Embedded data sources are often copies. The audit fingerprints each one (connection, tables, joins, columns; not names or captions). On a three-workbook sample, two workbooks embedding the same data source under different names form one group, and a third with one extra column is a separate group. The plan proposes one shared explore per group.

| You say | Wire replies |
|---|---|
| "Approve the audit. The extract is a nightly copy of the warehouse table." | Records the review and notes the extract finding for the plan. |

Ran: `tableau-audit-generate`, `tableau-audit-validate`, `tableau-audit-review`.

## Step 3: The plan

`bi-migration-plan-generate` adds two rulings for this pair: a consolidation ruling per fingerprint group, and an extract disposition per extract (dbt model, live connection, or drop). LOD expressions and table calculations each take a per-field ruling.

| You say | Wire replies |
|---|---|
| "Consolidate every group. Read the extract's table live. Drop the running total; rebuild the customer lifetime sales as a derived table." | Records the rulings and cuts model batches by fingerprint group and content batches by dashboard usage. |

## Step 4: Target, model and content

- `looker-target-setup-generate` checks the Looker connection and creates the migration branch, folders, groups and user attributes. It never merges.
- `lookml-model-generate` runs the converter for each batch and resolves its needs-human items from the rulings. Hand-written LookML (the derived table) goes in a separate `hand/` folder, so the converter's output stays regenerable. `lookml-model-lint` fails if any Tableau expression is left, and checks primary keys on joined views; `lookml-model-validate` runs Looker's validator and one smoke query per explore.
- `looker-content-generate` commits the LookML dashboards. Zones land on Looker's 24-column grid, quick filters become dashboard filters with `listen`, text zones become text elements, and images and device layouts are listed for hand finishing. A sheet on no dashboard becomes a one-tile dashboard that keeps the sheet's sort and filters; the plan keeps it, makes it a Look, or drops it.

**Deploying into an existing LookML project.** Most clients already have a LookML project, often with views of the same name (`companies_dim`, `invoices_fact`). Wire then converts with `--include-root <folder>` (for example `tableau_migration`) and a model name not in use. The views and dashboards go under that folder and the new model includes only it, so the project's own views are not pulled in and the existing models are untouched. The work goes on a branch; the client's Looker developer validates it in development mode, merges and deploys. A Looker admin configures the new model (Admin, Projects) before it can be queried in production. To undo, delete the folder and the model file and remove the model configuration.

**Primary keys.** Tableau's relationships record no keys, so joins arrive as `many_to_many`. Wire proposes each view's single `*_pk` column as its `primary_key`, for a person to confirm. Looker then uses symmetric aggregates, so totals stay correct across the joins; a joined view with no key is listed, because its totals can be wrong until one is set.

## Step 5: Parity and cutover

`bi-equivalency-validate` takes each Tableau sheet's rows through Query View Data (`tableau_export.py view-data`, with the view ID from the `view_luid` column of `bi_content_catalog.csv`) and the Looker element's rows through the Looker API, then compares them with the standard comparator. If an extract refreshed after the parity run, the tile is `INCONCLUSIVE`, not `PASS`. `migration-drift-generate` compares a fresh snapshot with the pinned one: a workbook whose `updatedAt` moved is `content_drifted`.

## What the live runs found

In October 2026 the pair ran against a Tableau Cloud trial site holding two sample workbooks (Superstore, World Indicators) and one published data source. The snapshot, audit, conversion, lint and Query View Data all ran. The run found eight faults that the hand-written fixtures had missed. Each is now fixed and covered by a test.

| Found | Fix |
|---|---|
| A bin built on a calculated field stopped the audit | Bins and groups over a translated calculation are emitted; otherwise listed for a person |
| A bin sized by a parameter | Emitted with `{% parameter %}` |
| Excel, CSV and extract-only (`.hyper`) sources looked like warehouse tables | Classed as redesign; the plan rules load or drop |
| Two Excel files with the same sheet name shared one view | The file name is part of the table identity |
| Column names with spaces (`Row ID`) were unquoted | Quoted for the dialect |
| A calculation that refers to another failed when processed first | Calculations are translated in dependency order |
| Parameter values kept Tableau's escapes and full float precision | Unescaped and tidied (`18.4`, not `18.399999999999999`) |
| The snapshot recorded the next extract refresh, not the last; no view IDs; lint passed an empty folder | Last refresh from job history; view IDs and all-time view counts recorded; lint fails on an empty folder |

Query View Data returns values as the sheet displays them (`$3,338`). The comparator now reads currency symbols and thousands separators.

A second run added a published data source on BigQuery (five tables in one dataset) and a workbook with one sheet: revenue by company, blank names excluded, totals of £50,000 or more, largest first. It found six more faults, now fixed and tested:

| Found | Fix |
|---|---|
| Two published data sources shared one internal name; one was lost | Published sources are kept by ID and named by their site name |
| The workbook named its published source by content URL, which did not resolve | The snapshot records content URLs; references resolve by content URL, name or internal name |
| Converting one workbook brought every published source | Only the published sources its workbooks use |
| A relationship with empty key fields | `sql_on` left to a person |
| No primary keys, so totals across joins could be wrong | A single `*_pk` column becomes the primary key, to confirm; a joined view with none is listed |
| A sheet on no dashboard was not emitted; its sort and filters were not read | A one-tile LookML dashboard keeping the sort, the null exclusion and the measure threshold |

The sheet's 34 rows from Query View Data were compared, with the standard comparator, against the SQL the emitted explore generates, run on BigQuery: `PASS` (`pass_qualified`, rounding), every company and value matching to six decimal places, in the same order. The LookML was then converted with `--include-root tableau_migration` (so the client project's existing views were not pulled into the new model), deployed to a Looker instance as a separate `tableau_migration` model, and queried through the Looker API with the tile's fields, filters and sort. Looker's 34 rows matched Tableau's: `PASS` (`pass_qualified`, rounding). Looker's SQL used the proposed `invoice_pk` primary key for a symmetric aggregate over the `many_to_many` join, which is why the proposed keys matter.

## Limitations

| Limitation | Effect | What to do |
|---|---|---|
| Experimental | Run end to end once on a Tableau Cloud trial site: one BigQuery sheet converted, deployed to Looker and matched row for row. Not on a client estate, and not on a multi-tile dashboard | Treat outputs as drafts for review; report problems on wire#287 |
| New estates hold new structures | Two live runs found fourteen faults the hand-written fixtures missed; a client estate will hold more | Run the audit early and read `needs_human.json` before planning |
| A client repo with views already | The default output assumes it owns the repo root | Use `--include-root <folder>` and a separate model |
| Displayed values in parity | Query View Data returns values rounded to the sheet's number format | Set each measure's precision to the displayed precision |
| Extract refresh history | The last refresh time comes from the site's job history, which keeps a limited period | An older refresh is recorded as unknown; check the extract's schedule |
| Translator covers the row-level subset | LOD expressions, table calculations, sets, blends and unmapped functions are never translated | Each is a needs-human item with the Tableau formula |
| No join cardinality in Tableau | Every physical join is `many_to_one` until confirmed | Confirm it and set primary keys in the model review |
| Extracts are not opened | Views read the live tables | The plan rules each extract; parity records the extract refresh time |
| Desktop files mode | No usage, no headless parity | Usage is `unknown`; export sheets by hand |
| Usage | Admin Insights column names differ between exports; without an export, usage is all-time view counts | The script accepts the common names; say which source the ranking used |
| No metric catalogue in this pair yet | Duplicate calculated fields across workbooks are not consolidated by name | Fingerprint groups consolidate whole data sources |
| No artifact rename | The other pairs keep their own artifact names; the tool-neutral rename proposed in wire#287 is not done | None needed for this pair |
| Out of scope | Prep flows, permission migration beyond groups, formatting fidelity | Handled by hand |

## See also

- [BI Tool Migration](../release-types/bi-migration)
- Pair files: `bi_pairs/tableau_to_looker/` (translation guide, property mapping, feature detection, content mapping, tooling, worked examples)
- IR schema: `wire/schemas/bi_ir-schema.md`
