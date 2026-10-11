# Omni to Looker: content mapping

Experimental. How an Omni dashboard document becomes a LookML dashboard (`.dashboard.lookml`, `layout: newspaper`).

## Chart types

| Omni `chartType` | Looker `type` | Class |
|---|---|---|
| `kpi` | `single_value` | mechanical |
| `table` | `looker_grid` | mechanical |
| `pie` | `looker_pie` | mechanical |
| `line`, `lineColor` | `looker_line` | mechanical |
| `area` / `areaStacked` | `looker_area` (`stacking: normal` when stacked) | mechanical |
| `column`, `columnGrouped` / `columnStacked` | `looker_column` (`stacking: normal` when stacked) | mechanical |
| `bar`, `barGrouped` / `barStacked` | `looker_bar` (`stacking: normal` when stacked) | mechanical |
| `point`, `scatter` | `looker_scatter` | mechanical |
| `barLine`, `columnLine` | `looker_column` | assisted (series types hand-finished) |
| `map`, `heatmap`, `funnel`, `sankey`, `boxplot`, `waterfall` | `looker_map`, `looker_grid`, `looker_funnel`, `looker_grid`, `looker_boxplot`, `looker_waterfall` | assisted |
| none (automatic or markdown KPI) | `single_value` for one field, else `looker_grid` | assisted |
| `omni-ai-summary-markdown` | not emitted | redesign |
| anything else | `looker_grid` | assisted |

## Layout

Omni dashboards use a 24-column grid, as Looker's newspaper layout does: `x` and `w` map one to one to `col` and `width`. Omni's row units are finer: `y` and `h` are divided by 6 and rounded (a tile 36 units high is 6 Looker rows). One document becomes one dashboard; a document with pages becomes one dashboard, listed.

## Tiles

| Omni | LookML element |
|---|---|
| Tile on a topic | `explore:` the topic's explore; `fields`, `pivots`, `sorts`, `limit`, `filters` translated; the container's name is the title |
| Tile on a view with no topic | an explore `<view>_tiles` made for it (hidden), joining what the tile needs through the relationships; listed |
| Table calculation | `dynamic_fields` table calculation, its name added to `fields` |
| Period over period | the comparison dropped, listed |
| Column or row totals | listed (`show_totals`, `show_row_totals`) |
| SQL tile | not emitted, listed |
| Field defined only in a workbook | not emitted, listed |
| Filter the converter cannot translate | the tile is withheld, listed |
| Workbook tab not on the dashboard | not emitted, listed as dropped |
| Text tile | `type: text`, `body_text` (Markdown); Mustache tokens listed |

## Controls

Each control becomes a `field_filter` on its field, with the explore of the first tile that listens. The control's `map` says which tiles listen and on which field: each listening tile gets `listen: {<control>: <field>}`. A date control filters on the `_date` timeframe. Defaults are translated (`property_mapping.md`); `required` is kept. A control no tile listens to and with no topic is listed. A field-selection control is listed: LookML needs a parameter and Liquid.

## Parity

`parity_map.json` has one entry per emitted query tile: the Omni tile identity (`omni:<instance>:document:<id>/query:<key>`), the document, the dashboard file and element, the explore, and the Omni-to-Looker field map. The source side runs the tile's saved query with `omni_export.py tile-data` (unpivoted, raw values); the target side runs the element's query with its own filters, without the dashboard filters' defaults.
