# Looker Studio to Omni: content mapping

How `/wire:omni-content-generate` turns Looker Studio reports into Omni documents. The Omni model must exist on the branch first; every tile metric resolves to the Omni measure named by the metric catalogue's `target_name`.

## Objects

| Looker Studio | Omni | Notes |
|---|---|---|
| Report family (copies of one template, one per client or team) | One document with a control or user attribute | The field that split the copies becomes the control. Merging is a plan ruling |
| Report (no family) | Document | |
| Page | Tab or section of the document | Navigation order kept. Hidden pages only under the plan's ruling |
| Report-level component | Once per document | Not once per page |
| Data component | Tile (`queryPresentation`) | Chart type below |
| Date range control | Date control | Default range from the report |
| Dimension filter control | Filter control | |
| Report, page and component filter | Control default or tile filter | From `report.json` `filters[]` |
| Comparison period on a scorecard | KPI comparison | |
| Text box | `inline-text` item | Text from `report.json` (HTML removed) |
| Shape, line, image | Not migrated | Listed in the hand-finish list |
| Blend | Tile on a topic with the modelled join | The join is built in the model batch |

## Chart types

Confirm each Omni `chartType` against `omni-content-builder/references/visConfig.md` in the installed Omni skills.

| Looker Studio `type` | Omni | Class |
|---|---|---|
| `kpi-metric` | KPI | mechanical |
| `simple-table` | table | mechanical |
| `pivot-table` | table with pivot | mechanical |
| `simple-barchart`, `simple-columnchart` | bar | mechanical |
| `simple-linechart` | line | mechanical |
| `simple-areachart` | area | mechanical |
| `simple-piechart` | pie | mechanical |
| `simple-scatterchart` | scatter | mechanical |
| `simple-combochart` | combo (bar and line) | assisted |
| `bulletchart` | KPI with target | assisted |
| `simple-geochart`, `geo-map` | map | assisted |
| Any other data-bound type, including community visualisations | none | redesign |

## Layout

Looker Studio places components at absolute pixel positions on a fixed canvas (often 1200 pixels wide). Omni lays tiles on a grid. Wire uses the same 24-column grid as the Looker to Omni pair, and converts each component deterministically (`looker_studio_extract.grid`, tested by `validate_looker_studio_extract.py`):

- One grid unit is `canvas_width / 24` pixels, horizontally and vertically, so page proportions are kept.
- `x = round(left / unit)`, `w = max(1, round(width / unit))`, `y = round(top / unit)`, `h = max(1, round(height / unit))`.
- `x` is clamped to 0 to 23 and `w` to the columns left, so no tile overhangs the grid.

The `containers` tree is authored in full from these cells. Overlapping components (a scorecard on a background shape) do not overlap in Omni, because shapes are dropped. Exact heights are hand-finished.

## Rules carried from the Looker to Omni pair

Every control id appears in every tile's filter map (with `false` where the tile is excluded); no quarter-grained date keys; never delete and recreate a document by name. See `wire/bi_pairs/looker_to_omni/content_mapping.md`.
