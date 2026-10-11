# Worked examples

Each example is a hand-written Omni snapshot (`before/`, in the layout `omni_export.py snapshot` writes) and the converter's output for it (`after/`): LookML views, the model file, LookML dashboards, `needs_human.json`, `parity_map.json`, `conversion_summary.json` and `dependencies.jsonl`. `wire/tests/bi_migration/validate_omni_to_lookml.py` round-trips every example byte for byte, so a converter change is a deliberate change to these files. The client (Halcyon) is fictional.

| Example | Shows |
|---|---|
| `01_schema_view_and_measures` | A schema view: columns, a time field with timeframes, a currency format, bare columns qualified, a filtered sum, a derived measure |
| `02_topic_joins_and_alias` | A topic with nested joins flattened, an alias joined with `from:`, a relationship declared from the other side reversed and listed, `always_where_sql` |
| `03_query_views_bins_groups` | A SQL query view as a derived table, a `SELECT *` view as `sql_table_name`, bins as a tier (listed), groups as a case |
| `04_dashboard_filters_controls` | A dashboard: a KPI with a "this quarter" window, a stacked column with a pivot, a negated string filter and a table calculation, a string control with `listen`, a SQL tile listed |

Regenerate after a deliberate converter change: `python3 wire/tests/bi_migration/validate_omni_to_lookml.py --update`, then review the diff.
