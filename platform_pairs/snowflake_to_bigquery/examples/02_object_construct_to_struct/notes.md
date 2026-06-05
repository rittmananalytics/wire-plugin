# Translation notes — OBJECT_CONSTRUCT → STRUCT

Reverse of the BQ → SF case. Snowflake's name/value-paired OBJECT becomes BigQuery's positional STRUCT; colon-path with casts becomes dot notation with implicit typing.

## What changed

| Snowflake | BigQuery |
|---|---|
| `object_construct('field_a', a, 'field_b', b)` | `struct(a, b)` — but field names come from source columns, so make sure source column names match desired STRUCT field names |
| `record:field::TYPE` | `record.field` |
| `where record:field::varchar = 'X'` | `where record.field = 'X'` (cast not needed) |

## The naming trap

In Snowflake's OBJECT_CONSTRUCT, field names are explicit string literals. You can rename a field at construction time:

```sql
object_construct('display_name', first_name || ' ' || last_name)
```

In BigQuery STRUCT, field names come from the source column name or an explicit alias. The above translates to:

```sql
struct((first_name || ' ' || last_name) as display_name)
```

`dbt_migration-generate` handles the rename automatically by inspecting the OBJECT_CONSTRUCT key/value pairs and emitting `as <key>` clauses on each STRUCT element where needed.

See `bigquery_to_snowflake/examples/02_struct_to_object_construct/notes.md` for the conceptual underpinning.
