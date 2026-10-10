# Tableau to Looker: content mapping

Experimental. How a Tableau dashboard becomes a LookML dashboard (`.dashboard.lookml`, `layout: newspaper`).

## Mark types

| Tableau mark | Looker `type` | Notes |
|---|---|---|
| Bar, dimension on rows | `looker_bar` | horizontal |
| Bar, dimension on columns | `looker_column` | vertical |
| Line | `looker_line` | |
| Area | `looker_area` | |
| Pie | `looker_pie` | |
| Circle, Shape | `looker_scatter` | |
| Text, Square | `looker_grid` | crosstab or highlight table; colour hand-finished |
| Map, Multipolygon | `looker_map` | hand-finished |
| Automatic with one measure and no dimension | `single_value` | |
| Automatic otherwise | `looker_grid` | |

## Layout

Tableau zones carry `x`, `y`, `w`, `h` in units of 100,000 of the dashboard size. Looker's newspaper layout has 24 columns. The converter maps each zone:

- `col = round(x / 100000 * 24)`, clamped to 0 to 23; `width = max(1, round(w / 100000 * 24))`, clamped to the columns left.
- Rows are scaled so cells keep the dashboard's proportions: `rows = 24 * height / width` of the Tableau size; `row = round(y / 100000 * rows)`, `height = max(1, round(h / 100000 * rows))`.

Layout containers are walked; only leaf zones become elements.

## Filters and actions

| Tableau | Looker |
|---|---|
| Quick filter zone on a field | dashboard `filters:` entry (`type: field_filter`) with `listen` on every sheet that has a filter on that field |
| Filter action | needs_human: `listen`, or `crossfilter_enabled: true` where the plan rules it |
| Highlight, URL, parameter actions | needs_human |
| Parameter control | the LookML `parameter` (in the model) exposed as a dashboard filter by hand |

## What is not migrated

Images, web page and blank zones, device layouts, stories, custom shapes, annotations and formatting. Each is listed in `needs_human.json` with class `drop` and appears in the content batch's hand-finish list.

## Rules shared with the other pairs

Never delete and recreate a dashboard by name; the manifest's identity is the only handle. A tile that references a field the model does not have is skipped with its reason and fixed in the model batch.
