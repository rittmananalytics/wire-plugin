---
wire_schema: "1.0"
command: generate
artifact: dbtcharts
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--subject-area <folder>[,<folder>] scaffolds and designs only the named warehouse folders (default: every folder); --auto designs every board to completion without pausing for decisions, one lane per subject area; --theme <name>, --currency <symbol>, --title <text>, --logo <path> pass through to the scaffold's meta.yml and landing page; --no-warehouse skips the warehouse dry-run, the profiling and the renders; --force overwrites boards that already exist under charts/"
preconditions:
  - artifact: dbt
    action: validate
    outcome: PASS
auto_validate: false
produces:
  - type: document
    path: "<dbt_project_path>/charts/<subject_area>.yml"
    description: "One dbt Charts board per warehouse subject area, read through ref() from the dbt models"
  - type: document
    path: "<dbt_project_path>/dbt_charts.yml"
    description: "The dbt Charts project anchor with a dbt_profile source; written only if absent"
  - type: document
    path: "<dbt_project_path>/charts/meta.yml"
    description: "Project-wide board defaults (theme, frame width); written only if absent"
  - type: document
    path: "<dbt_project_path>/charts/index.yml"
    description: "The landing page dct serves at /, one card per board, optional logo; written only if absent"
  - type: report
    path: "dev/dbtcharts_generation_report.md"
    description: "What the scaffold proposed, what the agent kept, changed or dropped, and every needs_human item with its resolution"
delegates_to:
  - utils/precondition_gate
  - utils/semantic_layer_developer_delegate
  - utils/stale_artifact_check
  - utils/jira_sync
  - utils/docstore_sync
description: Generate dbt Charts boards, one per warehouse subject area, from the dbt manifest and catalog — a deterministic scaffold inventories the models, the agent designs each board into a dashboard (KPI row with deltas, hero trend, breakdowns, table), dct validates and renders them; --auto runs the design for every subject area without pausing
argument-hint: <release-folder> [--subject-area <folder>[,<folder>]] [--auto] [--theme <name>] [--currency <symbol>] [--title <text>] [--logo <path>] [--no-warehouse] [--force]
workload: judgment
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbtcharts Generate Command

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below, **unless `--auto` is given**. An auto run is a fan-out of one lane per subject area, and the orchestrating session dispatches those lanes itself under the lane contract in `specs/utils/director_operating_model.md` (Step 5); wrapping the whole run in one specialist agent that then spawns the lanes hides a stall from the orchestrator, because nothing records progress until that agent returns.

## Purpose

Produce a first set of dashboards for a release's warehouse layer in [dbt Charts](https://dbtcharts.com): YAML boards that live in the dbt project next to the models, query them through `ref()`, are validated by the `dct` CLI and rendered by it. One board per **subject area**, where a subject area is a folder under the warehouse layer (`models/warehouse/w_sales/`, `models/warehouse/wh_finance/`), which is how Wire's dbt conventions and most client projects already group facts and dimensions.

The command is in two halves, and the line between them is fixed:

1. **The scaffold is deterministic.** `scripts/dbtcharts_scaffold.py` reads dbt's own artifacts (`target/manifest.json`, and `target/catalog.json` for column types), classifies every model and column from the naming conventions (`_fact`/`_dim`/`_xa`, `_dt`/`_ts`, `_amount`, `_pk`/`_fk`, `is_`/`has_`/`was_` booleans with or without an entity prefix, as in `is_active` and `user_is_active`), and writes the boards: for each fact a KPI row (record count and up to three formatted measures), a 24-month trend and a top-10 breakdown; for each dimension a record count and a breakdown. It also writes `charts/meta.yml` (theme, frame width) and `charts/index.yml` (the landing page) once. The same manifest and catalog always produce the same boards. Everything it could not decide goes to `needs_human.json` with a reason. Do not hand-write what it emits, and do not "improve" its SQL by hand before it has run.
2. **The design is judgement.** The scaffold's board is an inventory: one KPI per column, one line per month, one bar per category, for every table. Step 5 turns each into a dashboard to the shape in `skills/dbtcharts/board-design-brief.md`: the tables that matter, a KPI row with prior-period deltas, one hero trend over the last 24 months, a few breakdowns, a detail table, business names, and the data profiled first so nothing charts a null column. With `--auto` this runs to completion for every subject area, one lane each, without pausing for decisions; without it, the agent pauses per board where a choice is not obvious. Either way every choice is recorded, chart by chart, in the generation report.

`auto_validate: false`: the validate step runs `dct validate --warehouse`, a per-query dry run against the warehouse, so it is a separate command and a separate decision, as `dbt-validate` is.

## Usage

```bash
/wire:dbtcharts-generate 01-dbt-foundation
/wire:dbtcharts-generate 01-dbt-foundation --auto                  # design every board to completion, one lane per area
/wire:dbtcharts-generate 01-dbt-foundation --subject-area w_sales  # one subject area (its facts and the dimensions they join)
/wire:dbtcharts-generate 01-dbt-foundation --auto --currency '£' --theme vivid --title "Acme Warehouse" --logo docs/logo.svg
/wire:dbtcharts-generate 01-dbt-foundation --no-warehouse          # under warehouse_spend: none
/wire:dbtcharts-generate 01-dbt-foundation --force                 # rewrite boards that already exist
```

`--subject-area` takes the warehouse folder (`w_sales`) or its slug (`sales`). The board for an area covers every fact model in that folder and the dimensions those facts join to, regardless of the folder the dimension lives in (`wh_company_dim` from `w_crm` is charted on the sales board when `wh_deal_fact` refs it or carries `company_fk`; the CRM board still carries it too).

## Prerequisites

- `dbt`: `validate: PASS` (enforced by the precondition gate). The boards read the models; unbuilt or failing models give charts of nothing.
- The `dct` CLI (`uv tool install dbt-charts`, or `pip install dbt-charts`). Step 2 checks and stops with the install line if it is missing.
- A dbt profile the boards can read through. `dbt_charts.yml` points at it by name; no credential is ever written into a board.

## Inputs

| Input | Where it comes from | Required |
|---|---|---|
| The dbt project | `status.md` `dbt_project_path` (or `migration.dbt_project_path`), else `dbt/`, `dbt_project/` or the repository root, whichever holds `dbt_project.yml` | always |
| `target/manifest.json` | `dbt parse` in that project (Step 3) | always |
| `target/catalog.json` | `dbt docs generate` in that project (Step 3); optional under `warehouse_spend: none` | recommended |
| `design/visualization_catalog.md`, `design/dashboard_visualization_catalog.csv` | `viz_catalog-generate`, `mockups-generate` | `dashboard_first` |
| The dashboards section of `requirements/requirements_specification.md` | `requirements-generate` | `full_platform`, `dbt_development` when present |
| `business_rules/register.md` | `business-rules-generate` | when present: measure names and definitions |
| `.wire/conventions/dbt.yml` or the framework default | conventions | always |
| `.wire/conventions/dbtcharts.yml` or `wire/conventions/dbtcharts.yml` | design conventions: theme, currency, windows, board shape, chart defaults, formats, naming and layout rules | always |
| `budget.warehouse_spend` | `status.md` | always |

## Workflow

### Step 1: Resolve the dbt project and the subject areas

1. Read `status.md`. Resolve `dbt_project_path` in the order given in Inputs. If no `dbt_project.yml` is found at any candidate, stop:

   ```
   Cannot generate dbt Charts boards without a dbt project.
   Paths checked: <each path>/dbt_project.yml
   Set dbt_project_path in status.md and re-run.
   ```

2. Resolve the warehouse layer path: `.wire/conventions/dbt.yml` `layers.warehouse.path` if the convention file names one, else `models/warehouse`. List its immediate subfolders; these are the subject areas. Models sitting directly in the layer folder are grouped by their `wh_<group>__` prefix, else under the layer folder's own name. A subject area's board covers the fact models in its folder **plus the dimensions those facts join to, wherever they sit**: the scaffold finds them from the manifest (the fact `ref()`s the dimension) and the catalog (a fact `<x>_fk` column matching a dimension's `<x>_pk`), and marks each one in `scaffold_summary.json` with `linked_from` and `linked_via`. A dimension can therefore appear on more than one board; its own folder's board still carries it.
3. Apply `--subject-area` if given. A name that matches no folder stops the command and lists the folders that exist.
3a. **Resolve the design convention.** `.wire/conventions/dbtcharts.yml` in the engagement repo if present (the client's house style wins), else the framework's `wire/conventions/dbtcharts.yml` (synced from the process registry; see `wire/schemas/convention-schema.md`). Read `presentation` (theme, frame width, currency, landing page title and logo), `windows` (KPI period, event period, trend months, stopped-feed anchor), `board_shape`, `chart_defaults`, `formats`, `render` and `profiling`. A command flag (`--theme`, `--currency`, `--title`, `--logo`) overrides the convention for this run and the report says so. Record which file resolved.
4. Say what will happen before it happens, in one sentence and a table: the subject areas, the model count in each, and whether the catalog will be generated (Step 3).

### Step 2: Check the dct CLI

Run `dct --version`. If it fails, stop:

```
dbt Charts CLI not found. Install it, then re-run:
  uv tool install dbt-charts      # or: pip install dbt-charts
```

Record the version in the generation report. Do not substitute another renderer; the deliverable is board YAML that `dct` validates and renders.

### Step 3: Produce the dbt artifacts the scaffold reads

In the dbt project directory:

1. `dbt deps` then `dbt compile` for `target/manifest.json`. `dct` derives model columns from `compiled_code`; a bare `dbt parse` writes none, and every Jinja-wrapped model then comes back as "contains no SELECT statement". Compile needs the profile but runs no model.
2. `dbt docs generate` for `target/catalog.json`, which is where column **types** come from. This reads the warehouse's information schema. Skip it when `budget.warehouse_spend` is `none` or `--no-warehouse` was passed, and say so: without the catalog the scaffold classifies columns by name convention only, and models with no `schema.yml` columns are reported as `no_column_metadata` rather than charted.

Use the release's dbt profile and target as `dbt-validate` does. A manifest older than the newest model file is regenerated, never reused.

3. **Keep `target/manifest.json` still while `dct` reads it.** On dbt Fusion every `dbt show` rewrites `target/manifest.json`, and `dct validate` and `dct render` read that file, so a lane profiling with `dbt show` while another lane or the orchestrator renders makes the render fail with `ERR-DBT-MANIFEST-UNREADABLE`. Every `dbt show` run during Step 5 therefore passes `--target-path <scratch dir>` (one directory per lane, outside the project's `target/`), and the orchestrator runs `dbt compile` once more before Step 6 so the shared manifest is current.

### Step 4: Run the scaffold

```bash
python3 <plugin>/scripts/dbtcharts_scaffold.py \
  --manifest <dbt_project_path>/target/manifest.json \
  --catalog  <dbt_project_path>/target/catalog.json \
  --out      <dbt_project_path>/charts \
  --layer-path <layer path from Step 1> \
  --dialect  <bigquery | snowflake | postgres | duckdb | redshift, from the dbt profile type> \
  --write-anchor <dbt_project_path>/dbt_charts.yml --profile <profile> --target <target> \
  --theme <presentation.theme> --currency <presentation.currency> --frame-width <presentation.frame_width> \
  --trend-months <windows.trend_months> --breakdown-limit <chart_defaults.ranking.limit> \
  --kpi-row-height <board_shape.kpi_row_height> \
  [--title <presentation.landing_page.title>] [--logo <presentation.landing_page.logo>] \
  [--subject-area <folders>] [--force]
```

The presentation flags carry the resolved convention's values (Step 1, 3a); a command flag given by the user overrides the convention's value. The scaffold itself reads no convention file and stays standard-library only.

The scaffold writes one board per subject area to `<dbt_project_path>/charts/<subject_area>.yml` (the folder name with its `w_`/`wh_` prefix stripped: `w_sales/` becomes `charts/sales.yml`), the anchor to `<dbt_project_path>/dbt_charts.yml` when none exists, and `charts/meta.yml` and `charts/index.yml` when absent. The anchor holds the sources registry only; dct 0.8 rejects any other key there. `--currency` defaults to `$` because that is the only symbol dct's presets carry; a GBP or EUR client passes its symbol and the scaffold switches to prefix formats. Read `charts/scaffold_summary.json` (boards, models, the date, measure and dimension columns chosen for each, chart counts) and `charts/needs_human.json` (every model not charted or charted with a gap: `unknown_role`, `no_column_metadata`, `no_date_column`, `no_measure_column`, `no_breakdown_dimension`, `empty_subject_area`).

The scaffold never overwrites an existing board without `--force`. A board the consultant has already curated is not regenerated silently; the summary lists it under `skipped_existing`, and the report says so.

### Step 5: Design each board

This is the judgement half. Work board by board to `skills/dbtcharts/board-design-brief.md`, and record every change in the generation report as a row: `board`, `chart`, `scaffold proposed`, `kept | changed | dropped | added`, `why`.

**With `--auto`:** the orchestrating session dispatches one lane per subject area (one subagent each, all at once, within `lanes_max`), each with the lane brief template from `specs/utils/director_operating_model.md` filled in:

```
Lane:          dbtcharts [<area>]
Release:       <release folder>
Task:          design charts/<area>.yml to skills/dbtcharts/board-design-brief.md, using <resolved convention>
Owns:          <dbt_project_path>/charts/<area>.yml; .wire/releases/<release>/dev/dbtcharts/<area>.png; .wire/releases/<release>/lanes/dbtcharts-<area>.md
State file:    .wire/releases/<release>/lanes/dbtcharts-<area>.md
Resume:        Read the state file first; skip every completed item. Rewrite it after each completed item, not at the end.
Budget:        <warehouse_spend setting>
Flat:          Do not spawn sub-agents.
Status:        Do not write status.md or execution_log.md.
Report:        Report once, at completion, at a stall, or at a decision you cannot make.
```

Each lane receives the brief, the reference board if one is curated already, the scaffold's board and its rows in `scaffold_summary.json` and `needs_human.json`, and the tool notes (the `--target-path` rule from Step 3). Its items, in order, each written to the state file as it completes: profiled, designed (`charts/<area>.yml` rewritten in place), warehouse-validated, rendered and inspected, linted, and `complete` with the report rows (`board`, `chart`, `scaffold proposed`, `kept | reshaped | dropped | added`, `why`), the tables kept and dropped, the profiling findings and the `needs_human` decisions for its area. Nothing pauses; a choice the brief does not settle is made and recorded in the state file.

The orchestrator watches the state files, not the lanes: a lane with no writes for 30 minutes is stalled and its remaining items are re-dispatched to a fresh lane with the same brief, which the resume contract makes safe. When every lane's state file says `complete`, the orchestrator reads them all, then does Step 6 over the whole set. The generation report (Step 7) is assembled from the state files, so no lane's work exists only in a conversation.

**Without `--auto`:** the same work, board by board in the foreground, pausing where the brief does not settle a choice (which fact leads the board, which of two measures is the headline) and asking.

0. **Profile.** `dbt show --inline` over each candidate model: null rates, distinct counts, date coverage, whether the feed still loads. A column that is mostly null, all zero, or a single snapshot is not charted; a feed that has stopped anchors its windows on its last loaded month and the board `notes:` says so. Record what was dropped and why.
1. **Names.** Replace the scaffold's mechanical titles with the business names the release already uses: the measure's name in the business rules register, the requirement's wording, the viz catalog's `visualization_name`. A KPI's `label:` and every other chart's `title:` must read as a person would say it ("Deal value by pipeline stage", not "Deals by pipeline stage (deal_amount)").
2. **Shape.** Rebuild to the brief: 4 to 6 KPIs from one query with prior-period deltas; one hero trend over the last 24 months; two to four breakdowns; one detail table; about 8 visualisations; no section headings. Pick the tables that matter to the subject area and drop the rest (mappings, bridge tables, `_xa` models the release did not ask for, dimension record counts) and record why. A subject area that will not fit one screen is split into `tabs:` by fact, or a second board.
3. **Add what the release asked for.** Where a viz catalog or a requirements dashboards section exists, every row in it becomes a chart, mapped with this fixed table, and a row that cannot be mapped is recorded as unmapped, never dropped:

   | Catalog `chart_type` | dbt Charts `type` |
   |---|---|
   | `KPI tile`, `KPI`, `single value`, `stat` | `kpi` |
   | `line`, `spline` | `line` |
   | `area` | `area` |
   | `bar`, `column`, `vertical bar` | `bar` with `style.orientation: vertical` |
   | `horizontal bar`, `hbar` | `bar` (horizontal by default) |
   | `doughnut`, `donut`, `pie` | `pie` |
   | `table`, `grid`, `data table` | `table` |
   | `scatter` | `scatter` |
   | `map`, `geo` | `map` |
   | `heatmap` | `heatmap` |
   | `text`, `markdown`, `note` | a `text:` row |
   | `funnel`, `gauge`, `waterfall`, `sankey`, `treemap` | not drawable in dbt Charts: record as unmapped with the reason |

4. **Resolve `needs_human`.** For each item decide: chart it (write the query by hand only for these, still through `ref()`), leave it out, or send it back to the dbt work (a fact with no date column is usually a modelling gap). Record the decision. An item with no recorded decision fails validate.
5. **Follow the convention, the brief and the dbt Charts design skill.** The resolved convention (Step 1, 3a) sets the numbers: KPI count and period, trend months, ranking limit, table limit, layout row splits, chart type per question, format presets, currency handling. `skills/dbtcharts/board-design-brief.md` is the checklist for applying them; `dct skills board-design` and `dct docs` are the reference for chart choice and every field name; never guess a key. Formats go in the family slot (`style.value.format`, `style.number_format`, `style.columns.<col>.format`), money takes the release currency, trends set `axis_x.time_unit: yearmonth` and `axis_y.position: left`. Keep the scaffold's rules that validate depends on: every query reads a model through `{{ ref('...') }}`; no `type: values` inline data; every query and chart carries `notes:`; every KPI has `label:` and every other chart `title:`; the board's `source:` is a name in `dbt_charts.yml`, never a connection.
6. **Conventions.** Run `scripts/lint_conventions.py --domain dbt` over any model the curation exposed as mis-named; a chart cannot fix a column called `amt`.

### Step 6: Validate and render

0. `dbt compile` once more in the dbt project, so `target/manifest.json` is current and no lane is still writing it (Step 3, point 3). Nothing below runs while a lane's `dbt show` can touch that file.
1. `dct validate <dbt_project_path>/charts/` (structure and, with the manifest present, `ref()` names and model columns). Fix every error and re-run until there are none. Record warnings by code in the report; `WARN-DBT-MODEL-COLUMNS-UNRESOLVED` on a model whose SQL `dct` cannot derive columns from is expected and is cleared by the warehouse run.
2. Unless `--no-warehouse` or `warehouse_spend: none`: `dct validate charts/ --warehouse`. On BigQuery this is a dry run and is not billed; on Snowflake, Postgres and Redshift it is an `EXPLAIN`. Fix every error.
3. Unless `--no-warehouse` or `warehouse_spend: none`: render each board for the reviewer, `dct render charts/<board>.yml --format png --output .wire/releases/<release>/dev/dbtcharts/<board>.png`, and render `charts/index.yml` the same way. Renders run the queries; under `warehouse_spend: estimate_required` or a cap, the cost governance rules of `specs/utils/director_operating_model.md` apply and the run is disclosed in the report.
4. **Lint against the convention.** `python3 <plugin>/scripts/lint_conventions.py --domain dbtcharts --convention <resolved convention> --path <dbt_project_path>/charts/` and the same over `dbt_charts.yml`. Fix every error (missing titles, labels or notes; a `serve:` key in the anchor; a raw-string regex). Warnings (KPI label length or prefix, a `## Section` row, a hidden endpoint label, a trend without `time_unit`, `DATE_TRUNC(d, MONTH)`) are fixed where the brief agrees and otherwise recorded with a reason.
5. **Render clean.** `dct render` prints `WARN-*` codes for what a reviewer would see: `WARN-KPI-LABEL-TRUNCATED`, `WARN-CHART-TITLE-TRUNCATED`, `WARN-SERIES-LABEL-TRUNCATED`, `WARN-LIKELY-CURRENCY-OR-PERCENT-MISSING-FORMATTER`, `WARN-Y-ENCODING-MOSTLY-NULL`, `WARN-QUERY-RETURNED-ZERO-ROWS`, `WARN-TEMPORAL-SINGLE-POINT`. Fix each in the board (shorter label, a format, a different column, a narrower window) and re-render until only `WARN-DBT-MODEL-COLUMNS-UNRESOLVED` remains. Look at every PNG; the warnings do not see a wrong-side axis or a chart that is technically clean and tells nothing.

### Step 7: Write the generation report

`.wire/releases/<release>/dev/dbtcharts_generation_report.md`:

- dct version, dialect, source name, profile and target
- the design convention that resolved (engagement override or framework default) and any flag that overrode a value
- the subject-area table from Step 1 with boards written, skipped and empty
- the curation table from Step 5, assembled from the lane state files under `lanes/` on an `--auto` run
- the catalog mapping table where a viz catalog exists, with unmapped rows
- every `needs_human` item and its decision
- the profiling findings per board: columns and tables dropped, stopped feeds and the windows chosen
- the validate results (structure, warehouse, or `not run` with the reason), the render warning count per board, and the render paths (boards and landing page)

### Step 8: Update Status

```yaml
dbtcharts:
  generate: complete
  validate: not_started
  review: not_started
  generated_date: "{{TODAY}}"
  dct_version: "<x.y.z>"
  charts_dir: "<dbt_project_path>/charts"
  boards: []                 # one path per board written
  boards_skipped: []         # existing boards left alone (no --force)
  subject_areas: N
  charts_generated: N        # after design
  charts_scaffolded: N       # what the scaffold proposed
  design_mode: auto | guided # --auto lanes, or board by board in the foreground
  convention: ".wire/conventions/dbtcharts.yml | wire/conventions/dbtcharts.yml"   # which file resolved
  theme: vivid
  currency: "$"
  render_warnings: N         # across all boards, excluding WARN-DBT-MODEL-COLUMNS-UNRESOLVED; 0 to hand over
  needs_human: N             # items in needs_human.json
  needs_human_resolved: N    # must equal needs_human before validate can pass
  catalog_rows: N            # dashboard_first: viz catalog rows
  catalog_unmapped: N
  warehouse_validated: true | false | not_run
```

Then follow `specs/utils/stale_artifact_check.md` for artifacts downstream of this one.

### Step 9: Sync to Jira and the Document Store (Optional)

Follow `specs/utils/jira_sync.md` (artifact `dbtcharts`, action `generate`) and, if a document store is configured, `specs/utils/docstore_sync.md` with `artifact_id: dbtcharts`, `artifact_name: dbt Charts boards`, `file_path: .wire/releases/[release_folder]/dev/dbtcharts_generation_report.md`. A sync failure is logged and never blocks the command.

### Step 10: Report

```
## dbt Charts boards generated

**dct:**        <version> · dialect <dialect> · source <name> (profile <profile>, target <target>)
**Boards:**     N written under <charts_dir> (one per subject area), N skipped (existing)

| Subject area | Models | Charts proposed | Charts kept | needs_human |
|---|---|---|---|---|

### Design (<auto | guided>)
N charts scaffolded, N kept, N reshaped, N dropped, N added (viz catalog N), N needs_human items decided (N sent back to dbt)

### Validation
Structure: PASS / N errors fixed · Warehouse dry-run: PASS / not run (<reason>) · Renders: N PNGs under dev/dbtcharts/, N render warnings (0 to hand over)

### Next steps
1. /wire:dbtcharts-validate <release>
2. dct serve in <dbt_project_path> to walk the boards live
3. /wire:dbtcharts-review <release>
```

End with the commands that ran and the one that follows, in full (`specs/utils/director_operating_model.md` rule 7):

```
Ran: /wire:dbtcharts-generate <release> [flags]
Next: /wire:dbtcharts-validate <release>
```

## Edge Cases

### No `target/catalog.json` and models without `schema.yml` columns

The scaffold cannot see their columns and lists them as `no_column_metadata`. Either run `dbt docs generate` (Step 3) or document the models, then re-run. Do not write those boards by hand from memory of the SQL.

### A subject area folder with no fact or dimension

Reported as `empty_subject_area`; no board is written. Usually a folder of utility or mapping models; say so in the report.

### The client repository already has a `charts/` directory or a `dbt_charts.yml`

The anchor is never overwritten. Boards with the same file name are skipped without `--force`, and the report names them. Read the existing boards before curating; the scaffold's `source:` name must match a source the existing anchor declares.

### `warehouse_spend: none`

The catalog, the warehouse dry-run and the renders are skipped and each skip is named in the report and in `status.md` (`warehouse_validated: not_run`). The structural validation still runs. `dbtcharts-validate` records the warehouse check as `unverified`, which is not a pass.
