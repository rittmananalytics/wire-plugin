---
wire_schema: "1.0"
command: generate
artifact: lookml_model
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> translates one model batch (default: the next incomplete batch); --all translates every incomplete batch in order"
produces:
  - type: document
    path: "migration/lookml_model/lookml_model.md"
    description: "Batch summary: per batch, views, explores and parameters emitted, needs_human items open, branch commit"
  - type: report
    path: "migration/lookml_model/<batch_id>/needs_human.json"
    description: "Converter report: every construct not emitted, with class, reason and proposal"
  - type: document
    path: "migration/lookml_model/<batch_id>/models/<model>.model.lkml"
    description: "Emitted LookML model file with explores (views under views/ and the conversion summary in the same batch folder)"
preconditions:
  - artifact: looker_target_setup
    action: review
    outcome: approved
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
description: "Experimental: Translate one batch of Tableau, Metabase, Looker Studio or Omni content into LookML views and explores on the migration branch; the deterministic converter writes the mechanical LookML and every construct it cannot emit becomes a needs_human item"
argument-hint: <release-folder> [--batch <id> | --all]

---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: lookml_model` and `artifact_file_path: migration/lookml_model/lookml_model.md` before proceeding.

---

# LookML Model: Generate

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

The translation has two halves. The mechanical half is a script: `wire/scripts/twb_to_lookml.py convert` reads the snapshot, applies the pair's translation guide and emits LookML deterministically, including the row-level subset of the Tableau calculation language. The judgement half is what the script refuses: LOD expressions, table calculations, blends, sets, unmapped functions, and the cardinality of every join (Tableau physical joins declare none). Each arrives as a `needs_human` item. The agent resolves it from the plan's rulings or parks it. It never hand-writes LookML the script can emit.

```
⚠️  DATA SAFETY REMINDER
Tableau: read only (the snapshot). LookML: written to the migration branch only, never merged here.
Warehouse: no queries. Validation queries belong to /wire:lookml-model-validate.
```

## Pair: metabase_to_looker

The workflow applies with these differences.

- **Step 1.** A model batch is one Metabase database (one connection), optionally narrowed to the dashboards in the batch.
- **Step 2.** The converter is `mb_to_lookml.py`; it also writes the batch's LookML dashboards (one per dashboard tab, and a one-tile dashboard per question on no dashboard), which `looker-content-generate` takes from the batch output:

```bash
python3 <plugin-root>/scripts/mb_to_lookml.py convert \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/metabase \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> --database <metabase database id> \
  [--dashboards <id,id>] [--include-root <folder>]
```

- **Step 3.** The `needs_human` items for this pair: native SQL questions and models that became views on their SQL (remodel onto shared views, or keep), fields lifted from simple native SQL (keep or remove), joins not to a primary key, custom columns not translated, binning by number of bins (choose a fixed width), multi-stage questions, dashboard filters that change date grouping, and content on a database Looker cannot connect to. Primary keys come from Metabase's metadata (`type/PK`); a joined view without one is listed.

## Pair: looker_studio_to_looker

The workflow applies with these differences.

- **Step 1.** A model batch is a set of reports (a report family, or the reports on one subject area).
- **Step 2.** The converter is `ls_to_lookml.py`, run on the batch's `report.json` files and the ruled metric catalogue; it also writes the batch's LookML dashboards, which `looker-content-generate` takes from the batch output:

```bash
python3 <plugin-root>/scripts/ls_to_lookml.py convert \
  --reports .wire/releases/$ARGUMENTS/audit/looker_studio/reports/<report_id>/report.json ... \
  --catalogue .wire/releases/$ARGUMENTS/audit/metric_catalogue.json --namespace <looker_studio_namespace> \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> [--include-root <folder>]
```

- **What it writes.** A view per BigQuery table a data source reads and per custom SQL data source; measures for the aggregations the charts use; calculated fields translated to BigQuery SQL (a ruled catalogue entry names the measure; Looker Studio's division becomes `SAFE_DIVIDE`); charts on Looker Studio's Looker connector pointed at the existing explore, with no view; `parity_map.json` linking each chart to its element and its recording columns to Looker fields.
- **Step 3.** The `needs_human` items for this pair: custom SQL views (remodel or keep), calculated fields not translated, blends (model the join in an explore), data sources Looker cannot read (Search Console, GA4, Sheets, Funnel.io: a pipeline task or drop), date range control defaults (not in the capture), a chart's own date range ending today (Looker's nearest filter also takes in the rest of the current month), breakdown dimensions pivoted (Looker Studio draws only its top series), and dashboards on an existing Looker model (written to a folder of their own: add its include to that model).

## Pair: omni_to_looker

The workflow applies with these differences.

- **Step 1.** A model batch is a set of topics (with the views they join), optionally narrowed to the dashboards in the batch. One Omni shared model maps to one LookML model on one connection.
- **Step 2.** The converter is `omni_to_lookml.py`; it also writes the batch's LookML dashboards (one per Omni dashboard document) and `parity_map.json`, which `looker-content-generate` takes from the batch output:

```bash
python3 <plugin-root>/scripts/omni_to_lookml.py convert \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/omni \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> \
  [--topics <name,name>] [--documents <id,id>] [--include-root <folder>]
```

- **What it writes.** A view per Omni view: a schema view keeps its table (`sql_table_name`, with the connection's project on BigQuery), a query view that is only `SELECT * FROM <table>` does too, other SQL becomes a derived table. Bare column names in field SQL are qualified with `${TABLE}`; `${field[month]}` becomes `${field_month}`. A time field (declared timeframes, Omni's own field list, or a DATE or TIMESTAMP column in `columns.json`) becomes a dimension group. Topics become explores on their base view, with the nested joins flattened and each join's `sql_on`, relationship and type taken from the relationship that connects it; an alias (`join_to_view_as`) joins with `from:`.
- **Step 3.** The `needs_human` items for this pair: query views built from a topic query, views with Mustache in their SQL (and the topics on them), nested fields, markdown and links, bins (Looker labels tiers differently), cross-view references, filter-only fields, a relationship declared from the other side (confirm the join type), custom aggregate SQL on a joined view (fan-out), default filters (not emitted: Looker's `always_filter` would also change saved tiles), access filters (the user attributes must exist), AI context (dropped), and timeframes with no LookML equivalent. Dimensions are typed from the snapshot's `columns.json` (read from `INFORMATION_SCHEMA` through Omni), else from their format and the filters that use them; the rest default to `string`. A DATE column's group gets `datatype: date`.

## Workflow

### Step 1: Resolve the batch

Read the plan's model batches (`migration/bi_migration_batches.csv`, `batch_kind: model`). A batch is a set of data source identities (one per fingerprint group the plan ruled to consolidate).

### Step 2: Run the converter

```bash
python3 <plugin-root>/scripts/twb_to_lookml.py convert \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/tableau \
  --out .wire/releases/$ARGUMENTS/migration/lookml_model/<batch_id> \
  --model <bi_migration.target.model> --connection <connection> --dialect <bigquery|snowflake> \
  --datasets <identity,identity,...> [--include-root <folder>]
```

When the client's LookML repository already has views (most do), pass `--include-root <folder>` (for example `tableau_migration`) and a model name that is not in use: views and dashboards are written under the folder and the model includes only it, so the project's existing `/views/` are not pulled in and view names cannot clash. A new model must be configured by a Looker admin (Admin, Projects) before it can be queried in production.

### Step 3: Resolve needs_human

Read `migration/lookml_model/<batch_id>/needs_human.json`. For each item: apply the plan's ruling (an LOD becomes a derived table or is dropped; a table calculation becomes a Looker table calculation on the tile; an extract is rebuilt as a dbt model or read live), confirm each join's `relationship:` (Tableau's default relationship declares no unique keys, so the converter proposes `many_to_many`) and each proposed `primary_key: yes` (taken from a view's single `*_pk` column), set one on any joined view listed without one, or park the item for the release director. Write the resolution against each item in the batch summary. Hand-written LookML goes in a separate `<batch_id>/hand/` folder, so the converter's output stays regenerable.

### Step 4: Write to the branch

The batch folder now holds `views/<view>.view.lkml`, `models/<model>.model.lkml`, `needs_human.json` and `conversion_summary.json`. Copy `views/`, `models/` and `hand/` into the LookML repo on the migration branch and commit. Record the commit.

### Step 5: Update status and output

```yaml
artifacts:
  lookml_model:
    generate: complete
    file: migration/lookml_model/lookml_model.md
    experimental: true
    batches_complete: [<batch_id>]
    needs_human_open: N
```

Output `/wire:lookml-model-lint $ARGUMENTS --batch <batch_id>`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `lookml_model` as artifact_id, `LookML Model` as artifact_name, and the `file` value from `artifacts.lookml_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `lookml_model` as artifact, `generate` as action.
