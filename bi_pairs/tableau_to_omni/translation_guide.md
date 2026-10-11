# Tableau to Omni: translation guide

Experimental. The classes are those of the audit (`mechanical`, `assisted`, `redesign`, `drop`).

## Naming

- A dimension on a column takes the column's name; the Tableau caption becomes its `label`. Omni maps a column by name, so the dimension needs no `sql`.
- A measure, calculation or derived field whose name would collide with a column is suffixed (`_measure`, `_calc`), never allowed to take the column's name: in Omni, `${name}` inside a field named `name` refers to itself.
- A raw column that a derived field reads, and that no field shows, is declared as a hidden dimension.
- `--prefix` puts the same prefix on every view and topic, so a batch or a test cannot collide with names already on the model.

## Constructs

| Tableau | Omni | Class | Notes |
|---|---|---|---|
| Data source table (relation) | Query view `<prefix><table>.query.view` on `SELECT * FROM <table>` | mechanical | `--bind schema` writes `<schema>/<prefix><table>.view` instead |
| Custom SQL relation | Query view on the SQL | assisted | Check the dialect; listed |
| Column | Dimension named after the column, Tableau caption as `label` | mechanical | Omni auto-maps a column by name, so no `sql` |
| Date or datetime column | Dimension named after the column; Omni adds the timeframes | mechanical | Tiles use `field[month]` |
| Field inside a record column (`parent.child`) | Not emitted | assisted | A repeated record needs UNNEST; listed |
| Row-level calculation | Dimension with translated `sql` (`${view.field}` references) | assisted | Same translator as Tableau to Looker; renamed with `_calc` if it would take a column's name |
| Aggregate calculation | Measure with `sql` over other measures, no `aggregate_type` | assisted |  |
| Default aggregation of a measure column | Measure with `aggregate_type` (sum, average, count, count_distinct, min, max) | mechanical | Named `total_x`, `avg_x`; suffixed `_measure` if it would take a column's name |
| Group, bin | `CASE` or `FLOOR` dimension | assisted |  |
| Parameter, and any field that uses one | Not emitted | assisted | An Omni templated filter or a dashboard control, by hand |
| LOD expression, table calculation, set | Not emitted | redesign / assisted | Plan ruling: query view, Omni table calculation, or drop |
| Join or relationship | `relationships.yaml` entry and topic `joins` | assisted | Cardinality from the relationship, or `many_to_one` proposed; primary keys from `*_pk` columns, to confirm |
| Duplicate embedded data sources | One topic per fingerprint group | assisted | Plan ruling |
| Extract, file source | Views read the live tables; file sources listed | redesign | Plan ruling |
