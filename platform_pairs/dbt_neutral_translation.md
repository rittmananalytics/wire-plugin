# dbt-Neutral Translation — Macro-First Strategy

This doc applies to every platform pair. The per-pair `translation_guide.md` files tell you what a construct becomes on the target dialect. This doc tells you *where to put* that difference so the dbt project stays maintainable — ideally a single project that compiles on both the source and target warehouse through a parallel-run window, not two diverging copies.

dbt is the right abstraction for a warehouse migration because model structure, lineage, tests, docs, and environments stay stable while the dialect-specific SQL moves behind macros. Keep business logic in models. Push dialect differences down into macros.

## The hierarchy — reach for the highest rung that works

```
1. dbt built-in cross-database macro   (dbt.dateadd, dbt.cast, dbt.type_string …)
2. dbt_utils macro                     (generate_surrogate_key, star, union_relations …)
3. your own dispatched macro           (adapter.dispatch — for JSON, arrays, DDL-ish behaviour)
4. target.type branching inside a macro
5. target.type branching inside a model   ← last resort
```

The source models a migration starts from often live at rung 5 — `{% if target.type == 'snowflake' %} … {% elif target.type == 'bigquery' %} … {% endif %}` scattered through the model body. That compiles, but it spreads dialect logic across every model and makes the project hard to read and to test. Migrate it *up* the hierarchy as you go.

## Rung 1 — dbt built-in cross-database macros

dbt ships macros that compile to the right SQL per adapter. Prefer these over hand-written dialect SQL for the common cases.

### Types

| Need | Macro |
|---|---|
| String | `{{ dbt.type_string() }}` |
| Integer | `{{ dbt.type_int() }}` |
| Big integer | `{{ dbt.type_bigint() }}` |
| Numeric | `{{ dbt.type_numeric() }}` |
| Float | `{{ dbt.type_float() }}` |
| Boolean | `{{ dbt.type_boolean() }}` |
| Timestamp | `{{ dbt.type_timestamp() }}` |

### Casts

| Intent | dbt-neutral |
|---|---|
| `cast(x as varchar)` | `{{ dbt.cast('x', dbt.type_string()) }}` |
| `try_cast(x as number)` | `{{ dbt.safe_cast('x', dbt.type_numeric()) }}` |
| `try_cast(x as date)` | `{{ dbt.safe_cast('x', 'date') }}` |

### Dates and timestamps

| Need | dbt-neutral |
|---|---|
| Current timestamp | `{{ dbt.current_timestamp() }}` |
| Date from expression | `{{ dbt.date('created_at') }}` |
| Add interval | `{{ dbt.dateadd('day', 7, 'order_date') }}` |
| Difference | `{{ dbt.datediff('start_date', 'end_date', 'day') }}` |
| Truncate | `{{ dbt.date_trunc('month', 'order_date') }}` |
| Last day | `{{ dbt.last_day('order_date', 'month') }}` |

### Strings and aggregates

| Need | dbt-neutral |
|---|---|
| Concatenate | `{{ dbt.concat(['first_name', "' '", 'last_name']) }}` |
| Hash | `{{ dbt.hash('customer_id') }}` |
| Length | `{{ dbt.length('col') }}` |
| Split part | `{{ dbt.split_part('col', "'-'", 1) }}` |
| List aggregation | `{{ dbt.listagg('order_id', "','") }}` |
| Boolean OR aggregate | `{{ dbt.bool_or('flag') }}` |
| Set difference / intersect | `{{ dbt.except() }}` / `{{ dbt.intersect() }}` |

The set operators are handy when writing equivalence checks that diff source against target.

## Rung 2 — dbt_utils

Use `dbt_utils.generate_surrogate_key` for keys rather than hand-rolling a hash. It absorbs the differences in hashing, NULL handling, and string concatenation between platforms, which is exactly where hand-written keys drift between a source and target warehouse.

```sql
{{ dbt_utils.generate_surrogate_key(['customer_id', 'order_id', 'order_date']) }} as order_key
```

(Note: `dbt_utils.surrogate_key` is deprecated — use `generate_surrogate_key`.)

## Rung 3 — your own dispatched macros

JSON, arrays, and semi-structured handling are where the built-ins run out. Snowflake `VARIANT` / `LATERAL FLATTEN` and BigQuery `JSON` / `STRUCT` / `UNNEST` don't map one-to-one, so write a dispatched macro and keep the model clean.

```sql
-- macros/cross_db/json_get_scalar.sql
{% macro json_get_scalar(json_col, json_path) %}
  {{ return(adapter.dispatch('json_get_scalar')(json_col, json_path)) }}
{% endmacro %}

{% macro snowflake__json_get_scalar(json_col, json_path) %}
  {{ json_col }}:{{ json_path | replace('$.', '') }}::string
{% endmacro %}

{% macro bigquery__json_get_scalar(json_col, json_path) %}
  json_value({{ json_col }}, '{{ json_path }}')
{% endmacro %}

{% macro default__json_get_scalar(json_col, json_path) %}
  {{ exceptions.raise_compiler_error("json_get_scalar is not implemented for this adapter") }}
{% endmacro %}
```

The worked examples in each pair's `examples/` folder show concrete dispatched-macro alternatives for array-membership joins and NULL-safe `ARRAY_AGG` — patterns with no built-in equivalent.

## Profiles, not models, hold environment differences

Keep one dbt project. Add a target per warehouse in `profiles.yml` and run the same models against each.

```yaml
my_project:
  target: snowflake_dev
  outputs:
    snowflake_dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      database: ANALYTICS
      warehouse: TRANSFORMING
      schema: dbt_dev
      threads: 8
    bigquery_dev:
      type: bigquery
      method: service-account
      project: "{{ env_var('BQ_PROJECT') }}"
      dataset: dbt_dev
      keyfile: "{{ env_var('BQ_KEYFILE') }}"
      location: europe-west2
      threads: 8
```

```bash
dbt build --target snowflake_dev
dbt build --target bigquery_dev
```

Use `source()` and `ref()` everywhere — never hardcode `database.schema.table`. For BigQuery, source `database` maps to the GCP project and `schema` maps to the dataset; parameterise both through `vars` so the same `sources.yml` resolves on either platform.

## Incremental models

The portable shape is `materialized='incremental'` with `incremental_strategy='merge'` and a `unique_key`. Two things to watch:

- **Literals aren't neutral.** `timestamp('1900-01-01')` is BigQuery-only. Use `{{ dbt.safe_cast("'1900-01-01'", dbt.type_timestamp()) }}` in the `is_incremental()` watermark filter.
- **Partition and cluster config is warehouse-specific.** BigQuery wants `partition_by={...}` plus `cluster_by`; Snowflake wants `cluster_by` only. Keep these in model-level YAML, folder-level config, or a small wrapper macro rather than a `target.type` block in the model. Making BigQuery partitioning explicit is usually the single biggest cost and performance lever in the migration.

## Prove equivalence — compilation is only step one

Translated SQL that compiles is not translated SQL that's correct. Freeze the source outputs before you start and diff the target against them. Build an aggregate audit model and run it on both targets:

```sql
select
  'fct_orders' as model_name,
  count(*)                  as row_count,
  count(distinct order_id)  as distinct_orders,
  min(order_date)           as min_order_date,
  max(order_date)           as max_order_date,
  sum(order_total)          as total_revenue
from {{ ref('fct_orders') }}
```

| Check | Catches |
|---|---|
| Row count | Missing or duplicated rows |
| Distinct primary keys | Merge / grain issues (e.g. array-membership join fan-out) |
| Null counts | Casting or JSON-parsing breakage |
| Min/max dates | Timezone drift (`TIMESTAMP_NTZ` → `DATETIME` vs `TIMESTAMP`) |
| Revenue / financial totals | Numeric precision differences |
| Hash totals | Row-level drift aggregate checks miss |

Validate at the model grain, not just in aggregate — aggregate sums can match while individual rows are wrong. This is what the `/wire:equivalency-*` commands automate; this doc is the manual backbone they follow.

## Ten practical rules

1. Macro every dialect difference, not every expression — keep models readable.
2. Use dbt built-ins for dates, casts, strings, and types. Rarely hand-write these.
3. Use dispatched macros for JSON, arrays, and DDL-ish behaviour.
4. Don't overuse `target.type` in models. Hide it in a macro if you must use it at all.
5. Make BigQuery partitioning explicit.
6. Validate at the model grain — aggregate checks hide duplicates.
7. Normalise timestamps early in staging. Decide `TIMESTAMP_NTZ` → `DATETIME` or `TIMESTAMP` once.
8. Prefer typed nested fields (STRUCT) over raw JSON in BigQuery marts.
9. Move environment differences into `profiles.yml`, `vars`, and folder configs.
10. Treat compilation success as step one. Semantic equivalence needs real test data.

## How this slots into Wire

- `migration_strategy-generate` — sets the per-layer translation approach. Decide here how aggressively to push toward dbt-neutral macros versus a one-direction rewrite that decommissions the source.
- `dbt_migration-generate` — applies the per-pair `translation_guide.md` and `examples/`, then lifts dialect logic up this hierarchy. The guiding principle: **models express business logic, macros absorb dialect differences, tests prove equivalence.**
- `equivalency-validate` / `equivalency-investigate` — run the audit-model diffs above against both targets.

References: [dbt cross-database macros](https://docs.getdbt.com/reference/dbt-jinja-functions/cross-database-macros) · [dbt dispatch](https://docs.getdbt.com/reference/dbt-jinja-functions/dispatch).
