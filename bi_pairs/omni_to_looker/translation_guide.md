# Omni to Looker: translation guide

Experimental. One row per Omni construct. Classes: `mechanical` (the converter emits it and nothing needs deciding), `assisted` (emitted, or listed, with a decision for a person), `redesign` (not emitted: the plan rules it), `drop` (not migrated, listed).

## Omni facts that shape every row

- **A bare identifier in a field's `sql` is a column** of the view's table; fields are always `${field}` or `${view.field}`. The converter qualifies bare columns with `${TABLE}.` and leaves function names, keywords, date parts and type names alone. In an expression that holds a subquery nothing is qualified, and the field is listed.
- **A field with no `sql` is the column of the same name.** LookML needs `sql: ${TABLE}.<column> ;;`.
- **Time is one field with timeframes.** `${created_at[month]}` is LookML's `${created_at_month}`; a bare `${created_at}` in SQL is `${created_at_raw}`.
- **A view is named by its file path.** `analytics/orders.view` is the view `analytics__orders`; the LookML view keeps that name, so field references in topics and documents stay one to one.
- **Types are not in the YAML.** Omni infers a field's type from the warehouse. The snapshot reads column types from the warehouse's `INFORMATION_SCHEMA` through Omni (`columns.json`); where it has none (a view on other SQL), a dimension is typed from its format, from the filters that use it, or left as LookML's default (`string`).

## Views

| Omni | LookML | Class | Notes |
|---|---|---|---|
| Schema view (`schema`, `table_name`, optional `catalog`) | `sql_table_name` | mechanical | BigQuery: backticked, with the connection's project when there is no `catalog` |
| Query view `sql: SELECT * FROM <table>` | `sql_table_name` | mechanical | |
| Query view with other `sql:` | `derived_table: { sql: ... ;; }` | mechanical | |
| Query view built from a topic query (`query:`) | not emitted | redesign | A native derived table (`explore_source`) or a view on the generated SQL |
| Mustache in the view's SQL (`{{ filters.view.field... }}`) | not emitted; neither is a topic on it | redesign | Liquid `{% condition %}` or a parameter |
| `extends: [v]` | the chain merged into the extending view | mechanical | Fields of the extending view win |
| `template: true` | `extension: required` | mechanical | |
| `label`, `description` | same | mechanical | |
| `filters:` (filter-only field) | `filter:` field, typed | assisted | Omni applies it through Mustache in SQL; the SQL needs Liquid |
| `custom_compound_primary_key_sql` | listed | assisted | A hidden concatenated dimension with `primary_key: yes` |
| `dbt`, `schema_label` | dropped | mechanical | Read-only metadata |

## Dimensions

| Omni | LookML | Class | Notes |
|---|---|---|---|
| `col: {}` | `dimension: col { sql: ${TABLE}.col ;; }` | mechanical | A name LookML cannot use is lower-cased and slugged; the column keeps its case |
| `sql:` | `sql:` translated | mechanical | See the facts above |
| `${other_view.field}` in SQL | unchanged | assisted | Every explore that exposes it must join the view |
| `${x}` in a dimension's SQL where `x` is only a measure | `${TABLE}.x` | assisted | Omni reads it as the column `x`; LookML would read the measure, and Looker rejects a measure in a dimension. Lint fails on any dimension that references a measure. Found by Looker's validator on the real-model test |
| `timeframes: [...]`, or Omni's field list shows `[date]` variants, or a DATE/TIMESTAMP column | `dimension_group: type: time` | mechanical | Timeframes per `property_mapping.md`; `raw` always added; a DATE column gets `datatype: date` |
| A timeframe with no LookML equivalent (`day_of_quarter`) | dropped | assisted | Listed |
| `convert_tz: false` | `convert_tz: no` | mechanical | |
| `primary_key: true`, `hidden: true` | `primary_key: yes`, `hidden: yes` | mechanical | |
| `label`, `description`, `group_label`, `view_label` | same | mechanical | |
| `format` | `value_format_name` or `value_format` | mechanical | Unmapped formats are listed; a numeric format makes the dimension `type: number` |
| `groups:` on one field (equality, `is`) with `else` | `case:` with `when` and `else` | mechanical | Any other condition is listed |
| `bin_boundaries: [...]` | `type: tier`, `tiers`, `style: integer` | assisted | Looker labels tiers differently from Omni's bins |
| `all_values`, `suggestion_list` | `suggestions` | mechanical | |
| `suggest_from_field` | `suggest_dimension` | mechanical | |
| `order_by_field` | `order_by_field` | mechanical | |
| `drill_fields` | `drill_fields`, timeframes rewritten | mechanical | |
| `links` | listed | assisted | Omni's Mustache tokens are not Liquid |
| `markdown` | listed; the dimension is still emitted | redesign | LookML `html:` with Liquid |
| `parent_field`, `nested_on_field` | not emitted | redesign | A record field is `${TABLE}.parent.child`; a repeated one needs a join on `UNNEST` |
| `duration:` | listed | assisted | `dimension_group: type: duration` |
| `ai_context`, `synonyms`, `sample_values` | dropped | drop | No LookML equivalent |

## Measures

| Omni | LookML | Class | Notes |
|---|---|---|---|
| `aggregate_type: sum`, `count_distinct`, `average`, `min`, `max`, `median`, `list` | `type:` same name | mechanical | |
| `aggregate_type: count` with no `sql` | `type: count` | mechanical | |
| `aggregate_type: count` with `sql` | `type: number`, `sql: COUNT(...)` | assisted | `count_distinct` if the values are keys |
| `percentile` + `percentile: N` | same | mechanical | |
| `sum_distinct_on` + `custom_primary_key_sql` (and average, median, percentile) | `sum_distinct` + `sql_distinct_key` | mechanical | |
| No `aggregate_type`, `sql:` over other measures | `type: number` | mechanical | |
| No `aggregate_type`, `sql:` aggregating columns (`SUM(total)`) | `type: number` with the columns qualified | mechanical; assisted where the view is joined | No protection from join fan-out |
| `filters: {field: {operator: value}}` | one `filters: [field: "expr", ...]` list | mechanical | Operators per `property_mapping.md`; a timeframe key `created_at[date]` becomes `created_at_date`. If any condition does not translate, the measure is withheld: an unfiltered measure would change the number |

## Topics and relationships

| Omni | LookML | Class | Notes |
|---|---|---|---|
| `<topic>.topic` with `base_view` | `explore: <topic>` with `view_name` | mechanical | The folder a topic file sits in is not part of its name |
| `label`, `description`, `group_label`, `hidden` | same | mechanical | |
| `joins:` tree | flat `join:` list, parents first | mechanical | Each join's `sql_on`, `relationship` and `type` come from the relationship that connects it |
| Relationship declared from the joined view to its parent | reversed: `many_to_one` becomes `one_to_many` | assisted | Confirm the join type from this explore's side |
| `join_to_view_as: alias` | `join: alias { from: view }` | mechanical | Matched on the alias or on the view behind it |
| `join_type: always_left`, `inner`, `full_outer`, `cross` | `left_outer`, `inner`, `full_outer`, `cross` | mechanical | `right_left`, `left_right`: `left_outer`, listed |
| `relationship_type` | `relationship` | mechanical | `many_to_many` is listed (primary keys on both sides) |
| No relationship connects a join | not emitted | redesign | |
| `always_where_sql` | `sql_always_where` | mechanical | |
| `default_filters` | listed, not emitted | assisted | Omni applies them to new queries; Looker's `always_filter` would also change saved tiles. The proposal carries the translated filter |
| `always_where_filters` | listed | assisted | `sql_always_where` |
| `access_filters` | `access_filter` | assisted | The user attributes must exist in Looker |
| `required_access_grants` | same | assisted | The grants must exist in the LookML model |
| `fields: [all_views.*, -v.f]` | `fields: [ALL_FIELDS*, -v.f]` | mechanical | Other lists are listed |
| `ai_context`, `ai_fields`, `sample_queries` | dropped | drop | |
| `cache_policy` | listed | assisted | A datagroup and `persist_with` |

## Model file

| Omni | LookML | Class |
|---|---|---|
| `week_start_day` | `week_start_day` | mechanical |
| `fiscal_month_offset` | `fiscal_month_offset` | mechanical |
| `access_grants` | listed | assisted |
| `dynamic_schemas` | listed | redesign |
| `cache_policies`, `default_cache_policy`, `query_timezone` | listed | assisted |
| `ai_context` | dropped | drop |

## Content

Dashboards, tiles and controls: see `content_mapping.md`.
