# Translation notes — array-membership join (Snowflake → BigQuery)

A dimension stores an array of identifiers — every source `company_id` that was merged into one canonical company — and a fact table joins to it by matching its single `company_id` against any element of that array. This is a different problem from example 01. There the array is *exploded into output rows*. Here the array sits on the *join-key side* and the question is membership, not expansion.

That difference forces a structural change, not a function swap.

## What changed

| Snowflake | BigQuery |
|---|---|
| Pre-flatten the array to one row per id in a CTE: `table(flatten(c.all_company_ids)) cf` projecting `cf.value::string as company_id` | Keep the array intact: `select * from dim_companies` |
| Equi-join on the flattened id: `on d.company_id = c.company_id` | Test membership inline: `on d.company_id in unnest(c.all_company_ids)` |

BigQuery can put `UNNEST` inside the join predicate, so the array never has to be expanded into its own relation. Snowflake's `FLATTEN` is a table function — it can only appear in the `FROM` clause — so the array must first become a row set in a CTE, and only then can you equi-join against it. A translator that swaps `flatten` for `unnest` token-for-token without collapsing the CTE produces SQL that compiles but reads worse and joins wrong.

## Watch out for

- **Grain.** The Snowflake pre-flatten produces one row per `(company_pk, company_id)`. As long as `all_company_ids` holds no duplicates within a company, the join grain matches the BigQuery `IN UNNEST` form. If the array can contain duplicate ids, the Snowflake side fans out and the BigQuery side does not — dedupe in the CTE (`select distinct`) to keep them equivalent.
- **Casting.** Snowflake `cf.value` comes back as VARIANT, hence the explicit `::string`. BigQuery `UNNEST` of a typed `ARRAY<STRING>` yields the scalar type directly — no cast. If the join key types differ across the two sides (e.g. the fact's `company_id` is INT64 but the array is STRING), cast on the BigQuery side too: `on cast(d.company_id as string) in unnest(c.all_company_ids)`. This mirrors the `timesheet_users_id` join in the source models.
- **Null-preserving variant.** A `LEFT JOIN` against a flattened CTE in Snowflake keeps facts with no matching company. The BigQuery equivalent is `left join unnest(...)` or a `left join` to the dimension with the membership test moved into the `on` clause — confirm the outer-join semantics survive the rewrite.
- **`generate_surrogate_key`, not `surrogate_key`.** `dbt_utils.surrogate_key` is deprecated. Use `dbt_utils.generate_surrogate_key` — both examples here do.

## Portable alternative — don't branch in the model

The real-world source these examples are drawn from carried both forms in one model behind `{% if target.type == 'snowflake' %}` / `{% elif target.type == 'bigquery' %}` branches. That works, but it scatters dialect logic through the model body and is the pattern dbt's own guidance puts last. For a project that must run on both platforms during a parallel-run window, wrap the join in a dispatched macro instead:

```sql
-- macros/cross_db/array_member_join.sql
{% macro array_member_join(scalar_col, array_col) %}
  {{ return(adapter.dispatch('array_member_join')(scalar_col, array_col)) }}
{% endmacro %}

{% macro bigquery__array_member_join(scalar_col, array_col) %}
  {{ scalar_col }} in unnest({{ array_col }})
{% endmacro %}

{% macro snowflake__array_member_join(scalar_col, array_col) %}
  array_contains({{ scalar_col }}::variant, {{ array_col }})
{% endmacro %}
```

Snowflake's `ARRAY_CONTAINS(value, array)` tests membership without a pre-flatten, which keeps the join inline on both adapters and removes the CTE asymmetry entirely. See `platform_pairs/dbt_neutral_translation.md` for the full macro-first hierarchy.

See `bigquery_to_snowflake/examples/` for the reverse direction.
