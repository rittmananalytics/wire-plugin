# 01 Plain view

Every row here is `mechanical`.

- `sql_table_name: analytics.dim_customers` becomes `schema` and `table_name`. The file lands at `analytics/customers.view`.
- `customer_id` and `full_name` reference their own column through `${TABLE}`, so they are emitted with no `sql:`. Omni auto-maps a plain column dimension by name.
- `country` reads a differently named column, so it keeps `sql: ${country_code}`. There is no `${TABLE}` in Omni.
- `type: number` and `type: string` are dropped; Omni infers types.
- `hidden: yes` becomes `hidden: true`; `value_format_name: usd` becomes `format: currency_2`.
- `type: count` becomes `aggregate_type: count`; `type: sum` becomes `aggregate_type: sum`.
