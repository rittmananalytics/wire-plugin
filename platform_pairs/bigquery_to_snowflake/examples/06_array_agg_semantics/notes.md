# Translation notes — ARRAY_AGG semantics (BigQuery → Snowflake)

The reverse of `snowflake_to_bigquery/examples/05`. Two `ARRAY_AGG` calls that differ between dialects: NULL handling, and how each builds an array of records. Going BigQuery → Snowflake both differences relax — there is no runtime error to avoid — but the SQL still has to change.

## Trap 1 — drop IGNORE NULLS (it's a no-op on Snowflake)

| BigQuery | Snowflake |
|---|---|
| `array_agg(x ignore nulls)` | `array_agg(x)` |
| `array_agg(x)` (RESPECT NULLS default) — **errors** if a NULL reaches it | `array_agg(x)` — omits NULLs silently |

Snowflake `ARRAY_AGG` omits NULLs by default and has no `IGNORE NULLS` clause in this position, so the clause is simply removed. The semantics match BigQuery's `IGNORE NULLS` form. There's no reverse hazard here — unlike the forward direction, where dropping the clause causes a BigQuery runtime error.

## Trap 2 — STRUCT array becomes OBJECT_CONSTRUCT array

BigQuery builds a typed `ARRAY<STRUCT>` with positional fields and aliases. Snowflake has no STRUCT literal — the equivalent is an array of OBJECTs built with `OBJECT_CONSTRUCT`, which takes explicit `'key', value` pairs:

| BigQuery | Snowflake |
|---|---|
| `array_agg(struct(addr as address, city as city) ignore nulls)` | `array_agg(object_construct('address', addr, 'city', city))` |
| Downstream access by dot notation: `a.city` | Downstream access by colon path: `a:city::varchar` (see example 02) |

This is the same STRUCT ↔ OBJECT_CONSTRUCT shift as example 02, applied inside an aggregate. The field names move from element aliases to string keys.

## Watch out for

- **Don't translate to `PARSE_JSON(CONCAT(...))`.** Some hand-written Snowflake models build object arrays by string-concatenating JSON and parsing it back. `OBJECT_CONSTRUCT` is the correct, safe target — it handles typing and quote-escaping that the concat idiom does not. Treat any inherited `parse_json(concat(...))` as legacy, not a pattern to reproduce.
- **NULL keys in OBJECT_CONSTRUCT.** `OBJECT_CONSTRUCT` drops key/value pairs where the value is NULL. If a downstream consumer expects every key present (even with a null), use `OBJECT_CONSTRUCT_KEEP_NULL` instead.
- **Element order** is not guaranteed on either platform without an explicit `ORDER BY` inside the aggregate.

See `snowflake_to_bigquery/examples/05_array_agg_semantics/notes.md` for the forward direction, where the NULL difference is a runtime trap rather than a no-op.
