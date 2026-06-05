# Wire Platform Pairs

Translation guides, type mappings, feature-detection patterns, and worked examples for each supported source → target migration direction. Used by `/wire:migration_strategy-generate` and `/wire:dbt_migration-generate` when running a `platform_migration` release.

## Currently supported pairs

| Direction | Status |
|---|---|
| BigQuery → Snowflake | Supported (v3.7.0+) |
| Snowflake → BigQuery | Supported (v3.7.0+) |
| Databricks → BigQuery / Snowflake | Planned |
| Redshift → BigQuery / Snowflake | Planned |

## Anatomy of a platform pair

Each pair directory contains the following files:

```
wire/platform_pairs/<source>_to_<target>/
├── translation_guide.md     ← SQL construct translations (the pattern table) + dbt profile + dispatch + known limits
├── type_mapping.md          ← source type → target type lookup
├── feature_detection.md     ← regex / AST patterns used by audits to find platform-specific features
└── examples/                ← end-to-end before/after worked examples (v3.7.1+)
    ├── README.md
    ├── 01_<pattern_name>/
    │   ├── before.sql
    │   ├── after.sql
    │   └── notes.md
    └── …
```

`translation_guide.md` is the pattern table — short rules, one row per SQL construct. `examples/` is the library of worked translations used as few-shot context when the migration commands write code.

## Engagement-level overrides (v3.7.1+)

The Wire framework's canonical pair files cover the general case. Real engagements often need bespoke translations — a particular client's JSON schema is unusual, or the legacy dbt project uses a non-standard macro library, or there's an internal convention to preserve through the migration.

For these cases, drop overrides into the engagement directory:

```
.wire/engagement/platform_pair_overrides/<source>_to_<target>/
├── translation_guide.md     ← extra rows / overrides for this engagement
├── examples/                ← engagement-specific worked examples
└── …
```

When `migration_strategy-generate` or `dbt_migration-generate` runs, it reads the canonical files first, then layers the override directory on top. **Engagement overrides win where they cover the same construct; they supplement where they introduce new ones.** The resulting strategy artifact documents which decisions came from where under a "Translation overrides applied" section.

### When to use overrides vs PR back to the framework

| Situation | Approach |
|---|---|
| Translation is specific to this client's data model | Engagement override |
| Translation is specific to this client's macro library | Engagement override |
| Translation pattern appears in 2+ engagements | Promote to canonical via PR |
| The framework's canonical translation is wrong for the general case | PR back to the framework |
| You want to share a pattern with other RA consultants for now | PR back to the framework |

A reasonable workflow: during an engagement, capture novel translations as overrides. At engagement close, promote anything that's general enough into the canonical guide via a framework PR. Anything client-specific stays in the override directory and is carried into the next engagement at the same client.

## Adding a new platform pair

To add a new pair (e.g. `databricks_to_snowflake`):

1. Create the directory `wire/platform_pairs/databricks_to_snowflake/`.
2. Write `translation_guide.md`, `type_mapping.md`, `feature_detection.md` following the existing structure.
3. Add at least three end-to-end examples in `examples/`.
4. Add the new pair to the `/wire:new` release-type picker's `platform_pair` validation set (in `wire/specs/new.md`).
5. Update this README's "Currently supported pairs" table.
6. Run the platform_migration test suite at `wire/tests/platform_migration/` and add a fixture for the new pair if structural tests need it.
