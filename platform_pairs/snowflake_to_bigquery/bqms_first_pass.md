# BigQuery Migration Service — Automated First-Pass Translation

The BigQuery Migration Service (BQMS) is Google's managed SQL translation engine. It converts DDL and queries from a source dialect — Snowflake, Teradata, Oracle, Redshift, and others — into GoogleSQL, and returns a translation report flagging anything it could not translate cleanly. Use it as an **automated first pass** that Wire's canonical translation guide then reviews and corrects.

## When this applies

BQMS only translates *to* BigQuery. It is relevant for the **snowflake → bigquery** pair and not for the reverse. If the target platform is not BigQuery, skip this entirely and translate against [`translation_guide.md`](./translation_guide.md) directly.

It is a tool, not a replacement for the translation guide. BQMS handles dialect mechanics — function renames, type mapping, syntax — but it knows nothing about the dbt project: macros, `dispatch` overrides, materialisation config, `ref()`/`source()`, or the engagement-level overrides in `.wire/engagement/platform_pair_overrides/`. Treat its output as raw translated SQL to be reconciled against the guide, never as finished dbt models.

## What it does

Two interfaces, same engine:

- **Batch SQL Translator** — point it at a GCS folder of `.sql` files, it writes translated files plus a translation report to an output folder. Right for bulk DDL and query translation.
- **Interactive SQL Translator** — single-statement translation via API or the console. Right for spot-checking one tricky model.

The API lives at `google.cloud.bigquery.migration.v2`. You create a `MigrationWorkflow` with a translation task, supply a source dialect and config, and poll for completion. Access via the `google-cloud-bigquery-migration` client library or `gcloud`.

Configuration worth setting:

- **Object name mapping** — remap source `database.schema.table` to target `project.dataset.table`. Without this, BQMS keeps source names that won't resolve on BigQuery.
- **Default database / schema search path** — so unqualified identifiers resolve correctly.

## Reference implementations

Google's Professional Services repo has two utilities built around exactly this flow — extract source DDL, call the Migration API, create the target tables, log each conversion to an audit table:

- [`bigquery-snowflake-tables-migration-utility`](https://github.com/GoogleCloudPlatform/professional-services/tree/main/examples/bigquery-snowflake-tables-migration-utility) — Snowflake-specific. Pulls table DDL via the Snowflake connector's `GET_DDL`, converts through BQMS, creates BigQuery tables (carrying over partitioning and clustering), and archives the intermediate DDL.
- [`bigquery-generic-ddl-migration-utility`](https://github.com/GoogleCloudPlatform/professional-services/tree/main/examples/bigquery-generic-ddl-migration-utility) — the same pattern generalised across Oracle, Snowflake, MSSQL, Vertica, and Netezza, reading from each source's metadata tables.

Two patterns from these are worth lifting regardless of whether you run the utilities directly:

1. **Per-object audit logging** — write a row per table conversion (object name, status, timestamp, any translation warnings) to an audit table on the target. It gives a clean record of what translated cleanly and what needs hand-finishing.
2. **Metadata + partition/cluster carry-over** — the target DDL should preserve partitioning and clustering intent, not just columns and types.

## How it slots into the Wire flow

- **`target_setup` (DDL)** — run source DDL through the Batch SQL Translator to get a first-pass set of `CREATE TABLE` statements, then reconcile against [`type_mapping.md`](./type_mapping.md) before writing the final target DDL scripts. BQMS gets the bulk of the column/type work right; the guide catches the lossless-conversion flags (e.g. `NUMBER` precision, `VARIANT` → `JSON` vs `STRING`).
- **`dbt_migration` (model SQL)** — translate the *compiled* SQL of a model as a first pass to surface the dialect changes, then port those changes back into the dbt model by hand, applying macros and config per [`translation_guide.md`](./translation_guide.md). Do not feed raw Jinja to BQMS — it cannot parse it.
- **`migration_strategy`** — when scoping the translation approach, decide per layer whether BQMS first-pass is worth the setup. For a large, mechanical DDL set it usually is. For a small project with heavy macro use, hand translation against the guide is often faster.

## Limitations to plan around

- It translates SQL, not dbt. Everything above the SQL — Jinja, macros, config, lineage — is still manual.
- The translation report's warnings are the signal worth reading. An empty report does not guarantee semantic equivalence; that is what the `equivalency` checks are for.
- Setup cost is real (GCS staging, API enablement, IAM). For a handful of models the interactive translator or hand translation beats wiring up a batch job.
