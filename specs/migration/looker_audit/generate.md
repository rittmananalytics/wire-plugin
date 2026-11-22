---
wire_schema: "1.0"
command: generate
artifact: looker_audit
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
mcp_contextual:
  - looker
produces:
  - type: document
    path: "audit/looker_audit.md"
    description: "Looker estate audit: model constructs and content, each with a translation class"
  - type: report
    path: "audit/looker_model_catalog.csv"
    description: "One row per LookML view, explore, join, field, set, filter and parameter with construct, translation_class and complexity"
  - type: report
    path: "audit/looker_content_catalog.csv"
    description: "One row per dashboard, Look, tile, schedule, alert and folder with usage and translation_class"
preconditions: []
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Catalog the Looker estate (LookML model constructs and dashboards, Looks, schedules, usage) and classify every construct as mechanical, assisted, redesign or drop for the move to Omni"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: looker_audit` and `artifact_file_path: audit/looker_audit.md` before proceeding.

---

# Looker Audit: Generate

## Purpose

Catalogs the client's Looker estate so the migration plan can decide what moves to Omni and how. Two halves:

1. **The model.** Every LookML view, explore, join, dimension, dimension group, measure, filter field, parameter and set in the repo at `bi_migration.lookml_repo_path`, each classified by how it translates to Omni YAML.
2. **The content.** Every dashboard, Look, tile, schedule, alert and folder, read through the Looker API or the Looker MCP, with usage from System Activity so the plan can rank by use.

The classification is the four-class rule from the Looker to Omni pair (`wire/bi_pairs/looker_to_omni/translation_guide.md`). It is deterministic: the same construct always gets the same class. The audit does not decide what to migrate. That is the plan's job. The audit records what is there and what each thing would cost to move.

This is a **BI-tool** audit. It does not read the warehouse, and it does not depend on any warehouse migration audit. The warehouse does not move in a `bi_migration` release.

## Prerequisites

- Release folder with `project_type: bi_migration` in `status.md`
- The LookML repo available to Wire in one of two ways, preferred first:
  - `migration_sources.lookml` registered (`/wire:migration-source-register $ARGUMENTS lookml <github url>`) and refreshed (`/wire:migration-source-refresh $ARGUMENTS lookml`), so the audit reads the snapshot at `migration_sources.lookml.local_snapshot_path` and stamps `migration_sources.lookml.last_commit` on every row
  - `bi_migration.lookml_repo_path` set to a local read-only checkout, for a repo Wire cannot clone
- Looker API access for content and usage: `LOOKERSDK_BASE_URL`, `LOOKERSDK_CLIENT_ID`, `LOOKERSDK_CLIENT_SECRET`, or the Looker MCP server connected. System Activity access is needed for usage fields; without it the usage columns are written as `unknown`, never guessed.

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- The LookML repo at `migration_sources.lookml.local_snapshot_path` (or `bi_migration.lookml_repo_path` when no source is registered)
- The Looker instance at `bi_migration.looker_base_url`, via the Looker API or MCP
- `wire/bi_pairs/looker_to_omni/feature_detection.md` (the regexes that drive classification)
- `wire/bi_pairs/looker_to_omni/translation_guide.md` (the construct table and classes)
- `.wire/engagement/bi_pair_overrides/looker_to_omni/` (optional engagement overrides, layered over the canonical pair files)

## Workflow

### Step 1: Locate the release

Confirm `project_type: bi_migration` and `bi_pair: looker_to_omni` in `status.md`.

Resolve the LookML path: `migration_sources.lookml.local_snapshot_path` when `migration_sources.lookml` is registered and `last_refreshed` is set (run `/wire:migration-source-refresh $ARGUMENTS lookml` first if it is not), otherwise `bi_migration.lookml_repo_path`. Record `lookml_commit`: `migration_sources.lookml.last_commit` when the snapshot is used, `git -C <path> rev-parse HEAD` when the local path is a git checkout, else `null` with a note that drift detection will not be available. If neither source is set or the resolved path does not exist, stop and output:

```
bi_migration.lookml_repo_path is not set or the path does not exist.
Set it in status.md (a local checkout of the LookML repo) and re-run:
/wire:looker-audit-generate $ARGUMENTS
```

If `audit/looker_audit.md` already exists, ask whether to re-generate (overwrite) or update (append new items only).

### Step 2: Parse the LookML repo

Parse every `.lkml` and `.lookml` file under the repo path with the `lkml` grammar (the same parser `wire/scripts/lookml_to_omni.py` uses). Resolve `include:` statements within the repo only. Collect:

| Object | What to record |
|---|---|
| `view` | name, `sql_table_name` or `derived_table`, `extends`, whether it is a refinement (`view: +name`) |
| `explore` | name, `from` or `view_name`, `fields`, `sql_always_where`, `always_filter`, `conditionally_filter`, `access_filter`, `extends`, `hidden` |
| `join` | explore, view, `from`, `sql_on`, `relationship`, `type`, `fields` |
| `dimension` | view, name, `type`, `sql`, `primary_key`, `hidden`, `label`, `group_label`, `view_label`, `value_format`, `value_format_name`, `tiers`, `case`, `html`, `links`, `drill_fields` |
| `dimension_group` | view, name, `type` (`time` or `duration`), `timeframes`, `intervals`, `sql`, `sql_start`, `sql_end` |
| `measure` | view, name, `type`, `sql`, `filters`, `value_format_name`, `drill_fields`, `hidden` |
| `filter`, `parameter` | view, name, `type`, `allowed_value`, `default_value`, where each is referenced |
| `set` | view, name, member fields |
| `datagroup`, `persist_with`, `datagroup_trigger`, `sql_trigger_value`, `persist_for` | where they appear |

Merge refinements into their base view before classification, and record the merge in the catalog `reason` column (`refined by <file>`). A construct that references a view or field the parser cannot resolve is recorded with `complexity: High` and `reason: unresolved reference`, never dropped.

### Step 3: Classify every model construct

Apply the feature-detection regexes, then the four-class rule. One class per row:

| Class | Meaning |
|---|---|
| `mechanical` | The converter emits it with no human entry: plain column dimensions, `${field}` and `${view.field}` SQL, `type: time` dimension groups whose timeframes all map, `type: duration` groups, measures with a mapped aggregate type, simple measure filters, `tier` dimensions, `hidden`, `label`, `description`, `group_label`, `view_label`, `primary_key`, `value_format_name` in the mapping table, explore `from` or `view_name`, joins with `many_to_one` or `one_to_one` and `left_outer`, explore `fields` lists, `extends`, `sets` |
| `assisted` | The converter emits a best-effort mapping plus a `needs_human` entry: `type: number` measures, `case` dimensions where every `when` is an equality test, `sql_always_where`, `always_filter`, `conditionally_filter`, `access_filter`, `links`, `drill_fields` across views, custom `value_format` strings not in the table, `${other_view.field}` references in a view field's SQL, a `dimension_group` whose name collides with a dimension |
| `redesign` | No emission; the row carries the reason: Liquid (`{% %}` or `{{ }}`) in `sql`, `html` or `label`; `parameter` and `filter` fields; PDTs (`datagroup_trigger`, `sql_trigger_value`, `persist_for`, `materialized_view`); `sql_table_name` containing Liquid; native derived tables; `html`; timeframes with no Omni equivalent; symmetric-aggregate measures on a view with no primary key |
| `drop` | Not used for model rows. A view or explore with no content referencing it is still `mechanical`, `assisted` or `redesign`; the plan decides whether to carry it |

Assign `complexity`: `Low` for `mechanical`, `Medium` for `assisted`, `High` for `redesign` or any unresolved reference. Every `redesign` row must have a non-empty `reason`.

### Step 4: Catalog content and usage

Through the Looker API (`all_dashboards`, `all_looks`, `dashboard(id)` for tiles and filters, `scheduled_plans`, `alerts`, `all_folders`) or the Looker MCP equivalents, record one row per object with the catalog columns in Step 6. For each dashboard and Look, record every explore and field its tiles reference (`explore_refs`, `fields_refs`) so the plan can tie content batches to model batches.

Usage comes from System Activity (`history` and `content_usage` explores): `last_viewed` and `views_90d` per dashboard and Look. If System Activity is not accessible, write `unknown` in both columns and record `usage_source: unavailable` in `status.md`. Never infer usage from folder names or titles.

Text and markdown tiles are recorded with `has_text_tile: true` on their dashboard and their own tile rows carry `translation_class: drop` with `reason: text tile, recreate by hand`. Every other content row is `translation_class: mechanical` at this stage; the plan may re-rule it `redesign` or `drop`.

### Step 5: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/looker_audit.md`

Include:
- Summary table: views, explores, fields (dimensions, dimension groups, measures), filters and parameters, joins, sets; dashboards, Looks, tiles, schedules, alerts, folders
- Classification breakdown: model rows by class and complexity; content rows by class
- Usage distribution: dashboards ranked by `views_90d`, the count that carries 80% of views, dashboards and Looks with zero views in 90 days
- Redesign register: every `redesign` row with its reason, grouped by construct (Liquid, parameters, PDTs, html, unmapped timeframes)
- Explore to content map: which dashboards and Looks reference each explore
- Unresolved references: every construct the parser could not resolve
- Text and markdown tiles, per dashboard
- Usage source and any access gaps

### Step 6: Write the catalogs

`audit/looker_model_catalog.csv` columns, in this order: `object_type` (`view` | `explore` | `dimension` | `dimension_group` | `measure` | `filter` | `parameter` | `join` | `set`), `object_uri`, `view_name`, `explore_name`, `field_name`, `construct`, `translation_class`, `complexity`, `reason`, `lkml_file`, `line`, `lookml_commit`.

`audit/looker_content_catalog.csv` columns, in this order: `object_type` (`dashboard` | `look` | `tile` | `schedule` | `alert` | `folder`), `object_uri`, `id`, `title`, `folder`, `owner`, `last_viewed`, `views_90d`, `source_updated_at` (the Looker API `updated_at`; the baseline `migration-drift-generate` compares against), `tile_count`, `explore_refs`, `fields_refs`, `has_text_tile`, `translation_class`, `reason`.

Both files are written in full on every run. Rows are sorted by `object_type` then name or id, so a re-run produces a stable diff.

**Identities.** `object_uri` is the object's stable name across the whole release, in the same namespace the converter uses for its intermediate representation, so plan, drift, parity and the Omni-side manifest all join on it: `looker:<project>:view:<name>`, `looker:<project>:field:<view>:<field>`, `looker:<project>:explore:<name>`, `looker:<project>:join:<explore>:<join>`, `looker:<project>:dashboard:<id>`, `looker:<project>:dashboard:<id>/element:<element_id>`, `looker:<project>:look:<id>`, `looker:<project>:schedule:<id>`, `looker:<project>:folder:<id>`. `<project>` is the LookML project name; a Looker title or file path is never an identity, because both change.

### Step 6b: Write the dependency edges

`audit/dependencies.jsonl`: one JSON object per line, `{"from": <object_uri>, "to": <object_uri>, "kind": <kind>}`, sorted by `kind`, `from`, `to`. Kinds on the content side: `contains` (dashboard to element, dashboard to filter), `uses_explore` (element or look to explore), `references` (element or look to field, including filter fields and pivots, and each `dynamic_fields` entry's inputs), `listens` (element to dashboard filter). The converter writes the model side of the same graph (`view` contains `field`, `field` references `field`, `topic` base_view and joins) per batch, so the union answers "which dashboards does this view change reach" without re-parsing anything. `migration-drift-generate` reads both.

### Step 7: Update status

```yaml
artifacts:
  looker_audit:
    generate: complete
    file: audit/looker_audit.md
    generated_date: "{{TODAY}}"
    view_count: N
    explore_count: N
    field_count: N
    dashboard_count: N
    look_count: N
    tile_count: N
    mechanical_count: N
    assisted_count: N
    redesign_count: N
    drop_count: N
    usage_source: system_activity | unavailable
    generated_files:
      - audit/looker_audit.md
      - audit/looker_model_catalog.csv
      - audit/looker_content_catalog.csv
```

### Step 8: Output summary

Print the totals, the class breakdown, the 80% usage cut, the redesign count, and the next command:

```
/wire:looker-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/looker_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/dependencies.jsonl`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_audit` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_audit` as artifact_id, `Looker Audit` as artifact_name, and the `file` value from `artifacts.looker_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_audit` as artifact, `generate` as action.
