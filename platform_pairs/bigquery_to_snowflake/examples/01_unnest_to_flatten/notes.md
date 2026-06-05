# Translation notes — UNNEST → LATERAL FLATTEN

## What changed

| BigQuery | Snowflake |
|---|---|
| `unnest(array_col) as alias` | `lateral flatten(input => array_col) alias` |
| `alias.field_name` (dot notation on STRUCT) | `alias.value:field_name::TYPE` (colon-path + explicit cast on VARIANT) |
| Implicit type of struct fields | Explicit `::number`, `::varchar`, `::timestamp_ntz` casts |

## Why

In BigQuery, `UNNEST` of a repeated record produces a STRUCT per row, and STRUCT fields are accessed by dot notation with the platform inferring the type from the schema.

In Snowflake, `LATERAL FLATTEN` produces VARIANT rows. Every field access on a VARIANT must use the colon-path syntax (`alias.value:field_name`), and unless you cast explicitly the result will be typed as VARIANT all the way down. Downstream models can't filter or aggregate on VARIANT columns without errors, so the cast is mandatory at the point of unpacking.

## dbt config impact

None. Both versions are `+materialized: view` or `+materialized: table` per the project default — `LATERAL FLATTEN` has no special config requirement on Snowflake.

## Edge cases

- **Empty arrays**: BigQuery's `UNNEST` returns zero rows for an empty array; the parent row is dropped. Snowflake's `LATERAL FLATTEN` with default `outer => false` does the same. If you need the parent row preserved (e.g. orders with no line items show as `null`-line-item rows), use `lateral flatten(input => o.order_lines, outer => true)`.
- **Index column**: BigQuery requires `UNNEST(arr) WITH OFFSET` to get the array index; Snowflake provides `alias.index` (no extra clause). Worth knowing if any source model uses the index.
- **Null arrays**: Same behaviour as empty — zero rows produced. If the column might be `null`, wrap in `coalesce(array_col, array_construct())` to be explicit.

## Wire macro equivalent

The translation guide refers to `{{ bq_to_sf.unnest(array_col) }}` for the FROM-clause portion. The field-level casts still need to be written by hand because they depend on the source schema. `dbt_migration-generate` produces both the FROM-clause translation and the SELECT-list casts in one pass when given the source DDL.
