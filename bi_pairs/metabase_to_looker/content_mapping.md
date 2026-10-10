# Metabase to Looker: content mapping

Experimental. How a Metabase dashboard becomes a LookML dashboard (`.dashboard.lookml`, `layout: newspaper`).

## Chart types

| Metabase `display` | Looker `type` | Class |
|---|---|---|
| `table` | `looker_grid` | mechanical |
| `pivot` | `looker_grid` | assisted |
| `bar` | `looker_column` | mechanical |
| `row` | `looker_bar` | mechanical |
| `line`, `area`, `pie`, `scatter`, `funnel` | `looker_line`, `looker_area`, `looker_pie`, `looker_scatter`, `looker_funnel` | mechanical |
| `combo` | `looker_column` | assisted |
| `scalar` | `single_value` | mechanical |
| `smartscalar`, `gauge`, `progress` | `single_value` | assisted (comparison, goal and ranges are hand-finished) |
| `map` | `looker_map` | assisted |
| `waterfall`, `boxplot` | `looker_waterfall`, `looker_boxplot` | assisted |
| `object` | `looker_single_record` | mechanical |
| `sankey` and anything else | `looker_grid` | assisted (chart listed) |

A line, bar, area, row or combo chart with two breakouts pivots on the second, as Metabase splits series by it.

## Layout

Metabase dashboards use a 24-column grid (since version 47), as Looker's newspaper layout does: `row`, `col`, `size_x`, `size_y` map one to one to `row`, `col`, `width`, `height`. A dashboard with tabs becomes one LookML dashboard per tab, titled `<dashboard> - <tab>`. A question on no dashboard becomes a one-tile dashboard.

## Cards

| Metabase dashcard | LookML |
|---|---|
| Question | element with the question's fields, filters, sorts, pivots and limit; the dashcard's title override wins |
| Heading | text element with `title_text` |
| Text | text element with `body_text` (Markdown); a `{{tag}}` showing a filter value becomes plain words and is listed |
| Link, iframe, action, placeholder | dropped and listed |
| Combined series | only the first card migrates; listed |
| Click behaviour | dropped and listed |

## Filters

Each dashboard filter becomes a `field_filter` on the field its first mapped tile reads, and every mapped tile `listen`s on its own field. Through a foreign key the field is the joined view's (`customers.region`). A filter mapped to a native question's field filter or variable listens on the view's `filter` or `parameter`. A filter that changes date grouping (`temporal-unit`) is listed: LookML dashboard filters cannot. When a tile filters a field itself and listens to a dashboard filter on the same field, it is listed: Metabase applies both, Looker's dashboard filter replaces the tile's. Defaults are translated (`property_mapping.md`); `required` is kept.
