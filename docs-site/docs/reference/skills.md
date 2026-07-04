---
sidebar_position: 2
title: Skills Reference
---

# Skills Reference

Wire skills are Markdown files that Claude loads as instruction sets. Unlike commands (which you invoke explicitly), most skills **auto-activate** — they fire when you're doing work that matches their trigger conditions, without you needing to reference them.

Skills ship as part of the Wire plugin. They live in `wire/skills/<name>/SKILL.md`.

---

## dbt development

### `dbt-development`

**Activates when**: creating, reviewing, or refactoring dbt models in staging, integration, or warehouse layers.

Enforces Wire's three-layer dbt architecture and naming conventions:
- Staging models: `stg_<source>__<entity>.sql` — one-to-one with source tables, minimal transformation
- Integration models: `int_<domain>__<description>.sql` — business logic, joins, deduplication
- Warehouse models: `dim_<entity>.sql` / `fct_<entity>.sql` — final analytics-ready tables

Validates: naming conventions, PK/FK field naming (`_pk`, `_fk`), boolean prefixes (`is_`, `has_`), timestamp suffix (`_ts`), test coverage (every model needs at minimum `not_null` + `unique` on its PK), and documentation completeness.

Integrates with sqlfluff when present in the project. Supports project-specific convention overrides via `CLAUDE.md`.

---

### `dbt-migration`

**Activates when**: migrating a dbt project between data platforms (BigQuery ↔ Snowflake ↔ Databricks) or upgrading between dbt versions.

Provides a systematic migration workflow: audit the source project → classify models by migration complexity (trivial / low / medium / high / blocked) → translate in batches → validate equivalency. Marks translated models with `-- WIRE:REVIEW` (non-trivial dialect differences) or `-- WIRE:REWRITE` (platform-coupled logic requiring manual attention).

---

### `dbt-semantic-layer`

**Activates when**: working with semantic models, MetricFlow metrics, entities, or dimensions in dbt.

Covers the dbt Semantic Layer with MetricFlow: semantic model definitions, metric types (simple, ratio, cumulative, derived), entity relationships, and dimension groups. Supports both the current spec (dbt Core 1.12+ / dbt Fusion) and legacy formats (1.6–1.11). Distinct from LookML — this skill covers MetricFlow only.

---

### `dbt-troubleshooting`

**Activates when**: encountering dbt errors, failed jobs, compilation issues, or test failures.

Provides a systematic diagnosis workflow: classify the error type (compilation, runtime, test, environment) → identify root cause → apply resolution pattern. Covers the most common failure categories: missing source definitions, ref before model exists, environment variable mismatches, BigQuery/Snowflake permission errors, and incremental model state issues.

---

### `dbt-analytics-qa`

**Activates when**: running analytics QA against dbt model outputs.

Generates a structured QA checklist for dbt mart models: row counts vs source, null rates, value distributions, referential integrity, freshness. Produces a QA report suitable for client review.

---

### `dbt-dag`

**Activates when**: working with dbt lineage, model dependencies, or DAG structure.

Helps design and validate the dbt model dependency graph: identifies circular references, orphaned models, overly-wide fans, and models with too many direct dependencies. Produces a lineage summary and a set of structural recommendations.

---

### `dbt-unit-testing`

**Activates when**: writing or reviewing dbt unit tests.

Covers dbt's native unit testing framework (dbt Core 1.8+): test structure, `given`/`expect` blocks, mocking sources and refs, and common patterns for testing business logic in SQL.

---

### `dbt-fusion`

**Activates when**: working with dbt Fusion (the Rust-based dbt engine).

Covers dbt Fusion-specific behaviour, config differences from dbt Core, and performance characteristics. Useful when a client is on or migrating to the Fusion engine.

---

### `dbt-mcp-server`

**Activates when**: using the dbt MCP server for semantic layer queries or dbt Cloud integration.

Covers the dbt MCP server's tool set: querying metrics, listing semantic models, running dbt commands via MCP, and integrating the semantic layer with Claude Code sessions.

---

## BI and reporting

### `lookml-content-authoring`

**Activates when**: writing or modifying LookML views, explores, measures, dimensions, or dashboards.

Enforces Wire's LookML conventions:
- Views must reference real data sources — never mock data
- Use `${TABLE}.column` syntax with exact case-matching
- Validate field references against source DDL before writing
- Explores live in model files, not view files
- Dashboard tiles reference explores by `explore_source`, not raw SQL

Covers both local file editing and the Looker MCP server (read from live Looker instance, push changes back). Includes validation against source DDL to catch column name mismatches before they reach production.

---

### `looker-dashboard-mockup`

**Activates when**: creating or iterating on Looker dashboard mockups in the `dashboard_first` or `full_platform` release types.

Produces interactive HTML mockups with sample data that match Looker's visual conventions — tile layouts, filter bars, dimension/measure chips. Mockups reference the Wire design system (colours, typography, chart types). Used in the `mockups-generate` command to create client-facing wireframes before any real data is connected.

---

### `metabase`

**Activates when**: auditing or migrating a Metabase reporting layer — cataloguing collections, dashboards, cards/questions, database connections, or permission groups, or repointing Metabase from one warehouse to another.

Connects to a Metabase instance (metabase-cli serialization export, the REST API, or a client-supplied query inventory) and maps the collection → dashboard → card hierarchy, each card's SQL and its warehouse dependencies, the database connections, and the permission groups. Used by the `metabase-audit-*` and `metabase-migration-*` platform-migration commands (gated on `migration.reporting_tool: metabase`, not on migration scope). Wraps the upstream `metabase/agent-skills` (metabase-cli, metabase-representation-format, metabase-database-metadata).

---

### `cube`

**Activates when**: building or reviewing a Cube.dev semantic-layer model — cubes, views, dimensions, measures, joins, or pre-aggregations — or connecting to a live Cube deployment via its MCP server; also activates for semantic-layer work in other release types where the client's semantic layer is Cube rather than LookML.

Covers Cube's core concepts (cubes vs. views, dimensions, measures, joins, pre-aggregations) and the Cube MCP server connection flow, and encodes Rittman Analytics' own Cube modeling conventions and coding standards — project/folder structure, naming, per-object-type standards, security, style, and a Definition of Done checklist — as the canonical reference for how RA builds Cube models. Referenced by `semantic_layer-generate` when the engagement's semantic layer is Cube rather than Looker.

---

### `omni`

**Activates when**: auditing or migrating an Omni Analytics reporting layer — cataloguing connections, the semantic model, dashboards/tiles, or repointing Omni from one warehouse to another; also activates for semantic-layer or dashboard work in other release types where the client's BI tool is Omni.

Connects via the Omni CLI and maps the connection → model (topics, views, dimensions, measures, relationships) → folder → workbook → tile hierarchy, each view's warehouse dependencies, and which tiles carry a raw-SQL override versus querying through the model. Used by the `omni-audit-*` and `omni-migration-*` platform-migration commands (gated on `migration.reporting_tool: omni`, not on migration scope), and referenced by `semantic_layer-generate` when the engagement's BI tool is Omni rather than Looker. Wraps the official `exploreomni/omni-agent-skills` (omni-model-explorer, omni-model-builder, omni-content-explorer, omni-content-builder, omni-query, omni-admin).

---

### `smml-semantic-modeling`

**Activates when**: hand-authoring, editing, reviewing, or troubleshooting an Oracle Analytics Cloud (OAC) semantic model directly in SMML (Semantic Modeler Markup Language) — physical/logical/presentation layers, role-playing dimensions, hierarchies, calculated measures, or subject-area design.

Covers the SMML object model (every layer, property, and enum, confidence-tagged by whether it's ground-truth-validated against a real OAC import or sourced from Oracle's own schema doc) and the judgement calls that separate a mechanically-correct model from one that behaves right in OAC. Ships `scripts/validate_smml.py`, a structural validator shared with `dbt-to-smml`. This is the modeling knowledge the `dbt-to-smml` generator is built on.

---

### `dbt-to-smml`

**Activates when**: generating, converting, or scaffolding an OAC semantic model in SMML from a dbt project — driven by dbt's `manifest.json`/`catalog.json` plus `meta.oac` annotations in `schema.yml`.

A deterministic generator (`scripts/generate_smml.py`) that turns dbt's physical truth (tables, columns, types) into SMML's physical/logical/presentation layers, with `meta.oac` metadata supplying the semantics a script can't infer (measures, hierarchies, role-playing dimensions, subject areas). Referenced by `semantic_layer-generate` when the engagement's semantic layer is OAC rather than Looker. Builds on the modeling knowledge in the sibling `smml-semantic-modeling` skill.

---

## Data ingestion

### `fivetran`

**Activates when**: configuring Fivetran connectors, destinations, transformations, or groups — either via the Fivetran MCP server or from connector config files.

Covers all 78 tools exposed by the Fivetran MCP server: listing and creating connections, modifying connector schema config, syncing, pausing, and monitoring. Also covers writing Fivetran connector YAML configuration and integration with Wire's `pipeline-generate` command.

---

### `airbyte`

**Activates when**: working with Airbyte connections, sources, or destinations via the Airbyte Agent MCP server.

Covers the hosted Airbyte Agent MCP (for AI agents using connectors) and managing an existing Airbyte Cloud or OSS workspace. Distinguishes between the two deployment modes and provides appropriate guidance for each. Integrates with Wire's `pipeline-generate` command for Airbyte-based ingestion configurations.

---

## Orchestration

### `dagster`

**Activates when**: creating or modifying Dagster assets, schedules, sensors, or components, or when working on the `orchestration` artifact in a Wire project.

Covers the assets-first pattern, `dagster-dbt` integration, automation (schedules, sensors, declarative automation), the component framework, and CLI usage (`dg dev`, `dg launch`, `dg check`, `dg scaffold`). Integrates with Wire's `orchestration-generate` command for Dagster-based orchestration layers.

---

## Warehouse

### `snowflake-development`

**Activates when**: querying, designing, or auditing Snowflake objects, running migrations, assessing AI-readiness, or using the Snowflake MCP server.

Covers SQL conventions, object management, performance patterns, dynamic tables, streams, tasks, and data quality assessment. Includes Snowflake-specific Wire conventions (stage naming, warehouse sizing, role hierarchy).

---

## Schema introspection

### `droughty`

**Activates when**: working with Droughty commands, profile/project configuration, LookML generation from warehouse schemas, dbt test generation, DBML diagrams, field documentation, or data quality reports.

Provides full coverage of the Droughty toolkit: `droughty introspect`, `droughty dbml`, `droughty docs`, `droughty qa`, `droughty lookml`, `droughty dbt-tests`, `droughty stage`. Handles profile configuration (`~/.droughty/profile.yaml`) for BigQuery and Snowflake. Integrates with Wire's Droughty release type commands.

---

## Wire Framework meta-skills

### `engagement-context`

**Activates automatically** when a `.wire/` directory is present in the repository root and context has not yet been established in the current session.

Reads `.wire/releases/` to identify active releases, loads `status.md` for the most recently-active release, and outputs a brief context summary at the start of the session. This is what makes Wire "remember" where you left off — no session start command needed. Appends context to the beginning of every session silently.

---

### `wire-release`

**Activates when**: creating a new Wire Framework release, bumping the version number, or saying "release this as vX.Y".

Covers the full release lifecycle: bump type selection, pre-release cleanup, documentation updates (CHANGELOG, USER_GUIDE, README files), VS Code extension updates, plugin rebuild via `build-packages.sh`, remote pushes to all three plugin repos, PR creation, and docs-site sync. See the [Advanced → Extending Wire](../advanced/extending) section for the full release workflow.

---

### `project-review`

**Activates when**: reviewing a Wire engagement's overall progress, running a project health check, or preparing a client status update.

Reads the execution log, artifact states, and open decisions across all releases in the engagement. Produces a structured project review: what's complete, what's in progress, what's blocked, open design decisions, and recommended next actions.

---

## Research and utilities

### `research`

**Activates when**: performing technical research — looking up library documentation, warehouse schemas, API references, or comparing implementation approaches.

Saves structured research summaries to `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md`. The engagement-context skill checks these on session load and surfaces prior findings rather than re-running the same research. Cross-release knowledge accumulates here.

---

### `dignified-python`

**Activates when**: writing Python code in a Wire project — Cloud Functions, dlt pipelines, data quality scripts, or deployment automation.

Enforces Python conventions: type hints, structured logging, environment variable handling (never hardcoded credentials), error handling patterns, and packaging (`requirements.txt`, `Dockerfile` for Cloud Run deployments). Integrates with Wire's pipeline and deployment artifact conventions.
