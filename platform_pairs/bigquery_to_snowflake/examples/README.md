# BigQuery → Snowflake — Worked Examples

End-to-end before/after model translations for the most common BigQuery → Snowflake patterns. Each example folder contains:

- `before.sql` — a representative BigQuery dbt model (or model fragment) using the source-platform construct
- `after.sql` — the same model after translation to Snowflake-compatible SQL
- `notes.md` — the translation rationale, edge cases, and any dbt config changes

These examples are used as few-shot context by `/wire:dbt_migration-generate` when it translates dbt models. They sit alongside the canonical `translation_guide.md` (the pattern table) and `type_mapping.md` (the data-type table).

## Index

| # | Pattern | When it applies |
|---|---|---|
| 01 | `UNNEST(array)` → `LATERAL FLATTEN` | Any model that explodes arrays |
| 02 | `STRUCT(...)` + dot-notation field access → `OBJECT_CONSTRUCT` + colon-notation | Nested record types, especially from JSON ingestion |
| 03 | `TIMESTAMP_DIFF` / `DATE_ADD` / `INTERVAL` → `TIMESTAMPDIFF` / `DATEADD` | Any date or timestamp arithmetic — high frequency |
| 04 | `ML.PREDICT(MODEL ...)` → no direct equivalent | Models using BigQuery ML — requires architectural decision |
| 05 | `JOIN … ON x IN UNNEST(array)` → `ARRAY_CONTAINS(x::variant, array)` | Joining a fact to a dimension that stores an array of ids (e.g. merged-entity id lists) |
| 06 | `ARRAY_AGG(… IGNORE NULLS)` and native `STRUCT` arrays → `ARRAY_AGG(...)` and `OBJECT_CONSTRUCT` | Any aggregation rolling rows up into arrays — scalar or record |

For projects that must run on both warehouses, see `wire/platform_pairs/dbt_neutral_translation.md` — the macro-first hierarchy these examples point back to.

## Adding new examples

To add a new example to this canonical set, PR a new numbered folder containing the three files. New examples should:

- Be derived from real engagement work, anonymised (no real client names, real data values, or real schema names).
- Be self-contained — the `before.sql` should compile against BigQuery without external context, and `after.sql` against Snowflake.
- Include a `notes.md` covering: what changed, why, any dbt config impact, edge cases, and whether a Wire macro now handles this pattern.

For engagement-specific examples that aren't general enough for the canonical set, use the per-engagement override slot at `.wire/engagement/platform_pair_overrides/bigquery_to_snowflake/examples/`. See `wire/platform_pairs/README.md` for how overrides work.
