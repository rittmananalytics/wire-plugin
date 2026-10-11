# Metabase to Omni: translation guide

Experimental. The classes are those of the audit (`mechanical`, `assisted`, `redesign`, `drop`).

## Naming

- A dimension on a column takes the column's name; the Metabase caption becomes its `label`. Omni maps a column by name, so the dimension needs no `sql`.
- A measure, calculation or derived field whose name would collide with a column is suffixed (`_measure`, `_calc`), never allowed to take the column's name: in Omni, `${name}` inside a field named `name` refers to itself.
- A raw column that a derived field reads, and that no field shows, is declared as a hidden dimension.
- `--prefix` puts the same prefix on every view and topic, so a batch or a test cannot collide with names already on the model.

## Constructs

| Metabase | Omni | Class | Notes |
|---|---|---|---|
| Synced table | Query view `<prefix><table>.query.view` on `SELECT * FROM <table>` | mechanical | `--bind schema` writes `<schema>/<prefix><table>.view` instead |
| Field (typed, with semantic type) | Dimension named after the column, Metabase display name as `label`; `primary_key` from type/PK | mechanical | Omni auto-maps a column by name |
| Field Metabase casts (coercion) | Hidden raw column, and a cast dimension named `<column>_calc` | assisted | The cast cannot take the column's name: it would refer to itself |
| Foreign key | `relationships.yaml` entry `many_to_one` and topic `joins` | mechanical |  |
| Explicit join with an alias | Relationship with `join_to_view_as` | assisted |  |
| Aggregation (count, sum, avg, distinct, min, max, median, percentile) | Measure with `aggregate_type` | mechanical |  |
| Metric | Measure with Omni operator-object `filters` | mechanical |  |
| Ratio of aggregations, custom column | Measure or dimension with translated `sql` | assisted |  |
| Native SQL question, model | Query view on its SQL | assisted | Template tags become TRUE (field filters) or the default value (variables); listed |
| Simple single-table SQL | Lifted onto the table's view, as a proposal | assisted | Needs `sqlglot` |
| Binning by number of bins, multi-stage question, snippet | Not converted | redesign | Plan ruling |
