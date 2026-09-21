# Looker to Omni: feature detection

Patterns `/wire:looker-audit-generate` applies to every `.lkml` file to tag constructs before classifying them. Each tag maps to a translation class in `translation_guide.md`. Patterns are Python regular expressions applied per line unless stated; `\|` is alternation inside a pattern.

| Tag | Pattern | Class | Description |
|---|---|---|---|
| `liquid` | `\{%\|%\}\|\{\{\|\}\}` | redesign | Any Liquid tag or output. In `html` only, the dimension is still emitted and only the html is withheld. |
| `table_ref` | `\$\{TABLE\}\.` | mechanical | `${TABLE}.col` becomes `${col}` or auto-maps. Informational. |
| `timeframe_ref` | `\$\{\w+_(raw\|date\|week\|month\|quarter\|year\|time\|day_of_week\|day_of_month\|hour_of_day\|month_name\|fiscal_quarter\|fiscal_year)\}` | mechanical | Becomes `${group[timeframe]}`. |
| `parameter` | `^\s*parameter:\s*\w+` | redesign | Parameter field. |
| `filter_field` | `^\s*filter:\s*\w+\s*\{` | redesign | Filter-only field (not a measure `filters:` list). |
| `pdt` | `^\s*(datagroup_trigger\|sql_trigger_value\|persist_for\|materialized_view\|increment_key\|cluster_keys\|partition_keys\|indexes\|distribution)\s*:` | redesign | Persistent derived table. |
| `native_derived_table` | `^\s*explore_source\s*:` | redesign | |
| `derived_table` | `^\s*derived_table\s*:` | mechanical | Ephemeral unless a `pdt` tag is present in the same block. |
| `html` | `^\s*html\s*:` | redesign | Withheld; the field is still emitted. |
| `link` | `^\s*link\s*:\s*\{` | assisted | |
| `case_dimension` | `^\s*case\s*:\s*\{` | assisted | Simple equality cases become `groups`. |
| `tier` | `^\s*type\s*:\s*tier` | mechanical | |
| `dimension_group_time` | `^\s*type\s*:\s*time` inside a `dimension_group` | mechanical | |
| `dimension_group_duration` | `^\s*type\s*:\s*duration` inside a `dimension_group` | assisted | |
| `unsupported_dimension_type` | `^\s*type\s*:\s*(location\|distance\|bin)` | redesign | |
| `derived_measure` | `^\s*type\s*:\s*number` inside a `measure` | assisted | |
| `unsupported_measure_type` | `^\s*type\s*:\s*(running_total\|percent_of_total\|percent_of_previous)` | redesign | |
| `distinct_measure` | `^\s*type\s*:\s*\w+_distinct\b` | mechanical | Needs `sql_distinct_key`. |
| `measure_filters` | `^\s*filters\s*:` inside a `measure` | mechanical | Each expression classified per `property_mapping.md`; a non-mechanical expression withholds the measure. |
| `date_filter_expression` | `"(\d+\s+(second\|minute\|hour\|day\|week\|month\|quarter\|year)s?(\s+ago)?\|(last\|this\|next)\s+\w+\|before\s.*\|after\s.*\|today\|yesterday\|tomorrow\|\d{4}-\d{2}-\d{2}.*)"` | assisted | Looker date grammar; never mechanical. |
| `value_format_custom` | `^\s*value_format\s*:` | mechanical / assisted | Mapped if in the table, else `needs_human`. |
| `extends` | `^\s*extends\s*:` | mechanical | |
| `extension_required` | `^\s*extension\s*:\s*required` | mechanical | Becomes `template: true`. |
| `refinement` | `^\s*(view\|explore)\s*:\s*\+\w+` | mechanical | Merged into the base before conversion. |
| `sql_always_where` | `^\s*sql_always_where\s*:` | assisted | |
| `always_filter` | `^\s*(always_filter\|conditionally_filter)\s*:` | assisted | |
| `access_filter` | `^\s*access_filter\s*:` | assisted | |
| `join_one_to_many` | `^\s*relationship\s*:\s*one_to_many` | assisted | |
| `join_many_to_many` | `^\s*relationship\s*:\s*many_to_many` | redesign | |
| `join_type_non_left` | `^\s*type\s*:\s*(inner\|full_outer)` inside a `join` | assisted | |
| `join_cross` | `^\s*type\s*:\s*cross` inside a `join` | redesign | |
| `aliased_join` | `^\s*from\s*:` inside a `join` | assisted | Topic-scoped extended view. |
| `join_sql_where` | `^\s*sql_where\s*:` inside a `join` | assisted | |
| `datagroup` | `^\s*datagroup\s*:` | mechanical | Dropped; note for `cache_policy`. |
| `set` | `^\s*set\s*:\s*\w+` | mechanical | Expanded on use. |
| `required_access_grants` | `^\s*required_access_grants\s*:` | mechanical | Grants created by `omni-target-setup`. |

## Complexity

A view's complexity for the audit, from its tags:

| Complexity | Rule |
|---|---|
| Low | Only mechanical tags |
| Medium | At least one assisted tag, no redesign tag |
| High | At least one redesign tag, or more than 30 fields with any assisted tag |

## Content signals (Looker API, not LookML)

| Signal | Source | Use |
|---|---|---|
| `views_90d`, `last_viewed` | System Activity `history` explore | Drop rule in `looker_audit/generate.md`: `views_90d = 0` and `last_viewed` older than `stale_after_days` |
| `folder_kind: personal`, `owner_active: false` | Folders and users API | Drop rule |
| `tile_type: text` or `markdown` | Dashboard elements API | Not migrated programmatically; listed for hand recreation |
| Tile `listen` map, dashboard filters | Dashboard API | `content_mapping.md` |
