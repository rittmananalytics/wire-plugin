# Translation notes — STRUCT + dot notation → OBJECT_CONSTRUCT + colon path

## What changed

| BigQuery | Snowflake |
|---|---|
| `struct(field_a, field_b)` (implicit field names from source columns) | `object_construct('field_a', field_a, 'field_b', field_b)` (explicit name/value pairs) |
| `record.field_name` | `record:field_name::TYPE` |
| `where record.field_name = 'X'` | `where record:field_name::varchar = 'X'` (cast required in WHERE too) |

## Why

BigQuery STRUCT is a strongly-typed record. Field access by dot notation returns a typed scalar.

Snowflake's nearest equivalent is OBJECT (a VARIANT subtype). Field names must be explicit at construction time because OBJECT is a key/value map, not a positional record. Field access by colon path returns VARIANT — the cast (`::varchar`, `::number(18,2)`, `::timestamp_ntz`) is what makes the value usable in filters, joins, and aggregates.

A common trap: forgetting the cast in WHERE/JOIN clauses. The query will compile but the comparison will be VARIANT-vs-string, which doesn't behave the way a SQL author expects. Always cast on field extraction.

## dbt config impact

None for the model itself. However, if any source schema.yml documents the STRUCT field columns with tests (e.g. `not_null` on `address.country_code`), those tests must be rewritten to test the colon-path expression. Wire's `dbt_migration-generate` does this automatically when it sees STRUCT-typed columns in the source schema.

## Edge cases

- **Nested STRUCTs**: BigQuery allows `struct(struct(x, y) as inner)` — Snowflake nests with `object_construct('inner', object_construct(...))`. Field access becomes `outer:inner:x::TYPE`.
- **NULL handling**: BigQuery's dot access on a null STRUCT returns null. Snowflake's colon-path on a null OBJECT also returns null. Behaviour matches; no special handling needed.
- **Schema evolution**: if the source data adds a new field to a STRUCT, the BigQuery model breaks at compile. The Snowflake OBJECT pattern is forgiving — extra fields are ignored. This usually surfaces in week 2 of a migration when production data deviates from the schema you tested against.

## Wire macro equivalent

`{{ bq_to_sf.struct(field_a=field_a, field_b=field_b) }}` produces the OBJECT_CONSTRUCT call. Field access translations are not macro'd — they're handled by `dbt_migration-generate` walking the source schema and applying casts in the SELECT and WHERE clauses.
