# Tableau to Omni: content mapping

Experimental. `bi_to_omni.py` writes one document body per dashboard; `omni-content-generate` reviews it and writes it to Omni.

| Source | Omni | Notes |
|---|---|---|
| Dashboard (and each Metabase tab) | One document body, `documents/<slug>.json` | Created by name on the shared model, then the draft is patched with the body and the branch id |
| Question or sheet on no dashboard | A one-tile document | Plan ruling: keep, or drop |
| Tile | `queryPresentations.data.<n>` with `query`, `topicName` and `visConfig` | `query.table` is the topic's base view; `join_paths_from_topic_name` the topic |
| Bar, column, line, area, pie, scatter, single value, table | `chartType` `bar`, `column`, `line`, `area`, `pie`, `point`, `kpi`, `table` | Anything else is a table, with a fidelity note |
| Pivot | `query.pivots` on tables; a chart takes the second dimension as its colour | |
| Sort, limit | `sorts` (`column_name`, `sort_descending`), `limit` | |
| Tile filter | Omni filter object | See `property_mapping.md`; an unmapped expression skips the tile (`unmapped_filter`) |
| Dashboard filter | `controls.data.<id>` with `config` (`fieldName`, `kind`, `type`, default) and a `map` naming every tile | A tile that does not listen is `false` |
| Text or heading card | Not created | `text_tile`, recreated by hand |
| Layout | `containers`: one page, one grid, one stack per tile with `gridPosition` | Columns carried; rows times 6; heights hand-finished |
