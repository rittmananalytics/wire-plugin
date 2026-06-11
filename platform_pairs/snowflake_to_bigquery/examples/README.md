# Snowflake → BigQuery — Worked Examples

End-to-end before/after model translations for the most common Snowflake → BigQuery patterns. Each example folder contains:

- `before.sql` — a representative Snowflake dbt model using the source-platform construct
- `after.sql` — the same model after translation to BigQuery-compatible SQL
- `notes.md` — translation rationale, edge cases, dbt config changes

Used by `/wire:dbt_migration-generate` as few-shot context.

## Index

| # | Pattern | When it applies |
|---|---|---|
| 01 | `LATERAL FLATTEN` → `UNNEST` | Any model exploding arrays or VARIANT lists |
| 02 | `OBJECT_CONSTRUCT` + colon-path → `STRUCT` + dot notation | Nested record construction and access |
| 03 | `DATEDIFF` / `DATEADD` → `DATE_DIFF` / `DATE_ADD` with INTERVAL | Date and timestamp arithmetic — high frequency |
| 04 | pre-flatten CTE + equi-join → `JOIN … ON x IN UNNEST(array)` | Joining a fact to a dimension that stores an array of ids (e.g. merged-entity id lists) |
| 05 | `ARRAY_AGG` NULL handling and `PARSE_JSON(CONCAT(...))` record arrays → `ARRAY_AGG(… IGNORE NULLS)` and native `STRUCT` | Any aggregation rolling rows up into arrays — scalar or record |

Each `notes.md` ends with a "Portable alternative" section. Examples 04 and 05 cover patterns with no dbt built-in equivalent, so the portable form is a dispatched macro — see `wire/platform_pairs/dbt_neutral_translation.md` for the macro-first hierarchy these point back to.

See `wire/platform_pairs/bigquery_to_snowflake/examples/` for the reverse direction. The conceptual notes are mostly the same — just reverse the arrows.

## Adding new examples

Follow the same convention as the BQ→SF set. For engagement-specific examples that aren't general enough for the canonical set, use the per-engagement override slot at `.wire/engagement/platform_pair_overrides/snowflake_to_bigquery/examples/`.
