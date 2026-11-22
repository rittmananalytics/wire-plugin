---
wire_schema: "1.0"
command: generate
artifact: looker_content
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
      description: "--batch <id> writes one content batch; --all writes every incomplete batch"
produces:
  - type: document
    path: "migration/looker_content/looker_content.md"
    description: "Batch summary: per batch, dashboards and tiles written, tiles skipped by reason"
  - type: report
    path: "migration/looker_content/<batch_id>/manifest.csv"
    description: "One row per Tableau dashboard: source identity, LookML dashboard file, state, tile counts"
  - type: document
    path: "migration/looker_content/<batch_id>/dashboards/<dashboard>.dashboard.lookml"
    description: "One LookML dashboard per Tableau dashboard in the batch"
preconditions:
  - artifact: lookml_model
    action: validate
    outcome: PASS
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
description: "Experimental: Write one batch of Tableau, Metabase, Looker Studio or Omni dashboards as LookML dashboards in the client's Looker repo on the migration branch; every tile that cannot be rebuilt is listed with its reason, never dropped silently"
argument-hint: <release-folder> [--batch <id> | --all]

---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: looker_content` and `artifact_file_path: migration/looker_content/looker_content.md` before proceeding.

---

# Looker Content: Generate

## Purpose

> **Experimental.** This command serves three experimental pairs, each run end to end once and none on a client estate: `tableau_to_looker` (one BigQuery sheet on a Tableau Cloud trial site), `metabase_to_looker` (four BigQuery questions on a Metabase Cloud trial instance) and `looker_studio_to_looker` (two Looker Studio reports on BigQuery and Looker data sources), each converted, deployed to Looker and matched. It also serves `omni_to_looker` (three dashboards from Rittman Analytics' own Omni model, 39 of 39 tiles matched). At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Tableau dashboards become LookML dashboards (`.dashboard.lookml`) in the same repository as the model, not user-defined dashboards through the API, so they get the same branch, drift and reverse-port handling as the model. `twb_to_lookml.py convert` writes them with the model batch; this command takes the ones in the content batch, resolves their skipped tiles and commits them. A worksheet on no dashboard is emitted as a one-tile LookML dashboard (its sort and supported filters kept); it stays one, becomes a Look through the Looker API (`create_look`), or is dropped, as the plan says.

## Pair: metabase_to_looker

The workflow applies with these differences. **Step 1:** take each Metabase dashboard's files from the model batch output: one LookML dashboard per tab (`<dashboard> - <tab>`), and one one-tile dashboard per question on no dashboard. **Step 2:** the skipped tiles are questions the converter did not convert (see the model batch's `needs_human.json`), link, iframe and action cards, combined series, click behaviour, and text cards that showed a filter value. Metabase dashboard filters arrive as Looker dashboard filters with `listen` on each tile they were mapped to; a filter that changes date grouping is listed. **Step 3:** `source_object` in each parity contract is the Metabase card identity (`metabase:<instance>:card:<id>`), and the contract records the dashcard id so the source side runs the card as it runs on that dashboard.

## Pair: looker_studio_to_looker

The workflow applies with these differences. **Step 1:** take each report's dashboards from the model batch output: one per visible page, with charts on the same 24-column grid, text boxes as text tiles, the date range control and dimension filter controls as dashboard filters with `listen`. A dashboard whose charts all read one existing Looker model is in `dashboards/<model>/`, so the new model does not include it: add that folder's include to the existing model, or leave the dashboard out. **Step 2:** the skipped tiles are charts on blends and on data sources Looker cannot read. **Step 3:** fill each Route C contract from `parity_map.json`: `target_object` the element, `field_map` from recording column to Looker field.

## Pair: omni_to_looker

The workflow applies with these differences. **Step 1:** take each Omni dashboard's file from the model batch output: one LookML dashboard per document, with tiles on the same 24-column grid (heights scaled), text tiles kept, tile filters translated, Omni table calculations (arithmetic and safe divide) as Looker table calculations, and controls as dashboard filters with `listen` on each tile the control was mapped to. **Step 2:** the skipped tiles are SQL tiles, tiles on fields defined only in a workbook, tiles with a filter the converter cannot translate (composite OR, negated numbers), field-selection controls, period-over-period comparisons and workbook tabs not on the dashboard (see the model batch's `needs_human.json`). A document with pages becomes one dashboard. **Step 3:** fill each parity contract from `parity_map.json`: `source_object` the Omni tile identity (`omni:<instance>:document:<id>/query:<key>`), `target_object` the element, `field_map` from Omni field to Looker field.

## Workflow

### Step 1: Select the batch

Read the plan's content batch. For each Tableau dashboard, take `dashboards/<dashboard>.dashboard.lookml` from the model batch output that carries its explores.

### Step 2: Resolve skipped tiles

The converter lists each tile it could not write in `needs_human.json` (a blend, a sheet on a redesigned field, an image, a filter action). Apply the plan's ruling per tile: rebuild against a redesigned field, add a Looker table calculation, add `listen` for a filter action, or list it for hand finishing. Filter actions become dashboard filters with `listen`, or cross-filtering (`crossfilter_enabled: true`) where the plan rules it.

### Step 3: Commit and record

Copy each `<dashboard>.dashboard.lookml` into `migration/looker_content/<batch_id>/dashboards/` and commit the dashboards to the migration branch. Write `manifest.csv` with one row per dashboard and `looker_content.md` with the batch summary and the hand-finish list. For each tile, write a parity contract under `migration/parity/contracts/<dashboard>/<tile>.yaml` with `source_object` the Tableau sheet identity and `target_object` the LookML dashboard element.

```yaml
artifacts:
  looker_content:
    generate: complete
    file: migration/looker_content/looker_content.md
    experimental: true
```

Output `/wire:looker-content-validate $ARGUMENTS --batch <batch_id>`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_content` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_content` as artifact_id, `Looker Content` as artifact_name, and the `file` value from `artifacts.looker_content` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_content` as artifact, `generate` as action.
