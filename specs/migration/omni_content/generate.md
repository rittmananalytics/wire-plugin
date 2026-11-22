---
wire_schema: "1.0"
command: generate
artifact: omni_content
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
      description: "--batch <id> plans (and, once validated, writes) one content batch; --all processes every incomplete content batch in order; --write executes the write step for a batch whose plan has validated"
produces:
  - type: document
    path: "migration/omni_content/omni_content.md"
    description: "Batch summary: per batch, dashboards planned and created, tiles planned, tiles skipped by reason"
  - type: report
    path: "migration/omni_content/<batch_id>/plan.json"
    description: "The dry-run plan for the batch: per dashboard, the Omni document body to create, the control map, and every skipped tile with its reason"
  - type: report
    path: "migration/omni_content/<batch_id>/manifest.csv"
    description: "One row per dashboard: source_id, target_identifier, state (planned | created | failed), tile counts"
preconditions:
  - artifact: omni_model
    action: validate
    outcome: PASS
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
description: Rebuild one batch of Looker dashboards as Omni documents against the translated model, as a plan first and a write second; every tile that cannot be rebuilt programmatically is listed with its reason, never dropped silently
argument-hint: <release-folder> [--batch <id> | --all] [--write]
---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_content` and `artifact_file_path: migration/omni_content/omni_content.md` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

Looker: READ ONLY. Dashboard definitions are read through the Looker API
  (or the Looker MCP). Nothing on the Looker instance is edited, moved,
  or deleted. Looker stays live as the rollback path until cutover.

Omni: the plan step writes NOTHING to Omni. The write step (--write) creates
  NEW documents only, in the folder the plan names. It never edits or deletes
  an existing Omni document, and it touches only documents whose
  target_identifier it recorded itself in manifest.csv.

Warehouse: the plan step runs no queries. The write step runs none either;
  Omni renders tiles when a user opens the document.
```

If a planned document's title matches an existing Omni document in the target folder, the plan records `collision: true` and the write step refuses that dashboard until the release director rules (rename, replace, or skip).

---

# Omni Content: Generate

## Purpose

Rebuilds Looker dashboards and Looks as Omni documents on the translated model. The command is split in two on purpose, the same way the Metabase carve-out transport is (`specs/migration/metabase_carveout/transport_generate.md`): a **plan** that decides every tile's fate and writes nothing to Omni, a **validate** that checks the plan against the branch, and a **write** that executes only a validated plan. The plan is the dry run. Nothing is created in Omni until `/wire:omni-content-validate` has passed for the batch and this command is re-run with `--write`.

What the rebuild can and cannot do is fixed by Omni's document API and by what the model carries. A tile whose every field exists on the branch becomes a `queryPresentation`; dashboard filters become `controls` with per-tile `map` entries; the layout becomes a `containers` tree. A text or markdown tile becomes an `inline-text` content item when its markdown is plain, and a listed manual item when it uses Liquid. A tile that references a field the model does not have is skipped with reason `unmapped_field`, and the model batch is where that is fixed, not here.

## Prerequisites

- `artifacts.omni_model.validate: pass` for the model batch this content batch depends on (the gate reads the overall value; when model batches are still in progress, the plan's `depends_on_batch` names the model batch and its presence in `batches_validated` is what this command checks)
- `omni_model review: approved` before the write step (the plan may be produced earlier)
- Looker API credentials (`LOOKERSDK_BASE_URL`, `LOOKERSDK_CLIENT_ID`, `LOOKERSDK_CLIENT_SECRET`) or the Looker MCP connected
- Omni CLI configured against the target profile

## Inputs

- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv` (rows with `batch_kind: content`)
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv` (dashboards, Looks, tiles, folders, usage)
- `.wire/releases/$ARGUMENTS/migration/omni_model/<model batch>/**` (emitted views and topics; the field namespace)
- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (parity-or-redesign ruling per dashboard, target folder structure)
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- `wire/bi_pairs/looker_to_omni/content_mapping.md` (tile type to `chartType`, filter kinds, control types)
- `wire/bi_pairs/looker_to_omni/tooling.md` (Omni's dashboard inspector and builder scripts, and how this command may use them)
- `wire/bi_pairs/looker_to_omni/content_mapping.md`, section "Rules from Omni's own dashboard migration guide": every control in every tile's map, no quarter-grained date keys, hidden fields left out of `fields`, table pivots in `query.pivots` and chart pivots as the series field, parameters as Mustache block templated filters, never delete by name
- `.wire/releases/$ARGUMENTS/status.md`

## Pairs: tableau_to_omni and metabase_to_omni

These pairs are experimental. Steps 2 to 4 are done by the converter: for each dashboard (and each Metabase tab, and each question or sheet on no dashboard) the model batch wrote `documents/<slug>.json`, an Omni document body with tiles, Omni filter objects, sorts, controls and a `containers` layout, and `documents/<slug>.plan.json` with the tiles planned, the skipped tiles and their reasons (`text_tile`, `unmapped_field`, `unmapped_filter`) and fidelity notes. Step 5 copies them into `plan.json`; the agent reviews the skipped tiles and fidelity notes and adds the hand-finish list. In Step 6, create each document by name on the shared model (`omni documents v2-create`), then patch its draft with the body and the branch (`omni documents v2-patch-draft <identifier> --body` with `branchId`), so the draft runs against the branch; the published document stays empty until the branch merges. Fill each parity contract's `target_object` and `field_map` from `parity_map.json`.

## Pair: looker_studio_to_omni

This pair is experimental in 4.2.2 (see `specs/migration/looker_studio_audit/generate.md`).

For a content batch (one report family), Step 2 reads `audit/looker_studio/reports/<report_id>/report.json` in place of the Looker API, and the mapping follows `wire/bi_pairs/looker_studio_to_omni/content_mapping.md`:

- **One document per report family.** The family's copies become one Omni dashboard; the field that split them (for example a client id filter) becomes a dashboard control or a user attribute, per the plan's ruling.
- **Pages.** Each visible page in scope becomes a tab or a section of the document, in navigation order. Hidden pages are carried only under the plan's ruling.
- **Components.** `mechanical` and `assisted` components map to tiles by `omni_chart` in the content catalog. Report-level components appear once per dashboard, not once per page. Text boxes become `inline-text` items from `report.json` text; decorative shapes and images are dropped and listed in the hand-finish list.
- **Layout.** Use the `grid_x`, `grid_y`, `grid_w`, `grid_h` columns (24-column grid, rule in `content_mapping.md`) to author the `containers` tree in full.
- **Fields.** Each tile's metrics resolve to the Omni measure named by the metric catalogue's `target_name` for that metric; a chart-level formula with no ruled group is `unmapped_field` and skipped.
- **Controls and comparison.** Date range and dimension filter controls become Omni controls; a scorecard comparison period becomes an Omni comparison on the KPI tile.
- **Parity link.** For every created tile, fill `target_object` in the matching Route C contract under `migration/parity/looker_studio/<report_id>/recordings/<key>/contract.yaml`, and its `field_map` from recording column to Omni field.


### Step 1: Resolve the batch

Read `migration/bi_migration_batches.csv` and keep `batch_kind: content` rows. `--batch <id>` selects one batch (`b05` or `5`); `--all` processes every content batch not in `artifacts.omni_content.batches_complete`; no flag selects the lowest incomplete one. Confirm the batch's `depends_on_batch` (a model batch) is in `artifacts.omni_model.batches_validated`; stop and name it otherwise.

Rows with `ruling: drop` are excluded and their register rows set to `state: removed`. Rows with `ruling: redesign` are planned only when the plan document carries the redesigned tile list for that dashboard; otherwise they are parked (`kind: ruling`) and skipped this run.

### Step 2: Read each dashboard from Looker

For each dashboard row, fetch the definition through the Looker API: `dashboard(id)` for elements, filters and layout; each element's `query` or `result_maker` for fields, filters, sorts, pivots, limits, table calculations and visualisation config; `dashboard_filters` and each element's `listen` map. Omni's `looker_dashboard_inspect.py` (see `wire/bi_pairs/looker_to_omni/tooling.md`) prints the same structure and may be used as the extractor. For a Look, fetch `look(id).query` and treat it as a one-tile dashboard.

Record the raw definition alongside the plan (`migration/omni_content/<batch_id>/source/<dashboard_id>.json`) so validate and parity can re-derive from it without another Looker call.

### Step 3: Map every tile

For each tile, in this order:

1. **Fields.** Map each Looker `view.field` to the Omni `view.field` on the branch. The view name is the emitted view's name (the converter preserves it unless the plan renamed it, in which case the plan's rename table applies); a dimension group timeframe `created_month` maps to `created_at[month]`. A field that does not exist on the branch skips the tile with reason `unmapped_field`, naming the field. Do not substitute a similar field.
2. **Filters.** Tile filters and dashboard filters become Omni filter objects (`{ "kind": "EQUALS", "type": "string", "values": [...] }`, `{ "type": "date", "kind": "TIME_FOR_INTERVAL_DURATION", ... }`), never the shorthand string. A filter expression the mapping table does not cover skips the tile with reason `unmapped_filter`.
3. **Table calculations.** Arithmetic and `CASE`-shaped calculations become Omni `calculations`; a calculation referencing `pivot_where`, `offset`, or another calculation is `unsupported_calc`.
4. **Visualisation.** Map the Looker `type` to `chartType` and `visType` through `content_mapping.md`, with the chart spec nested under `visConfig.visConfig.config` and `prefersChart: true`. A pivoted bar becomes a stacked bar with the pivot dimension in `query.pivots`. A type with no mapping row becomes `chartType: table` and the tile is flagged `fidelity: table_fallback`, never skipped.
5. **Text and markdown tiles.** Plain markdown becomes an `inline-text` content item in `containers`. Markdown containing Liquid (`{{ }}` or `{% %}`) is skipped with reason `liquid`; Omni's Mustache namespaces differ and the rewrite is a hand job, listed in the report.
6. **Query collection.** Every tile query carries the full required set: `table`, `fields`, `join_paths_from_topic_name` (the topic name), `limit`, `sorts`, `filters`, `pivots`, `calculations`, `column_totals`, `row_totals`, `fill_fields`, `userEditedSQL`. No `modelId` in a tile query.

### Step 4: Map controls and layout

Dashboard filters become `controls.data` entries with `config.type` by filter kind (`date`, `string`, `number`, `boolean`). Each element's `listen` map becomes the control's `map`: tile keys the filter applies to, with a field remap where the Looker filter listened on a different field. A tile the filter did not listen to is excluded with `{ "<tileKey>": false }`.

The layout becomes a full `containers` tree from the Looker element positions (row, column, width, height on the 24-column grid, scaled to Omni's grid per `content_mapping.md`). Auto-layout places only the first tile, so the tree is authored in full for every tile and every text item.

### Step 5: Write the plan

`migration/omni_content/<batch_id>/plan.json`:

```json
{
  "batch_id": "b05",
  "model_batch": "b01",
  "branch_id": "<bi_migration.omni_branch>",
  "dashboards": [
    {
      "source_id": "42", "source_type": "dashboard", "title": "Store Performance", "folder": "Retail",
      "ruling": "parity", "collision": false,
      "body": { "queryPresentations": {"data": {}, "order": []}, "controls": {"data": {}, "order": []}, "containers": [], "settings": {} },
      "tiles_planned": 9,
      "skipped": [
        {"element_id": "7", "title": "Notes", "reason": "liquid", "detail": "{{ _filters['orders.created_date'] }} in markdown"},
        {"element_id": "9", "title": "Margin %", "reason": "unmapped_field", "detail": "orders.margin_pct not on branch (needs_human nh-014)"}
      ],
      "fidelity": [{"element_id": "3", "note": "table_fallback: looker_waterfall has no Omni chartType"}]
    }
  ]
}
```

The plan is complete when every in-scope dashboard has either a body or a parked ruling, and every skipped tile has a reason from the closed set `text_tile`, `liquid`, `unsupported_calc`, `unmapped_field`, `unmapped_filter`. Write `manifest.csv` with one row per dashboard, `state: planned`.

Update `omni_content.md` and status.md (Step 7), then output:

```
Plan written for batch <batch_id>: <N> dashboards, <N> tiles planned, <N> skipped.
Nothing has been written to Omni. Next:
/wire:omni-content-validate $ARGUMENTS --batch <batch_id>
then /wire:omni-content-generate $ARGUMENTS --batch <batch_id> --write
```

Stop here unless `--write` was passed.

### Step 6: Write step (`--write`)

Refuse unless `artifacts.omni_content.plan_validated` lists this batch and `omni_model review: approved`. For each dashboard with `collision: false` and a body:

```bash
omni documents v2-create <bi_migration.omni_model_id> "<title>" --body "$(cat migration/omni_content/<batch_id>/bodies/<source_id>.json)"
```

The body is one JSON object with nested slices, never stringified slices. Capture the returned `identifier`; read it back with `omni documents v2-get <identifier>` and confirm the tile count equals `tiles_planned` and every control is present. Move the document to the plan's folder with `omni documents move`. Record `target_identifier`, `target_url` and `state: created` in `manifest.csv`. A create that fails records `state: failed` with the error text and continues with the next dashboard; it does not retry blindly.

Omni's `omni_dashboard_builder.py` may be used as the write mechanism instead of the CLI call above when the engagement has it installed (see `wire/bi_pairs/looker_to_omni/tooling.md`); the plan body is the input either way, and the read-back check is the same.

Advance register rows: the dashboard row (`object_type: dashboard`) and its tile rows (`object_type: tile`) to `state: migrated`, skipped tiles to `state: deferred` with the reason in `notes`.

### Step 7: Update the summary and status

`migration/omni_content/omni_content.md`:

```markdown
## Batch summary

| Batch | Dashboards planned | Created | Tiles planned | Skipped: text | liquid | calc | field | filter | Table fallbacks |
|---|---|---|---|---|---|---|---|---|---|
| b05 | 6 | 6 | 47 | 3 | 2 | 1 | 2 | 0 | 4 |

## Hand-finish list
| Dashboard | Element | Reason | What to do in Omni |
```

```yaml
artifacts:
  omni_content:
    generate: complete          # complete only when every content batch has state created for all its dashboards
    file: migration/omni_content/omni_content.md
    generated_date: "{{TODAY}}"
    batches_total: N
    batches_complete: [b05]
    plan_validated: [b05]       # written by omni-content-validate
    dashboards_planned: N
    dashboards_created: N
    tiles_skipped: N
```

### Step 8: Output next command

After a write:
```
Batch <batch_id> created in Omni: <N> documents. Hand-finish list: <N> items.
Next: /wire:omni-content-validate $ARGUMENTS --batch <batch_id>   (post-write checks)
then /wire:bi-equivalency-validate $ARGUMENTS --batch <batch_id>
```

## Under the release director model

This command is one **content batch** lane. The brief owns `migration/omni_content/<batch_id>/` and its state file, and carries no warehouse budget line. Each dashboard is one item for the resume contract: a killed lane resumes at the first dashboard with no `state` in the manifest. The lane reports once per step (plan written; write complete) with the skipped and hand-finish counts, and parks the collision and redesign rulings it cannot make.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/plan.json`
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/bodies/<source_id>.json` (one per dashboard)
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/source/<dashboard_id>.json` (raw Looker definitions)
- `.wire/releases/$ARGUMENTS/migration/omni_content/<batch_id>/manifest.csv`
- `.wire/releases/$ARGUMENTS/migration/omni_content/omni_content.md`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact_id, `Omni Content` as artifact_name, and the `file` value from `artifacts.omni_content` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_content` as artifact, `generate` as action.
