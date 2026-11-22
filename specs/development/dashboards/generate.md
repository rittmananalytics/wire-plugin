---
wire_schema: "1.0"
command: generate
artifact: dashboards
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Generate dashboards from design and requirements
argument-hint: <project-folder> [--slice <slice>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dashboards Generate Command

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.

## Purpose

Generate dashboards based on requirements and design specifications.

## Usage

```bash
/wire:dashboards-generate YYYYMMDD_project_name
```

## Prerequisites

Enforced by the precondition gate (`preconditions: dynamic` — see
`wire/release-types/<project_type>.yaml`), release-type dependent:

- **`full_platform`**: `semantic_layer`: `validate: PASS`. Dashboards here sit
  on top of the deployed semantic layer.
- **`dashboard_first`**: `seed_data`: `review: approved`. Dashboards here are
  built against seed data before the real dbt project exists — see
  `data_refactor` for the later swap to live data.

## Inputs

| Input | Where it comes from | Required |
|---|---|---|
| `design/dashboard_visualization_catalog.csv` | `mockups-generate` Step 4A | `dashboard_first`, `dashboard_extension` |
| `design/dashboard_spec.md` | `mockups-generate` Step 4A | `dashboard_first`, `dashboard_extension` |
| `design/mockups/*.html` | `mockups-generate` Step 3A | `dashboard_first`, `dashboard_extension` |
| `design/visualization_catalog.md` | `viz_catalog-generate` | `dashboard_first` |
| the semantic layer files | `semantic_layer-generate` | `full_platform`, `dbt_development` |
| `bi_tool`, `semantic_layer_project`, `semantic_layer_model` | `status.md` frontmatter | always |

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and reads and writes the named dashboard or tiles of the slice only
(`specs/utils/ticket_delivery.md`, "The `--slice` option"). Without
`--slice`, the workflow below runs as written.

1. The slice must be in `tickets.yaml`. If it is not, stop and list the valid
   slices.
2. The precondition gate evaluates this slice's dependencies, not the whole
   release's (`specs/utils/precondition_gate.md`, "Sliced runs").
3. Add or replace the slice's part only. Never regenerate the whole document
   or project to change one slice; every other line stays as it is.
4. On a ticket branch, write the step's result to the ticket record's front
   matter (`results:`) and the log row to the ticket run log
   (`iterations/<ticket>.execution_log.md`), not to `status.md` and
   `execution_log.md`. The status and Jira or Linear updates in the workflow
   below are made by `/wire:status-sync`'s ticket roll-up when the pull request
   merges.

## Workflow

### Step 1: Resolve the target and the tile source

Read `status.md`. Establish four things and **stop rather than guess any of them**:

1. **`project_type`** — decides which tile source applies (Step 2).
2. **`bi_tool`** — `looker` (default), `omni`, `oac`, `metabase`, `cube`. Routes Step 4.
3. **The semantic layer target** — the project, model and explore (or the equivalent in the
   BI tool) the dashboard is built on. Read from `status.md`
   (`semantic_layer_project`, `semantic_layer_model`, `semantic_layer_explore`) where present,
   otherwise from the approved `semantic_layer` artifact, otherwise **ask**.
4. **The output path** — the BI project directory the files belong in. Read from
   `status.md` (`bi_project_path`) or the approved deployment guide, otherwise **ask**.

If any of 3 or 4 cannot be resolved, stop:

```
Cannot generate dashboards without a semantic layer target and an output path.

Resolved so far:
  bi_tool:                  [value or MISSING]
  semantic_layer_project:   [value or MISSING]
  semantic_layer_model:     [value or MISSING]
  semantic_layer_explore:   [value or MISSING]
  bi_project_path:          [value or MISSING]

Set the missing values in status.md and re-run, or supply them now.
```

A dashboard written against a guessed model or into a guessed directory has to be found and
deleted by hand, which costs more than asking.

### Step 2: Resolve the tile list

The tile list is read, never invented. Where it comes from depends on `project_type`:

| `project_type` | Tile source | If absent |
|---|---|---|
| `dashboard_first`, `dashboard_extension` | `design/dashboard_visualization_catalog.csv`, one tile per row | stop, and name `mockups-generate` as the command that writes it |
| `full_platform`, `dbt_development`, `pipeline_only`, `enablement` | the dashboards section of `requirements/requirements_specification.md`, plus the approved `semantic_layer` field list | stop, and name the missing artifact |

Parse the catalog into one record per tile: `dashboard_page`, `visualization_name`,
`chart_type`, `measures`, `dimensions`. Column names vary slightly between runs, so match on
substring (`page`, `visualization`, `chart`/`type`, `measure`, `dimension`) exactly as
`viz_catalog-generate` Step 2 does.

**Every catalog row becomes exactly one tile.** A row you cannot map is reported, never dropped
silently. See Step 3.

### Step 3: Map each catalog row to a visualization type

`chart_type` in the catalog is mockup vocabulary. It has to be translated to the BI tool's
vocabulary. The mapping is fixed, so that two people generating from the same catalog produce
the same dashboard:

| Catalog `chart_type` | Looker `type` | Omni / OAC / Metabase equivalent |
|---|---|---|
| `KPI tile`, `KPI`, `single value`, `stat` | `single_value` | single value / scalar |
| `line`, `area`, `spline` | `looker_line` | line |
| `bar`, `column`, `vertical bar` | `looker_column` | column |
| `horizontal bar`, `hbar` | `looker_bar` | bar |
| `doughnut`, `donut`, `pie` | `looker_pie` | pie |
| `table`, `grid`, `data table` | `looker_grid` | table |
| `scatter` | `looker_scatter` | scatter |
| `map`, `geo` | `looker_map` | map |
| `funnel` | `looker_funnel` | funnel |
| `text`, `markdown`, `note` | `text` | text |

Matching is case-insensitive and ignores surrounding whitespace and hyphens.

**An unrecognised `chart_type` is not a guess.** Record the tile with
`type: looker_grid` (a table shows the underlying values without reshaping them), and add the row to
an `unmapped_tiles` list carried into Step 6 and the output summary. A table showing the right
numbers is recoverable; a silently-chosen chart type that misrepresents them is not.

### Step 4: Generate the dashboard files

One file per dashboard page in the catalog. Follow the BI tool's own conventions, which the
relevant skill defines: `looker-dashboard-mockup` and `lookml-content-authoring` for Looker,
`omni` for Omni, `dbt-to-smml` and `smml-semantic-modeling` for OAC, `metabase` for Metabase,
`cube` for Cube.

For **Looker**, write LookML dashboard files to
`<bi_project_path>/dashboards/<page-slug>.dashboard.lookml`:

- `layout: newspaper`, 24 columns.
- Preserve the mockup's tile order. KPI tiles first, then chart rows, then tables, matching the
  mockup's reading order rather than the catalog's row order where the two differ.
- Every tile carries `model`, `explore`, `type`, `fields`, and a `listen` block mapping each
  dashboard filter to the field it filters.
- Reference each measure and dimension by its **semantic layer field name**
  (`<view>.<field>`), resolved against the approved semantic layer. A field the semantic layer
  does not define is an unresolved tile, reported per Step 6, never invented as LookML.
- Filters come from the `dashboard_spec.md` "Filter Dimensions" section. Each becomes a
  `field_filter` with the default value the spec records.
- Carry the mockup's series colours where the catalog or spec records them, so the delivered
  dashboard matches the artifact the stakeholder approved.
- Add a comment on each tile naming the catalog row it came from, so the mapping is auditable
  after the fact.

### Step 5: Cross-check the dashboard against the approved mockup

Before writing status, compare what you generated against the mockup that was signed off:

| Check | Rule |
|---|---|
| Tile count | one generated tile per catalog row, no more and no fewer |
| Tile titles | match the catalog's `visualization_name` |
| Filters | every filter in `dashboard_spec.md` is present on the dashboard |
| Fields | every measure and dimension resolves to a real semantic layer field |

Differences are recorded, not silently accepted. A dashboard that renders but shows nine of
eleven approved tiles has failed at the thing the release type exists to protect.

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.dashboards section:
   ```yaml
   dashboards:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: "{{TODAY}}"
     bi_tool: looker | omni | oac | metabase | cube
     semantic_layer_model: "<model>"
     semantic_layer_explore: "<explore>"
     dashboard_files: []            # one path per generated dashboard page
     tiles_generated: N
     catalog_rows: N                # must equal tiles_generated
     unmapped_tiles: N              # chart_type not in the Step 3 table, rendered as a table
     unresolved_fields: N           # measures/dimensions with no semantic layer field
   ```

`tiles_generated` and `catalog_rows` are both recorded so a mismatch is visible in the status
file itself, not only in this run's console output.
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `dashboards`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `dashboards`
- `artifact_name`: `Dashboards`
- `file_path`: `.wire/releases/[release_folder]/dev/dashboards.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

**Output**:
```
## Dashboards Generated

**BI tool:**   [bi_tool]
**Model:**     [semantic_layer_model] · explore [semantic_layer_explore]
**Files:**     [one path per dashboard page]

### Coverage
Catalog rows:        N
Tiles generated:     N
Unmapped chart type: N   [list each: row name, the chart_type given]
Unresolved fields:   N   [list each: tile name, the field that does not exist]

### Mockup cross-check (Step 5)
[PASS, or one line per difference between the dashboard and the approved mockup]

### Next Steps

1. **Validate**: /wire:dashboards-validate <release>
2. Open the dashboard in [bi_tool] and confirm it renders against real data
3. **Review with stakeholders**: /wire:dashboards-review <release>
```

Any non-zero `unmapped_tiles` or `unresolved_fields` count is stated here and again in status.
A dashboard is not finished while either is above zero, and `dashboards-validate` fails on both.

## Edge Cases

### Semantic layer target or output path cannot be resolved

Step 1 stops rather than guessing. See the message there.

### A catalog row's chart_type is not in the Step 3 table

The tile renders as `looker_grid` and the row is reported in `unmapped_tiles`. The dashboard is
generated, and `dashboards-validate` Check 2 fails while any unmapped tile remains, so the
fallback cannot become the delivered dashboard by default.

### A measure or dimension does not exist in the semantic layer

The tile is recorded in `unresolved_fields` and is not written with an invented field name.
`dashboards-validate` Check 3 fails while any remains.

### The catalog is missing on a dashboard-first release

Stop and name `mockups-generate` as the command that writes it. Do not fall back to
`requirements_specification.md` on a release type whose tile source is the catalog: that
substitutes a different, unapproved tile list for the one the stakeholder signed off.

### Prerequisites not met

The precondition gate blocks first (`preconditions: dynamic`), naming the artifact and action
that is outstanding for this release type.

## Output

This command creates:
- One dashboard file per catalog dashboard page, at the resolved `bi_project_path`
  (for Looker: `<bi_project_path>/dashboards/<page-slug>.dashboard.lookml`)
- Updates `status.md` `artifacts.dashboards` with the file list, tile counts, and the
  `unmapped_tiles` / `unresolved_fields` counts
- Appends one row to `execution_log.md`
