# Looker Studio to Looker: feature detection

Experimental. What the converter reads in `report.json` (written by `looker_studio_extract.py`).

| Construct | Where it is | Class |
|---|---|---|
| Data source kind | `datasources[].connection.connector`: `bigquery_table`, `bigquery_custom_sql`, `looker`, other | |
| Custom SQL | `connection.sql` (from `connectorConfig.sql` in the capture) | assisted |
| Looker connector | `connection.instance`, `model`, `explore` (from `lookerConnectorConfig`) | mechanical |
| Field | `fields[]`: `name`, `label` (the column), `data_type_code`, `default_aggregation_name`, `calculated`, `formula` | |
| Chart | `pages[].components[]` with `kind: data`: `type`, `grid`, `dataset`, `dimensions`, `metrics`, `chart_fields`, `sort`, `row_limit` | |
| Blend | `dataset.type_code` 2, or a `blends[].id` | redesign |
| Date range dimension | `date_range_dimension` (a chart field) | |
| Chart's own date range | `date_duration` (start and end offsets with unit codes) | assisted |
| Comparison | `comparison` (`compareDateDuration`), or a second metric on a scorecard | assisted |
| Control | `kind: control`: `simple-daterangepicker`, `dimension-filter` | assisted, mechanical |
| Text | `kind: text`, `text` | mechanical |
| Hidden page | `pages[].hidden` | drop |
