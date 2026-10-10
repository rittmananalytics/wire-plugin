# Worked examples

Each example is one or more hand-written `report.json` files (`before/<report id>/`, in the shape `looker_studio_extract.py` writes) and the converter's output (`after/`). `wire/tests/bi_migration/validate_ls_to_lookml.py` round-trips each one byte for byte. The client (Halcyon) is fictional; the examples are cut from `wire/tests/bi_migration/fixture/looker_studio_to_looker/`.

| Example | Shows |
|---|---|
| `01_bigquery_table_and_calculated_fields` | A BigQuery table as a view; a row-level calculated field with `SAFE_DIVIDE`; a chart-level formula as a measure |
| `02_looker_connector` | Charts on Looker Studio's Looker connector pointed at the existing explore; the dashboard in `dashboards/<model>/` |
| `03_controls_and_date_ranges` | Date range and dimension filter controls as dashboard filters; a chart's own date range; a text date cast to a date; a breakdown pivot; custom SQL as a view; Record Count |

Regenerate after a deliberate converter change: `python3 wire/tests/bi_migration/validate_ls_to_lookml.py --update`, then review the diff.
