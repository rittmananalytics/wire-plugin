# Looker to Omni: content mapping

How `/wire:omni-content-generate` turns Looker dashboards and Looks into Omni documents. The model must exist on the branch first: every tile field is resolved to an Omni `view.field` from the emitted model, and a tile with an unresolved field is skipped with reason `unmapped_field`, never guessed.

## Objects

| Looker | Omni | Notes |
|---|---|---|
| Dashboard | Document (`omni documents v2-create`) | One document per dashboard. Created through the v2 draft-and-publish surface, never v1. |
| Dashboard tile (query) | `queryPresentations.data.<key>` with `query` and viz config | `topicName` is the Omni topic that replaced the tile's explore. |
| Look | A single-tile document, or a tile on the dashboard that embeds it | The plan rules which. Default: a single-tile document in the same folder. |
| Dashboard filter | `controls.data.<id>` with `config.type` `date`, `string`, `number` or `boolean` | |
| Tile `listen` map | Control `map` entries binding the control to each tile's field | |
| Text tile, markdown tile | `inline-text` content item in `containers` | Created only when the plan carries the markdown; Looker Liquid tokens are not Mustache. Otherwise listed for hand recreation (`text_tile`). |
| Dashboard layout (`row`, `col`, `width`, `height`) | `containers` tree | Grid positions carried across; exact heights are hand-finished. |
| Folder | Folder | Recreated by path; ownership from the plan's permission map. |
| Schedule, alert | Recreated at cutover | Listed in `omni_content` plan; created by `cutover` after the parity gate. |
| Looker `user attribute` filters | Omni user attributes | Created by `omni-target-setup`. |

## Tile types

Confirm each `chartType` against `omni-content-builder/references/visConfig.md` in the installed Omni skills; the Omni names below are the ones that reference documents.

| Looker tile `type` | Omni | Class |
|---|---|---|
| `looker_column` | bar, vertical | mechanical |
| `looker_bar` | bar, horizontal | mechanical |
| `looker_line` | line | mechanical |
| `looker_area` | area | mechanical |
| `looker_scatter` | scatter | mechanical |
| `looker_pie` | pie | mechanical |
| `looker_donut_multiples` | pie (donut) | assisted |
| `single_value` | KPI | mechanical (comparison and conditional colour hand-finished) |
| `table`, `looker_grid` | table | mechanical |
| Pivoted table | table with pivot | mechanical |
| Pivoted bar with `pivot_where()` calcs | grouped bar | assisted |
| `looker_map`, `looker_geo_choropleth`, `looker_geo_coordinates` | map | assisted |
| `looker_funnel`, `looker_waterfall`, `looker_boxplot`, `looker_timeline` | closest Omni type | assisted |
| `text` | `inline-text` | manual unless markdown is plain |
| Custom visualisations (marketplace) | none | redesign |

## Rules from Omni's own dashboard migration guide

Omni's `looker-to-omni-dashboard` guide (docs.omni.co/guides/migrations/looker-to-omni-skill, read 2026-09-04) records rules its authors learned the hard way. `omni-content-generate` applies them and `omni-content-validate` checks the first two.

| Rule | Why |
|---|---|
| Every dashboard control id appears in every tile's filter map, with `false` where the tile is excluded | A missing entry is not "not filtered"; the control is silently ignored for that tile |
| Never use `[fiscal_quarter]` or `[quarter]` as a date control's field key; use `[date]` or `[month]` | A quarter-grained key returns 0 rows |
| Fields a Looker query used only for computation (hidden fields) are left out of the Omni tile's `fields` | Omni shows every listed field |
| Table tiles pivot with `query.pivots`; chart tiles pivot through the visualisation's colour (series) field, with no `pivots` entry | Omni's chart pivots are a presentation setting |
| Looker `parameter` fields become Omni templated filters written in Mustache block syntax, `{{# field }} ... {{/ field }}`, using the view's canonical name, not a join alias | An unset block collapses to `TRUE`, so OR-connected blocks match every row |
| Never delete and recreate a document by name | The guide's builder script's `delete_existing_by_name()` removes every accessible document with that exact name in any folder; the manifest's `target_identifier` is the only handle Wire uses |

Dynamic fields, per the same guide:

| Looker `dynamic_fields` entry | Omni |
|---|---|
| `calculation_type: group_by` | A `CASE WHEN` dimension in the view (or `groups`) |
| `category: measure` with same-view filters | A view measure with a `filters:` block |
| `category: measure` with cross-view filters | A query view (or a dbt model); ruled in the plan |
| `category: table_calculation`, simple arithmetic | A view measure |
| `category: table_calculation` using `pivot_where()`, other calculations, or runtime values | Skipped (`unsupported_calc`), listed for hand recreation |
| Any dynamic field referencing `${measure}` | Skipped (`unsupported_calc`) |

## Queries

| Looker query element | Omni |
|---|---|
| `fields` | `query.fields` as `view.field`, mapped through the emitted model |
| `filters` | `query.filters` in Omni filter syntax; Looker date expressions rewritten by hand (`assisted`) |
| `sorts`, `limit` | same |
| `pivots` | `query.pivots` |
| `dynamic_fields` table calculations: arithmetic, `CASE WHEN` | Omni table calculation | assisted |
| Table calculations referencing `pivot_where()`, `offset()`, other calcs, runtime values | skipped (`unsupported_calc`) | manual |
| Custom fields (`dimension`, `measure` in `dynamic_fields`) | Add to the model or the workbook layer; listed | assisted |
| Merged results | Two tiles, or a query view | redesign |

## Styling and fidelity

Not carried programmatically: colour themes, series colours beyond the model's `colors`, font sizes, KPI comparison styling, conditional formatting on tables. The content batch lists each as `hand_finish`. Plan for a fidelity pass on the prioritised dashboards; the Hunkemöller review found dashboard fidelity iteration to be the largest manual cost on a BI engagement.

## Skipped-tile reasons

`plan.json` records one of: `text_tile`, `unmapped_field`, `unsupported_calc`, `liquid`, `custom_vis`, `merged_results`. Every skipped tile appears in the batch's review and in `bi_equivalency` as `not_compared`.
