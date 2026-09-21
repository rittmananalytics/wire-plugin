---
sidebar_position: 2
title: Skills Reference
---

# Skills Reference

Much of the day-to-day work on an engagement is not a Wire command at all: you are writing a dbt model, fixing a LookML view or working out why a job failed overnight, and what you want is for the conventions Wire encodes to apply to that work without your having to look them up. That is what skills are for. Wire skills are Markdown files that Claude loads as instruction sets, and unlike commands, which you invoke explicitly, most skills **auto-activate**, which is to say they "fire" when the work you are doing matches their trigger conditions, without you needing to reference them.

Skills ship as part of the Wire plugin, and they live in `wire/skills/<name>/SKILL.md`. In the sections that follow we take each skill in turn, grouped by the area of work it covers, noting when it activates and what it does for you.

---

## dbt development

Most of the code Wire writes is dbt, and so the largest group of skills is the one that keeps that code consistent, from the naming of a staging model through to the way a failed run is diagnosed.

### `dbt-development`

**Activates when**: creating, reviewing or refactoring dbt models in staging, integration or warehouse layers.

This skill enforces Wire's three-layer dbt architecture and naming conventions, so that a model written with it active comes out in the shape the rest of the project expects:
- Staging models (`stg_<source>__<entity>.sql`): one-to-one with source tables, minimal transformation
- Integration models (`int_<domain>__<description>.sql`): business logic, joins, deduplication
- Warehouse models (`dim_<entity>.sql` / `fct_<entity>.sql`): final analytics-ready tables

It validates naming conventions, PK/FK field naming (`_pk`, `_fk`), boolean prefixes (`is_`, `has_`), timestamp suffix (`_ts`), test coverage (every model needs at minimum `not_null` + `unique` on its PK) and documentation completeness.

It integrates with sqlfluff when that is present in the project, and it supports project-specific convention overrides via `CLAUDE.md`.

---

### `dbt-migration`

**Activates when**: migrating a dbt project between data platforms (BigQuery ↔ Snowflake ↔ Databricks) or upgrading between dbt versions.

Moving a dbt project from one platform to another is mostly mechanical but never entirely so, and this skill provides a systematic migration workflow for it: audit the source project → classify models by migration complexity (trivial / low / medium / high / blocked) → translate in batches → validate equivalency. Translated models are marked with `-- WIRE:REVIEW` where there are non-trivial dialect differences, or with `-- WIRE:REWRITE` where platform-coupled logic requires manual attention, so that you know which of them to look at first.

---

### `dbt-semantic-layer`

**Activates when**: working with semantic models, MetricFlow metrics, entities or dimensions in dbt.

This skill covers the dbt Semantic Layer with MetricFlow: semantic model definitions, metric types (simple, ratio, cumulative, derived), entity relationships and dimension groups. It supports both the current spec (dbt Core 1.12+ / dbt Fusion) and the legacy formats (1.6–1.11). It is distinct from LookML, however, and covers MetricFlow only; for LookML see `lookml-content-authoring` below.

---

### `dbt-troubleshooting`

**Activates when**: encountering dbt errors, failed jobs, compilation issues or test failures.

When a dbt run fails the temptation is to start editing SQL before you know what kind of failure you have, and this skill provides a systematic diagnosis workflow instead: classify the error type (compilation, runtime, test, environment) → identify the root cause → apply the resolution pattern. It covers the most common failure categories: missing source definitions, ref before model exists, environment variable mismatches, BigQuery/Snowflake permission errors and incremental model state issues.

---

### `dbt-analytics-qa`

**Activates when**: running analytics QA against dbt model outputs.

Before a mart goes in front of a client you will want evidence that it reconciles to its sources, and this skill generates a structured QA checklist for dbt mart models to gather it: row counts vs source, null rates, value distributions, referential integrity, freshness. It then produces a QA report suitable for client review.

---

### `dbt-dag`

**Activates when**: working with dbt lineage, model dependencies or DAG structure.

This skill helps you design and validate the dbt model dependency graph, identifying circular references, orphaned models, overly-wide fans and models with too many direct dependencies, and it produces a lineage summary together with a set of structural recommendations.

---

### `dbt-unit-testing`

**Activates when**: writing or reviewing dbt unit tests.

This skill covers dbt's native unit testing framework (dbt Core 1.8+): test structure, `given`/`expect` blocks, the mocking of sources and refs, as well as the common patterns for testing business logic in SQL.

---

### `dbt-fusion`

**Activates when**: working with dbt Fusion (the Rust-based dbt engine).

This skill covers dbt Fusion-specific behaviour, config differences from dbt Core and performance characteristics, and it is useful when a client is on or migrating to the Fusion engine.

---

### `dbt-mcp-server`

**Activates when**: using the dbt MCP server for semantic layer queries or dbt Cloud integration.

This skill covers the dbt MCP server's tool set: querying metrics, listing semantic models, running dbt commands via MCP and integrating the semantic layer with Claude Code sessions.

---

## BI and reporting

The reporting layer is where the client sees the work, and the skills in this group cover each of the BI tools and semantic layers Wire builds for or migrates from, starting with Looker.

### `lookml-content-authoring`

**Activates when**: writing or modifying LookML views, explores, measures, dimensions or dashboards.

A LookML view that names a column its table does not have is a mistake you want to catch before it reaches production, and so this skill enforces Wire's LookML conventions as you write:
- Views must reference real data sources, never mock data
- Use `${TABLE}.column` syntax with exact case-matching
- Validate field references against source DDL before writing
- Explores live in model files, not view files
- Dashboard tiles reference explores by `explore_source`, not raw SQL

It covers both local file editing and the Looker MCP server (read from the live Looker instance, push changes back), and it includes validation against source DDL to catch column name mismatches before they reach production.

---

### `looker-dashboard-mockup`

**Activates when**: creating or iterating on Looker dashboard mockups in the `dashboard_first` or `full_platform` release types.

Clients find it easier to react to a dashboard they can click on than to a list of metrics, and this skill produces interactive HTML mockups with sample data that match Looker's visual conventions (tile layouts, filter bars, dimension/measure chips). The mockups reference the Wire design system (colours, typography, chart types), and the skill is used in the `mockups-generate` command to create client-facing "wireframes" before any real data is connected.

---

### `metabase`

**Activates when**: auditing or migrating a Metabase reporting layer: cataloguing collections, dashboards, cards/questions, database connections or permission groups, or repointing Metabase from one warehouse to another.

This skill connects to a Metabase instance (metabase-cli serialization export, the REST API or a client-supplied query inventory) and maps the collection → dashboard → card hierarchy, each card's SQL and its warehouse dependencies, the database connections and the permission groups. It is used by the `metabase-audit-*` and `metabase-migration-*` platform-migration commands (gated on `migration.reporting_tool: metabase`, not on migration scope), and it wraps the upstream `metabase/agent-skills` (metabase-cli, metabase-representation-format, metabase-database-metadata).

---

### `cube`

**Activates when**: building or reviewing a Cube.dev semantic-layer model (cubes, views, dimensions, measures, joins or pre-aggregations) or connecting to a live Cube deployment via its MCP server; also activates for semantic-layer work in other release types where the client's semantic layer is Cube rather than LookML.

This skill covers Cube's core concepts (cubes vs. views, dimensions, measures, joins, pre-aggregations) and the Cube MCP server connection flow, and it encodes Rittman Analytics' own Cube modelling conventions and coding standards (project/folder structure, naming, per-object-type standards, security, style and a "Definition of Done" checklist) as the canonical reference for how RA builds Cube models. It is referenced by `semantic_layer-generate` when the engagement's semantic layer is Cube rather than Looker.

---

### `omni`

**Activates when**: auditing or migrating an Omni Analytics reporting layer: cataloguing connections, the semantic model or dashboards/tiles, or repointing Omni from one warehouse to another; also activates for semantic-layer or dashboard work in other release types where the client's BI tool is Omni.

This skill connects via the Omni CLI and maps the connection → model (topics, views, dimensions, measures, relationships) → folder → workbook → tile hierarchy, each view's warehouse dependencies and which tiles carry a raw-SQL override rather than querying through the model. It is used by the `omni-audit-*` and `omni-migration-*` platform-migration commands (gated on `migration.reporting_tool: omni`, not on migration scope) and referenced by `semantic_layer-generate` when the engagement's BI tool is Omni rather than Looker, and it wraps the official `exploreomni/omni-agent-skills` (omni-model-explorer, omni-model-builder, omni-content-explorer, omni-content-builder, omni-query, omni-admin).

---


### `dbtcharts`

**Activates when**: the user mentions dbt Charts, `dct`, or a board file under `charts/`, or asks for a dashboard over dbt models where the reporting tool is dbt Charts.

Boards are YAML files in the dbt project (queries through `ref()`, charts, a layout) that the `dct` CLI validates and renders. The skill carries the Wire board rules (`ref()`-only queries, no inline data, `notes:` on every query and chart, `label:` on KPIs and `title:` elsewhere, one board per subject area), the deterministic scaffold `scripts/dbtcharts_scaffold.py`, and the validate-then-render loop. It is used by `/wire:dbtcharts-generate`, `-validate` and `-review`, and points to `dct docs` and `dct skills` as the field reference so no key is guessed. See [dbt Charts Boards](../advanced/dbt-charts).
### `agents-schema`

**Activates when**: the user mentions Agents Schema, `AGENTS.ROOT`, the `agents-schema` CLI or its GitHub workflows, warehouse-delivered skills, or asks how an AI agent should find governed context for a warehouse.

Agents Schema is dbt Labs' standard `AGENTS` schema inside Snowflake, Databricks or BigQuery, holding what the dbt manifest, the semantic layer and a set of markdown skills say about the warehouse. The skill carries the table contract, the two publication routes (the pinned reusable GitHub workflows, or `uvx --from agents-schema==<version>` from a laptop with the credentials in an environment variable), the skill front-matter rules the CLI enforces, the consumer side (`ROOT` first, lowercase on BigQuery, uppercase on Snowflake, the dbt Labs plugin marketplace) and the things found the hard way: every manifest model node is published, `ROOT` is shared across publishers, a malformed `uses:` is skipped silently. It is used by `/wire:agents_schema-generate`, `-validate` and `-review`. See [Agents Schema](../advanced/agents-schema).

---

### `smml-semantic-modeling`

**Activates when**: hand-authoring, editing, reviewing or troubleshooting an Oracle Analytics Cloud (OAC) semantic model directly in SMML (Semantic Modeler Markup Language): physical/logical/presentation layers, role-playing dimensions, hierarchies, calculated measures or subject-area design.

This skill covers the SMML object model (every layer, property and enum, confidence-tagged by whether it is ground-truth-validated against a real OAC import or sourced from Oracle's own schema doc) as well as the judgement calls that separate a mechanically-correct model from one that behaves right in OAC. It ships `scripts/validate_smml.py`, a structural validator shared with `dbt-to-smml`, and it is the modelling knowledge on which the `dbt-to-smml` generator, described next, is built.

---

### `dbt-to-smml`

**Activates when**: generating, converting or scaffolding an OAC semantic model in SMML from a dbt project, driven by dbt's `manifest.json`/`catalog.json` plus `meta.oac` annotations in `schema.yml`.

Where the previous skill is knowledge, this one is a deterministic generator (`scripts/generate_smml.py`) that turns dbt's physical truth (tables, columns, types) into SMML's physical/logical/presentation layers, with `meta.oac` metadata supplying the semantics a script cannot infer (measures, hierarchies, role-playing dimensions, subject areas). It is referenced by `semantic_layer-generate` when the engagement's semantic layer is OAC rather than Looker, and it builds on the modelling knowledge in the sibling `smml-semantic-modeling` skill.

---

## Data ingestion

### `fivetran`

**Activates when**: configuring Fivetran connectors, destinations, transformations or groups, either via the Fivetran MCP server or from connector config files.

This skill covers all 78 tools exposed by the Fivetran MCP server: listing and creating connections, modifying connector schema config, syncing, pausing and monitoring. It also covers writing Fivetran connector YAML configuration, together with the integration with Wire's `pipeline-generate` command.

---

### `airbyte`

**Activates when**: working with Airbyte connections, sources or destinations via the Airbyte Agent MCP server.

This skill covers the hosted Airbyte Agent MCP (for AI agents using connectors) as well as managing an existing Airbyte Cloud or OSS workspace, and since these are two different deployment modes it distinguishes between them and provides the appropriate guidance for each. It integrates with Wire's `pipeline-generate` command for Airbyte-based ingestion configurations.

---

## Orchestration

### `dagster`

**Activates when**: creating or modifying Dagster assets, schedules, sensors or components, or when working on the `orchestration` artifact in a Wire project.

This skill covers the "assets-first" pattern, `dagster-dbt` integration, automation (schedules, sensors, declarative automation), the component framework and CLI usage (`dg dev`, `dg launch`, `dg check`, `dg scaffold`), and it integrates with Wire's `orchestration-generate` command for Dagster-based orchestration layers.

---

## Warehouse

### `snowflake-development`

**Activates when**: querying, designing or auditing Snowflake objects, running migrations, assessing AI-readiness or using the Snowflake MCP server.

This skill covers SQL conventions, object management, performance patterns, dynamic tables, streams, tasks and data quality assessment, and it includes the Snowflake-specific Wire conventions (stage naming, warehouse sizing, role hierarchy).

---

## Schema introspection

### `droughty`

**Activates when**: working with Droughty commands, profile/project configuration, LookML generation from warehouse schemas, dbt test generation, DBML diagrams, field documentation or data quality reports.

Droughty reads the warehouse schema and generates LookML, dbt tests and DBML diagrams from what it finds there, and this skill provides full coverage of the toolkit: `droughty introspect`, `droughty dbml`, `droughty docs`, `droughty qa`, `droughty lookml`, `droughty dbt-tests`, `droughty stage`. It handles profile configuration (`~/.droughty/profile.yaml`) for BigQuery and Snowflake, and it integrates with Wire's Droughty release type commands.

---

## Wire Framework meta-skills

The skills so far are about the client's platform; the ones in this group are about Wire itself, and two of them run without any trigger from you at all.

### `engagement-context`

**Activates automatically** when a `.wire/` directory is present in the repository root and context has not yet been established in the current session.

Have you ever opened a project after a week away and spent the first half hour working out where you had got to? This skill reads `.wire/releases/` to identify active releases, loads `status.md` for the most recently-active release and outputs a brief context summary at the start of the session, which is what makes Wire "remember" where you left off with no session start command needed. It appends that context to the beginning of every session silently.

---

### `fathom-sync`

**Activates automatically** once per new conversation, right after `engagement-context` loads, when `.wire/engagement/context.md` has `fathom_sync.enabled: true` and the Fathom MCP server is reachable.

This skill pulls any new Fathom call transcripts for the engagement's client into `.wire/engagement/calls/` since the last sync, with an analytical findings write-up per call, and it is silent if nothing is new and prints one brief line if something was found. It is kept as a separate skill from `engagement-context` deliberately, since it can be slow (MCP calls, multiple file writes, a real analytical pass) and should not make the fast context-load feel sluggish. It runs on Claude Code only, as there is no Gemini CLI equivalent; see [Fathom Call Sync](../advanced/fathom-sync).

---

### `wire-release`

**Activates when**: creating a new Wire Framework release, bumping the version number or saying "release this as vX.Y".

This is a skill for Wire's own maintainers rather than for client work, and it covers the full release lifecycle: bump type selection, pre-release cleanup, documentation updates (CHANGELOG, USER_GUIDE, README files), VS Code extension updates, plugin rebuild via `build-packages.sh`, remote pushes to all three plugin repos, PR creation and docs-site sync. See the [Advanced → Extending Wire](../advanced/extending) section for the full release workflow.

---

### `project-review`

**Activates when**: reviewing how Wire was used on an engagement, auditing delivery against the record or preparing a usage review for a client.

This skill reads the engagement repository and nothing else: the git history, every release's `status.md`, and the full execution log, including its outcome, attribution, invocation, duration, token and cost columns where a run recorded them. It needs no telemetry warehouse, issue tracker or meeting recorder, so any organisation running Wire can use it. It produces a structured review: artifact and commit coverage against what the release type defines, where rework concentrated and how long each artifact took to reach approval, every recorded override with its stated reason, how the work was invoked (typed, orchestrated, by lane or by autopilot), measured effort and cost where the metrics hook filled them, the work the git history shows was done outside any command, and recommendations. The review is written to `.wire/reviews/` in the repository it describes. The log it reads is described in [Core Concepts → The execution log](../getting-started/core-concepts#the-execution-log); to repair the record rather than review it, use [`/wire:status-sync`](../reference/management-commands#wirestatus-sync).

---

## Research and utilities

### `research`

**Activates when**: performing technical research: looking up library documentation, warehouse schemas or API references, or comparing implementation approaches.

Research done in one session is easily lost by the next, and so this skill saves structured research summaries to `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md`. The engagement-context skill checks these on session load and surfaces prior findings rather than re-running the same research, which is how knowledge accumulates across releases.

---

### `dignified-python`

**Activates when**: writing Python code in a Wire project, whether Cloud Functions, dlt pipelines, data quality scripts or deployment automation.

This skill enforces Python conventions: type hints, structured logging, environment variable handling (never hardcoded credentials), error handling patterns and packaging (`requirements.txt`, `Dockerfile` for Cloud Run deployments), and it integrates with Wire's pipeline and deployment artifact conventions.
