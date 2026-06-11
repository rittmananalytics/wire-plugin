# Translation notes — ARRAY_AGG semantics (Snowflake → BigQuery)

Two `ARRAY_AGG` calls that look portable but aren't. The first differs in NULL handling. The second differs in how each platform builds an array of records. Both are silent traps — the naive port compiles and then misbehaves at runtime.

## Trap 1 — NULL handling is not the same default

| Platform | `ARRAY_AGG(x)` with a NULL in `x` |
|---|---|
| Snowflake | NULLs are omitted from the array — this is the default, no clause needed |
| BigQuery | defaults to RESPECT NULLS, then raises `Array cannot have a null element` because arrays may not contain NULL |

So Snowflake `array_agg(x)` is equivalent to BigQuery `array_agg(x ignore nulls)` — not to a bare `array_agg(x)`. A token-for-token translation that drops the clause compiles cleanly and passes on test data that happens to have no nulls, then fails in production the first time a NULL reaches the aggregate. Always add `IGNORE NULLS` on the BigQuery side when porting a Snowflake `ARRAY_AGG`.

Sources: [Snowflake ARRAY_AGG](https://docs.snowflake.com/en/sql-reference/functions/array_agg) · [BigQuery aggregate functions](https://cloud.google.com/bigquery/docs/reference/standard-sql/aggregate_functions).

## Trap 2 — array of records: JSON round-trip vs native STRUCT

Snowflake has no STRUCT literal usable directly inside `ARRAY_AGG`, so a common idiom — and the one in the source model these examples come from — builds each record as a JSON object string with `CONCAT` and parses it back with `PARSE_JSON`:

```sql
array_agg(parse_json(concat('{"address":"', contact_address, '", ...}')))
```

BigQuery builds the array of STRUCTs directly:

```sql
array_agg(struct(contact_address as address, contact_city as city, ...) ignore nulls)
```

| Snowflake | BigQuery |
|---|---|
| `array_agg(parse_json(concat('{"k":"', v, '"}')))` → `ARRAY` of VARIANT (JSON) | `array_agg(struct(v as k) ignore nulls)` → `ARRAY<STRUCT>` |
| Downstream access by colon path: `addr:city::string` | Downstream access by dot notation: `addr.city` (see example 02) |

This is the better outcome of the two dialects: BigQuery's result is a typed `ARRAY<STRUCT>` queryable with dot notation, where the Snowflake JSON array needs colon-path extraction and casting on every read. The migration is a chance to drop the JSON workaround, not reproduce it.

## Watch out for

- **Quote escaping in the source idiom.** The `PARSE_JSON(CONCAT(...))` pattern has no escaping — a value containing a `"` produces invalid JSON and the parse fails. If the Snowflake model has been silently tolerating this on clean data, the BigQuery STRUCT form removes the hazard, but flag any downstream consumer that was parsing the JSON defensively.
- **Field names.** In the JSON form the field names are the string keys (`"address"`, `"city"`). In the BigQuery STRUCT they come from the alias on each element (`as address`, `as city`). Carry the names across deliberately so downstream colon-path reads become matching dot-notation reads.
- **`DISTINCT` plus `IGNORE NULLS`.** Both are supported together in BigQuery (`array_agg(distinct x ignore nulls)`). Element order is not guaranteed on either platform unless you add `ORDER BY` inside the aggregate — see `translation_guide.md` for the `WITHIN GROUP` ↔ in-aggregate `ORDER BY` difference.

## Portable alternative — dispatched macro

If the project must run on both platforms, wrap the NULL-safe aggregate in a dispatched macro rather than branching in the model:

```sql
-- macros/cross_db/array_agg_safe.sql
{% macro array_agg_safe(expr) %}
  {{ return(adapter.dispatch('array_agg_safe')(expr)) }}
{% endmacro %}

{% macro bigquery__array_agg_safe(expr) %}
  array_agg({{ expr }} ignore nulls)
{% endmacro %}

{% macro snowflake__array_agg_safe(expr) %}
  array_agg({{ expr }})
{% endmacro %}
```

There is no dbt built-in cross-database macro for `ARRAY_AGG`, so this is dispatched-macro territory. See `platform_pairs/dbt_neutral_translation.md` for where this sits in the macro-first hierarchy. The record-array case is harder to abstract — STRUCT vs JSON differ in their return type, not just syntax — so for marts, prefer the native BigQuery STRUCT and treat the Snowflake JSON form as legacy to retire.

See `bigquery_to_snowflake/examples/` for the reverse direction.
