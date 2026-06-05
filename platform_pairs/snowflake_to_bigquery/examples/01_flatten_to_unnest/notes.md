# Translation notes — LATERAL FLATTEN → UNNEST

The reverse of the BQ → SF case. The main shift is: VARIANT/colon-path becomes STRUCT/dot-notation, and explicit casts (`::type`) become BigQuery `cast(... as TYPE)` calls.

## What changed

| Snowflake | BigQuery |
|---|---|
| `lateral flatten(input => array_col) alias` | `unnest(array_col) as alias` |
| `alias.value:field::TYPE` | `cast(alias.field as TYPE)` or `alias.field` if the source array is a STRUCT type |
| `outer => true` for null-preserving flatten | `LEFT JOIN UNNEST(array_col) WITH OFFSET` (BQ pattern; OFFSET preserves index) |

## Watch out for

- **Source array typing**: in Snowflake, an array is VARIANT — fields are accessed by colon path. In BigQuery, the equivalent is an ARRAY of STRUCT — fields are accessed by dot notation directly. The dbt_migration step rewrites field access based on the source schema discovered during db_object_audit.
- **Implicit vs explicit casts**: Snowflake colon access returns VARIANT; you cast explicitly. BigQuery STRUCT field access returns the typed scalar — but if the upstream array is itself VARIANT-typed (e.g. JSON ingestion), you still need explicit casts on the way out.
- **NUMBER → NUMERIC vs INT64**: `number(18,4)` becomes BigQuery `NUMERIC` (38-digit fixed precision). Pure integer `number` becomes `INT64`. The type_mapping.md file is authoritative.

See `bigquery_to_snowflake/examples/01_unnest_to_flatten/notes.md` for the forward direction.
