# Looker to Omni: translation guide

One row per LookML construct. `Class` is what the converter does: `mechanical` (emitted, no note), `assisted` (emitted with a `needs_human` note, or withheld with a note where a wrong emission would change a number), `redesign` (not emitted; the Omni alternative is recorded). Sources: Omni's `omni-model-builder` parameter reference, the Omni docs parameter pages for views, topics, dimensions, measures and relationships, and Omni's Looker dashboard migration guide.

## Omni facts that shape every row

- **There is no `${TABLE}` in Omni.** A plain column dimension auto-maps by name and needs no `sql:`. A derived expression references other fields with `${field}` or `${view.field}`.
- **A LookML timeframe reference becomes an Omni timeframe selector:** `${created_month}` becomes `${created[month]}`.
- **Measure filters are operator objects**, never bare scalars: `status: {is: complete}`.
- **Every view that appears in a relationship needs `primary_key: true`** on one dimension (or `custom_compound_primary_key_sql`), or aggregations fan out.
- **Model changes happen on a branch** (`omni models create-branch`, `yaml-create`, `validate`) and merge only on the release director's ruling.

## View naming: a plan ruling

An Omni view is named by its file, regardless of the directory it sits in (`ecomm__users.view` is the view `ecomm__users`); `schema` is required and `table_name` defaults to the file name. Omni's schema model auto-generates one view per table named `schema__table`, and Omni's own migration guide builds on those names.

The converter keeps the **LookML view name** and binds it with `schema:` and `table_name:` (`orders.view` with `schema: analytics`, `table_name: fct_orders`). Field references, topics, dashboards and the parity field map then stay one-to-one with Looker, which is what makes the tile comparison mechanical. The cost is a second view over the same table alongside Omni's auto-generated `analytics__fct_orders`. The plan may rule the other way for an engagement (extend the schema view and rewrite references to `schema__table`); that is a conversion setting, not a per-view choice, because every reference in every batch has to agree.

## Views

| LookML | Omni | Class | Notes |
|---|---|---|---|
| `view: v { sql_table_name: schema.table ;; }` | `<SCHEMA>/v.view` with `schema:` and `table_name:` | mechanical | BigQuery `project.dataset.table` and backticks: project dropped (the Omni connection carries it), dataset becomes `schema`. |
| `sql_table_name` containing Liquid | `needs_human` | redesign | Table chosen at query time has no Omni form. |
| `derived_table: { sql: ... }` with no persistence key | `sql:` view | mechanical | Liquid in the SQL makes it redesign. |
| `derived_table` with `datagroup_trigger`, `sql_trigger_value`, `persist_for`, `materialized_view`, `increment_key` | `needs_human` | redesign | PDT. The plan rules dbt model or Omni query view. Nothing emitted. |
| `derived_table: { explore_source: ... }` | `needs_human` | redesign | Native derived table: rebuild as an Omni query view. |
| `extends: [base]` | `extends: [base]` | mechanical | |
| `extension: required` | `template: true` | mechanical | |
| `view: +name` refinement | Merged into the base view before conversion | mechanical | Refined fields override by name. |
| `label`, `description` | `label`, `description` | mechanical | |
| `required_access_grants: [g]` | `required_access_grants: [g]` | mechanical | Grants themselves are created by `omni-target-setup`. |
| `set: s { fields: [...] }` | Expanded wherever `s*` is referenced | mechanical | |

## Dimensions

| LookML | Omni | Class | Notes |
|---|---|---|---|
| `dimension: col { sql: ${TABLE}.col ;; }` | `col: {}` | mechanical | Auto-mapped by name. |
| `dimension: x { sql: ${TABLE}.other ;; }` | `x: { sql: ${other} }` | mechanical | |
| `${field}` in SQL | Unchanged | mechanical | |
| `${other_view.field}` in a view field's SQL | Unchanged | assisted | Confirm every topic that exposes the field joins the referenced view. |
| A `dimension_group` named like an existing dimension | Group withheld | assisted | In Omni the group becomes one dimension, so the names collide; rename one by hand. |
| `type: string`, `number`, `date`, `date_time`, `yesno`, `zipcode`, `unquoted` | Dropped | mechanical | Omni infers the type from SQL. A `yesno` dimension is a boolean expression. |
| `type: location`, `distance`, `bin` | `needs_human` | redesign | No Omni equivalent. |
| `type: tier { tiers: [0, 10, 50] }` | `bin_boundaries: [0, 10, 50]` on the tiered `sql` | mechanical | |
| `case: { when: { sql: ${f} = 'a' } ... else: "z" }` where every `when` is `=` or `IN` on one field | `sql: ${f}`, `groups: [{filter: {is: [...]}, name: ...}]`, `else:` | assisted | Confirm labels and the else bucket. |
| `case` with any other condition | `needs_human` | assisted | Write the Omni `sql` by hand. Nothing emitted. |
| `hidden: yes` | `hidden: true` | mechanical | `no` omitted. |
| `primary_key: yes` | `primary_key: true` | mechanical | |
| `label`, `description`, `group_label`, `view_label` | Same keys | mechanical | |
| `value_format_name` | `format` per `property_mapping.md` | mechanical | Unmapped names: emitted without `format`, `needs_human`. |
| `value_format: "..."` | `format` per `property_mapping.md` | mechanical / assisted | Unmapped strings: emitted without `format`, `needs_human`. |
| `drill_fields: [a, b, set*, created_month]` | `drill_fields: [view.a, view.b, ..., view.created[month]]` | mechanical | Sets expanded, bare names qualified, timeframe fields rewritten to bracket form. |
| `suggestions: [...]` | `suggestion_list: [...]` | mechanical | |
| `suggest_dimension: f` | `suggest_from_field: f` | mechanical | |
| `order_by_field: f` | `order_by_field: f` | mechanical | |
| `link: { label, url }` | `links: [{label, url}]` | assisted | Looker URLs carry Liquid tokens; confirm the Omni links syntax and Mustache tokens. |
| `html: ... ;;` | Withheld | redesign | Looker `html` is Liquid; Omni `markdown` is Mustache. The dimension itself is still emitted. |
| Liquid in `sql` or `label` | `needs_human` | redesign | Templated filter or dashboard control. Nothing emitted. |
| `parameter:` | `needs_human` | redesign | Templated filter or a `FIELD_SELECTION` control. |
| `filter:` (filter-only field) | `needs_human` | redesign | Dashboard filter control. |

## Dimension groups

| LookML | Omni | Class | Notes |
|---|---|---|---|
| `dimension_group: g { type: time; timeframes: [...]; sql }` | `g: { sql, timeframes: [...] }` | mechanical | Timeframes per `property_mapping.md`; `time` dropped (`raw` covers it); an unmapped timeframe is dropped with a `needs_human` note. |
| `convert_tz: no` | `convert_tz: false` | mechanical | |
| `dimension_group: d { type: duration; sql_start; sql_end; intervals }` | `d: { duration: { start, end, intervals } }` | assisted | Confirm the parameter shape against the Omni docs before validate. |
| `${g_month}` referenced elsewhere | `${g[month]}` | mechanical | |

## Measures

| LookML | Omni | Class | Notes |
|---|---|---|---|
| `type: sum`, `count`, `count_distinct`, `average`, `min`, `max`, `median`, `list` | `aggregate_type:` same name | mechanical | `average` stays `average`. |
| `type: percentile; percentile: N` | `aggregate_type: percentile`, `percentile: N` | mechanical | |
| `type: sum_distinct; sql_distinct_key` (and average, median, percentile) | `aggregate_type: sum_distinct_on`, `custom_primary_key_sql` | mechanical | |
| `type: number` | `sql:` with no `aggregate_type` | assisted | Validate confirms it resolves on the branch. |
| `type: running_total`, `percent_of_total`, `percent_of_previous` | `needs_human` | redesign | Table calculation on the tile. |
| `type: date`, `string`, `yesno` measures | `needs_human` | redesign | |
| `filters: [f: "expr"]` (list or legacy `filters: { field value }`) | `filters: { f: {operator: value} }` per `property_mapping.md`; a timeframe key `created_date` becomes `created[date]` | mechanical | If any expression is not mechanical, the whole measure is withheld with a note. An unfiltered measure would change the number silently. |
| `value_format*`, `label`, `description`, `hidden`, `group_label`, `view_label`, `drill_fields`, `link`, `html` | As for dimensions | | |

## Explores

| LookML | Omni | Class | Notes |
|---|---|---|---|
| `explore: e { from: v }` or `view_name: v` | `e.topic` with `base_view: v` | mechanical | |
| `label`, `description`, `group_label`, `hidden: yes` | Same keys, `hidden: true` | mechanical | |
| `extends: [base]` | `extends: [base]` | mechanical | |
| `fields: [ALL_FIELDS*, -v.f]` | `fields: [base.*, join1.*, ..., -v.f]` | mechanical | Omni lists views explicitly. A `view.set*` reference is kept and flagged for hand expansion. |
| `join: j { sql_on; relationship: many_to_one; type: left_outer }` | `relationships.yaml` entry: `join_from_view`, `join_to_view`, `on_sql`, `relationship_type: many_to_one`, `join_type: always_left`; topic `joins:` tree by join path | mechanical | `join_from_view` is the other view referenced in `sql_on`, else the base view. |
| `relationship: one_to_one` | `relationship_type: one_to_one` | mechanical | |
| `relationship: one_to_many`, `many_to_many` | `relationship_type: one_to_many`, `many_to_many` | mechanical | Omni supports fan-out joins natively; symmetric aggregates need `primary_key` on the joined views, which `omni-model-lint` checks. |
| `type: inner`, `full_outer`, `cross` | `join_type: inner`, `full_outer`, `cross` | mechanical | Omni also has `right_left` and `left_right`; LookML has no equivalent. |
| Join without `sql_on`, Liquid in `sql_on` | `needs_human` | redesign | |
| `join: alias { from: v }` | Topic-scoped `relationships:` entry with `join_to_view: v`, `join_to_view_as: alias`; the topic's `joins:` and `on_sql` use the alias | mechanical | Omni's `join_to_view_as` is for joining the same view twice. |
| `sql_where` on a join | `needs_human` | assisted | Fold into `on_sql` or a topic filter. |
| `sql_always_where` | `always_where_sql` | assisted | Confirm references resolve on the topic. Liquid makes it redesign. |
| `always_filter`, `conditionally_filter` | `default_filters` (user-removable) | assisted | If any expression is not mechanical (date expressions never are), nothing is emitted. Use `always_where_filters` if it must not be removable. |
| `access_filter: { field, user_attribute }` | `access_filters: [{field, user_attribute}]` | assisted | The user attribute must exist in Omni (`omni-target-setup`). |
| `datagroup`, `persist_with` | Dropped | mechanical | Note for the topic `cache_policy`. |

## Content

Dashboards, Looks and tiles are not the converter's job. See `content_mapping.md`.
