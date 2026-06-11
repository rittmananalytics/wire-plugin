# Translation notes — array-membership join (BigQuery → Snowflake)

The reverse of `snowflake_to_bigquery/examples/04`. A dimension stores an array of identifiers — every source `company_id` merged into one canonical company — and a fact matches its single `company_id` against any element of that array.

In BigQuery the membership test goes straight into the join: `on d.company_id in unnest(c.all_company_ids)`. Snowflake has a direct equivalent — `ARRAY_CONTAINS` — so this does **not** need a pre-flatten CTE.

## What changed

| BigQuery | Snowflake |
|---|---|
| `on d.company_id in unnest(c.all_company_ids)` | `on array_contains(d.company_id::variant, c.all_company_ids)` |

## Watch out for

- **Argument order reverses.** BigQuery reads `value IN UNNEST(array)`; Snowflake's `ARRAY_CONTAINS(value, array)` puts the value first. Easy to flip.
- **The value must be VARIANT.** `ARRAY_CONTAINS` expects its first argument as VARIANT — hence `d.company_id::variant`. Without the cast you get a type error or a silent non-match depending on the source type.
- **Element type must match.** `all_company_ids` is a Snowflake VARIANT array, so its elements compare as VARIANT. If the array was built from strings, cast the probe value to string first (`d.company_id::string::variant`) so the comparison is like-for-like.
- **Don't reach for `TABLE(FLATTEN(...))` here.** A pre-flatten CTE plus equi-join is the older idiom and works, but it fans the join out to one row per array element and changes the grain. `ARRAY_CONTAINS` keeps the join inline and the grain intact. Only pre-flatten when you genuinely need the individual elements as rows for something else.

See `snowflake_to_bigquery/examples/04_array_membership_join/notes.md` for the forward direction and the dispatched-macro form that keeps this portable across both adapters.
