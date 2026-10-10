# Worked examples

Each example is a hand-written Metabase snapshot (`before/`, in the layout `metabase_export.py api` writes) and the converter's output for it (`after/`): LookML views, the model file, LookML dashboards, `needs_human.json`, `conversion_summary.json` and `dependencies.jsonl`. `wire/tests/bi_migration/validate_mb_to_lookml.py` round-trips every example byte for byte, so a converter change is a deliberate change to these files. The client (Halcyon) is fictional; the examples are cut from `wire/tests/bi_migration/fixture/metabase/`.

| Example | Shows |
|---|---|
| `01_fk_join_and_metric` | A metric as a filtered measure; a question reading a field through a foreign key, so an explore join from the metadata; "previous 11 months including this one" as `12 months` |
| `02_explicit_join_and_having` | A question's own join to a primary key; a ratio of aggregations as a `type: number` measure; second-stage filters on the ratio and on the grouping column |
| `03_native_sql` | A native question with a variable and an optional field filter as a view with a parameter and a templated filter; a simple native question also lifted onto the table's view |
| `04_dashboard_tabs_and_filters` | Two tabs as two LookML dashboards; the 24-column grid kept; a filter through a foreign key with `listen`; a date default translated; a date-grouping filter and a link card listed |

Regenerate after a deliberate converter change: `python3 wire/tests/bi_migration/validate_mb_to_lookml.py --update`, then review the diff.
