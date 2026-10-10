# Looker Studio to Looker: translation guide

Experimental. Classes as in the other pairs: `mechanical`, `assisted`, `redesign`, `drop`.

| Looker Studio | LookML | Class | Notes |
|---|---|---|---|
| BigQuery table data source | `view` with `sql_table_name`, one explore | mechanical | One view per table, shared by every data source on it |
| BigQuery custom SQL data source | `view` with `derived_table: sql:` | assisted | Exact, not reusable: remodel or keep |
| Looker connector data source | the existing explore; no view | mechanical | The dashboard goes in `dashboards/<model>/`; add its include to that model |
| Other connectors (Search Console, GA4, Sheets, Funnel.io) | not converted | redesign | A pipeline task in the plan, or drop |
| Source column | `dimension`, or `dimension_group` for dates | mechanical | Type from the data type code |
| Record Count | `measure: type: count` | mechanical | |
| Chart metric with an aggregation | measure of that type on the view | mechanical | `total_`, `average_`, `min_`, `max_`, `count_distinct_` |
| Calculated field, row level | `dimension` with translated SQL | assisted | Division is `SAFE_DIVIDE`, as Looker Studio sends it to BigQuery |
| Calculated field, aggregate | `measure: type: number` | assisted | A ruled metric catalogue entry names it |
| Chart-level formula | measure on the chart's view | assisted | |
| Unsupported function (`CONTAINS_TEXT`, regex functions not mapped) | not translated | redesign | |
| Blend | not converted | redesign | The plan rules the join keys and grain for an explore |
| Page | one LookML dashboard | mechanical | Pages with one name get numbered dashboards; hidden pages are dropped |
| Chart | element on the same 24-column grid | mechanical | Combo and scorecards with comparisons are assisted |
| Breakdown dimension (second dimension) | `pivots:` | assisted | Looker Studio draws only its top series |
| Sort | `sorts:` | mechanical | Direction code 1 is descending |
| Row limit | `limit:` | mechanical | |
| Date range control | dashboard filter with `listen` on each chart's date field | assisted | Its default range is not in the capture |
| Chart's own date range | element filter; the chart does not listen to the control | assisted | Start of the month N back to today becomes `N+1 months`, which also takes in the rest of the current month |
| Text date range field | `dimension_group` on `DATE(SAFE_CAST(col AS TIMESTAMP))` | assisted | As Looker Studio casts it |
| Dimension filter control | dashboard filter; every chart on its data source listens | mechanical | |
| Text box | text element | mechanical | |
| Image, shape, other controls | not migrated | drop | |
