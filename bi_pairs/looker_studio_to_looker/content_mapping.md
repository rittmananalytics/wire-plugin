# Looker Studio to Looker: content mapping

Experimental. How a Looker Studio page becomes a LookML dashboard (`layout: newspaper`).

## Chart types

| Looker Studio | Looker `type` | Class |
|---|---|---|
| `kpi-metric`, `scorecard` | `single_value` | assisted (comparison hand-finished) |
| `simple-linechart`, `timeseries` | `looker_line` | mechanical |
| `simple-barchart` | `looker_column` | mechanical |
| `simple-combochart` | `looker_column` | assisted |
| `simple-piechart`, `simple-donutchart` | `looker_pie` | mechanical |
| `simple-table`, `table` | `looker_grid` | mechanical |
| `simple-areachart`, `simple-scatterchart` | `looker_area`, `looker_scatter` | mechanical |
| anything else | `looker_grid` | assisted |

## Layout and folders

The extractor already places each component on a 24-column grid (`grid.x`, `y`, `w`, `h`), so positions map one to one. Each visible page is one dashboard. A dashboard whose charts all read one existing Looker model (Looker connector) goes in `dashboards/<model>/`, outside the new model's include, because a LookML dashboard belongs to the model that includes it: its filters would otherwise use fields the new model cannot reach.

## Controls

The date range control becomes a dashboard filter named Date range; every chart with a date range dimension and no range of its own listens on its date field. A dimension filter control becomes a filter that every chart on the same data source listens to.
