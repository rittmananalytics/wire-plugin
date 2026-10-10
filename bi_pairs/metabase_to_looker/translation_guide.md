# Metabase to Looker: translation guide

Experimental. One row per Metabase construct. Classes: `mechanical` (the converter emits it and nothing needs deciding), `assisted` (emitted, or listed, with a decision for a person), `redesign` (not emitted: the plan rules it), `drop` (not migrated, listed).

## Model

| Metabase | LookML | Class | Notes |
|---|---|---|---|
| Table (synced metadata) | `view` with `sql_table_name` | mechanical | One view per table, shared by every question on it. BigQuery names carry the connection's project |
| Field | `dimension`, or `dimension_group: type: time` for dates and timestamps | mechanical | Type from the field's effective type; label from its display name; `details-only` fields hidden |
| Primary key (`type/PK`) | `primary_key: yes` | mechanical | Symmetric aggregates need it on every joined view; a joined view without one is listed |
| Foreign key (`type/FK`, `fk_target_field_id`) | explore `join`, `relationship: many_to_one` | mechanical | Used when a question reads a field through the key (an implicit join) |
| A question's own join | explore `join` with `sql_on` | mechanical when the right side is a primary key | Otherwise `one_to_many` or `many_to_many`, assisted. `left-join`, `inner-join`, `full-join` map; `right-join` is redesign |
| Sensitive field | not emitted | assisted | Listed |
| Cast field (UNIX seconds or milliseconds, ISO 8601 text) | the cast in the dimension's `sql` | mechanical | Other casts: emitted uncast, assisted |
| JSON-unfolded field | `JSON_VALUE` (BigQuery) or `col:path` (Snowflake) | assisted | Check the path |
| Column named like a date group's generated field (`created_at_month` next to `created_at`) | renamed `<name>_column` | assisted | Looker would reject the duplicate field |
| Metric | `measure` on the table's view, with the metric's filters | mechanical | The metric's default breakout is not part of the measure |
| Saved model | `view` with `derived_table: sql:` (the SQL Metabase compiles for it) and an explore | assisted | Exact, but not reusable: the plan rules remodel or keep |
| Native SQL question | `view` on its SQL, with each result column as a dimension | assisted | Exact, but not reusable. `{{variable}}` becomes a `parameter` and `{% parameter %}`; a field filter becomes a `filter` and `{% condition %}`; `{{#123}}` becomes `${view.SQL_TABLE_NAME}` |
| Simple single-table native SQL | also lifted: dimensions and measures on the table's view | assisted | A proposal. `COUNT(DISTINCT x)`, `SUM`, `AVG`, `MIN`, `MAX`, `COUNT(*)` become typed measures; other aggregates `type: number`. The `WHERE` clause is listed, not lifted. A lifted name never reuses a taken one (`_from_sql`). Needs `sqlglot` |
| Optional clause on a variable (`[[AND x = {{v}}]]`) | removed | assisted | The view equals the question with that filter empty |
| Snippet | not converted | redesign | |
| Database Looker cannot connect to (SQLite, H2) | emitted, but cannot run | redesign | The Sample Database |

## Questions

| Metabase | LookML | Class | Notes |
|---|---|---|---|
| Breakout | element field | mechanical | A date breakout with a unit becomes that timeframe (`_month`) |
| Count, sum, average, min, max, distinct, median, percentile | `measure` of the matching type | mechanical | Named `count`, `total_<f>`, `average_<f>`, `min_<f>`, `max_<f>`, `count_distinct_<f>` |
| Count where, sum where, distinct where | `measure` with `filters:` | mechanical | |
| Arithmetic over aggregations | `measure: type: number` over the measures, `NULLIF` on division | mechanical | |
| Cumulative sum or count | `measure: type: running_total` | assisted | Runs down the result rows: check sorts and pivots |
| Share, standard deviation, variance, offset | not converted | redesign | |
| Custom column | `dimension` with translated `sql` on the view its fields belong to | assisted | Reading more than one table: redesign |
| Filter | element `filters:` in Looker filter syntax | mechanical | See `property_mapping.md` |
| Second-stage filter on an aggregation | element filter on the measure (HAVING) | assisted | |
| Second-stage filter on a grouping column | element filter on the dimension | assisted | |
| Other multi-stage questions | not converted | redesign | |
| Bin by width | `dimension: FLOOR(x / w) * w` | assisted | |
| Bin by number of bins (or default) | not converted | redesign | Metabase picks the width from the data range |
| Sort | element `sorts:` | mechanical | With no sort, Metabase orders by the breakouts ascending, and so does the element |
| Row limit | element `limit:` | mechanical | Default 500 |
| Question on no dashboard | one-tile LookML dashboard | assisted | Keep, make a Look, or drop |
| Archived card | not migrated | drop | |
