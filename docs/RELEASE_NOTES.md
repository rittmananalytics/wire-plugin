# Wire Framework v3.9.0 Release Notes

**Release date**: 2026-06-12

## Overview

Wire Agents Phase 1 — 12 specialist agents and /wire:delegate local execution

## What Changed

- Twelve specialist agent definitions covering all Wire release types (full_platform, pipeline_only, dbt_development, dashboard_extension, platform_migration, discovery, sop_discovery, agentic_commerce, agentic_data_stack, droughty)
- New /wire:delegate command replaces /wire:orchestrate — batch dispatch to specialist local subagents; runs on the user's workstation using their existing Claude Code API key, no managed agents service required
- Each agent appends decisions to decisions.md; downstream agents and human reviewers use this as a lightweight audit trail
- Auto-delegation: individual generate/validate commands now delegate to the appropriate specialist subagent automatically; review commands remain in the main session
- All 12 agent definitions bundled into the distributed plugin

---

# Wire Framework v3.8.6 Release Notes

**Release date**: 2026-06-12

## Overview

Wire Agents Phase 1 — specialist managed agents and orchestrate command

## What Changed

- Eight specialist agents (dbt-developer, lookml-developer, dashboard-prototyper, migration-auditor, qa-agent, data-quality-agent, stakeholder-interviewer, playbook-generator) defined in wire/agents/
- New /wire:orchestrate command decomposes pending release work and dispatches to parallel Claude Managed Agent sessions
- Build script bundles wire/agents/ into the distributed plugin
- status.md gains an agents block tracking mode, active sessions, and completed sessions
- /wire:upgrade surfaces /wire:orchestrate for releases created before v3.9


---

# Wire Framework v3.8.5 Release Notes

**Release date**: 2026-06-12

## Overview

Wire-aware PR template and utils-pr-create command

## What Changed

- New /wire:utils-pr-create command auto-populates PR body from execution_log.md and status.md
- wire:new Step 10.5 scaffolds .github/pull_request_template.md during engagement setup
- Wire-aware PR template covers release folder, artifacts changed, commands run/next, and issue links



### New Techniques & Commands

- **Learn**: New /wire:utils-pr-create command auto-populates PR body from execution_log.md and status.md
- **Learn**: wire:new Step 10.5 scaffolds .github/pull_request_template.md during engagement setup
- **Learn**: Wire-aware PR template covers release folder, artifacts changed, commands run/next, and issue links

---

# Wire Framework v3.8.4 Release Notes

**Release date**: 2026-06-12

## Overview

dbt migration now covers the companion schema/properties YAML, not just the model SQL — `sources.yml` repointing, dialect-bearing test translation, and dbt-managed column policy tags.

## What Changed

- `dbt-migration-generate` and `-validate` now handle the **companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`) alongside the model `.sql`.
- Adds an explicit step to repoint `sources.yml` to the target namespace (parameterised `database`/`schema`), translate source-dialect SQL inside singular/custom tests, `where:` filters, and `dbt_utils`/`dbt_expectations` arguments, and author column-level `policy_tags`/`meta` into the YAML when column protection is dbt-managed — or record it as deferred to the security workstream.
- New `dbt-migration-validate` Check 7 enforces companion-YAML coverage (un-repointed `sources.yml`, untranslated test SQL, or dropped policy-tag/meta config fail the check).



### New Techniques & Commands

- **Learn**: Two new platform_pairs translation examples in both directions: array-membership joins (FLATTEN / IN UNNEST / ARRAY_CONTAINS) and ARRAY_AGG null and struct-array semantics
- **Learn**: New shared dbt_neutral_translation.md: macro-first hierarchy (dbt built-in to dbt_utils to dispatched macro to target.type last) and the equivalence-testing backbone for dual-target dbt projects
- **Learn**: New snowflake_to_bigquery/translation_reference.md: exhaustive deep reference with a 25-item silent-behaviour-change checklist; corrected PARSE_JSON and QUALIFY entries in the quick translation guide
- **Learn**: New /wire:dbt-migration-lint command: static, offline pre-warehouse equivalence lint (dialect parse-check plus silent-behaviour-change rules) run before the live equivalency loop
- **Learn**: New feature-detection tags: flatten_join, array_agg, in_unnest

---

# Wire Framework v3.8.0 Release Notes

**Release date**: 2026-06-10

## Overview

Integrates the Droughty schema-introspection toolkit into Wire as a first-class release type and command namespace, adding bottom-up warehouse analysis to Wire's top-down document-driven delivery workflow.

## What Changed

- New `droughty` release type for schema introspection, warehouse audits, and post-dbt base-layer generation
- 9 new `/wire:droughty-*` commands covering setup, schema inventory, DBML diagram, AI field descriptions, data quality agent, staging SQL generation, dbt test generation, and LookML base view generation
- Pinned version mechanism: `wire/droughty/pinned_version.txt` pins Droughty at `0.20.1`; `wire/droughty/refresh_version.sh` lets repo owners update the pin to the latest PyPI release with a single command
- LookML file organisation convention: Droughty writes base views to `views/generated/`; Wire extensions (explores, refinements) go in `views/extended/` — never hand-edit `views/generated/`
- Droughty operates in two modes: **discovery/audit** (maps an existing warehouse — no dbt needed) and **post-dbt** (generates base layer from deployed dbt models, feeding into `/wire:semantic_layer-generate`)
- Full user guide section added (section 19) with step-by-step walkthroughs for both modes

### New Commands

| Command | Description |
|---------|-------------|
| `/wire:droughty-setup` | Install Droughty, generate profile.yaml + droughty_project.yaml |
| `/wire:droughty-introspect` | Schema inventory: tables, columns, PK/FK coverage |
| `/wire:droughty-dbml` | DBML entity-relationship diagram |
| `/wire:droughty-docs` | AI field descriptions (OpenAI) |
| `/wire:droughty-qa` | LangGraph data quality agent (OpenAI) |
| `/wire:droughty-stage` | Staging SQL + sources.yml (BigQuery only) |
| `/wire:droughty-dbt-tests` | Pattern-based schema.yml tests |
| `/wire:droughty-lookml` | Base LookML views from deployed dbt tables |
| `/wire:droughty-generate` | Full Droughty phase in sequence |

### Prerequisites for New Commands

- Python 3.9–3.12.3 (Droughty requirement)
- BigQuery Application Default Credentials (`gcloud auth application-default login`) or Snowflake credentials
- OpenAI API key for `/wire:droughty-docs` and `/wire:droughty-qa`
- dbt models deployed to the warehouse for `/wire:droughty-dbt-tests`, `/wire:droughty-stage`, and `/wire:droughty-lookml`

---

# Wire Framework v3.7.9 Release Notes

**Release date**: 2026-06-10

## Overview

Add GCP cloud skills, Amplitude product-analytics skills, and platform_migration hardening

## What Changed

- Six Google Cloud skills (bigquery-basics, cloud-run-basics, gcloud, recipe-auth, two WAF pillars) from google/skills
- 26 Amplitude product-analytics skills plus the Amplitude MCP server registered in Wire's MCP catalog
- platform_migration: BigQuery Migration Service documented as an optional first-pass DDL/SQL translator
- platform_migration: new row-level checksum and business-invariant equivalency checks plus edge-case canonicalisation
- platform_migration: cutover rehearsal step, rollback decision tree, and 7-14 day rollback window with separate decommission
- platform_migration: AI-translation safeguards in dbt_migration (confidence rating, record-loss and hallucination guards)



### New Techniques & Commands

- **Learn**: Six Google Cloud skills (bigquery-basics, cloud-run-basics, gcloud, recipe-auth, two WAF pillars) from google/skills
- **Learn**: 26 Amplitude product-analytics skills plus the Amplitude MCP server registered in Wire's MCP catalog
- **Learn**: platform_migration: BigQuery Migration Service documented as an optional first-pass DDL/SQL translator
- **Learn**: platform_migration: new row-level checksum and business-invariant equivalency checks plus edge-case canonicalisation
- **Learn**: platform_migration: cutover rehearsal step, rollback decision tree, and 7-14 day rollback window with separate decommission
- **Learn**: platform_migration: AI-translation safeguards in dbt_migration (confidence rating, record-loss and hallucination guards)

---

# Wire Framework v3.7.8 Release Notes

**Release date**: 2026-06-08

## Overview

Adds Git repository as an alternative data source for Hightouch reverse ETL audits

## What Changed

- Hightouch reverse ETL audit can now source config from a Git repo (audit/hightouch_git/) as an alternative to the REST API or CSV fallback
- Full model SQL available from Git source — no 200-character truncation as with the API
- Validation checks 6 and 8 auto-pass with informative skip messages when data source is Git
- Three-option data source waterfall in generate spec: API → Git → CSV, with clear user guidance at each fallback



### New Techniques & Commands

- **Learn**: Hightouch reverse ETL audit can now source config from a Git repo (audit/hightouch_git/) as an alternative to the REST API or CSV fallback
- **Learn**: Full model SQL available from Git source — no 200-character truncation as with the API
- **Learn**: Validation checks 6 and 8 auto-pass with informative skip messages when data source is Git
- **Learn**: Three-option data source waterfall in generate spec: API → Git → CSV, with clear user guidance at each fallback

---

# Wire Framework v3.7.7 Release Notes

**Release date**: 2026-06-08

## Overview

Adds first-class Snowflake support and a new Hightouch reverse ETL audit type to the `platform_migration` release. Wire can now audit a full Snowflake estate using the Snowflake MCP server, catalog all Snowflake-native object types (Dynamic Tables, Streams, Tasks, Pipes, Semantic Views, masking/row-access policies), and assess datasets for AI-readiness. Separately, Hightouch deployments are now a sixth, conditional audit type: Wire catalogs every sync, maps the warehouse objects each sync reads from, generates a migration runbook (repoint / rewrite / rebuild), and extends the lineage diagram with Reverse ETL and Destinations layers so stakeholders can see the full data flow from ingestion source through to SaaS destination.

## What's New

### Snowflake skills

Two new skills activate automatically when working with Snowflake:

**`snowflake-development`** — the general-purpose Snowflake skill. Covers MCP server connection verification, SQL conventions (IFF, TRY_CAST, VARIANT colon notation, QUALIFY, LISTAGG, timestamp types), a reference table of all Snowflake-native object types and their ACCOUNT_USAGE views, Dynamic Table and Stream/Task patterns with migration notes, and a structured AI-readiness assessment across five factors (Clean, Contextual, Consumable, Current, Compliant) that scores 0–1 per factor and produces a formatted readiness report.

**`snowflake-semantic-views`** — dedicated to Cortex Analyst semantic views. Three creation workflows: FastGen (AI-generated YAML draft), SQL DDL (full clause-ordered DDL with temp-object validation), and YAML (via `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML` verify-only flag). Covers adding Verified Query Records (VQRs), an audit checklist, and a debug table mapping common Cortex Analyst failure modes to root causes and targeted fixes.

### Enhanced `db_object_audit` for Snowflake source

The Snowflake branch of `/wire:db-object-audit-generate` is substantially expanded:

- All queries now explicitly target `mcp__claude_ai_Snowflake__sql_exec`
- Ten ACCOUNT_USAGE queries cover: tables/views, stored procedures, UDFs, stages, dynamic tables, streams, tasks, pipes, row access policies, masking policies, and `SHOW SHARES`
- `SHOW SEMANTIC VIEWS IN DATABASE` detects Cortex Analyst semantic layer objects
- Default migration approach table per Snowflake object type (all eight Snowflake-native types default to `evaluate` — none can be automatically translated)
- `status.md` YAML updated with fields for every new object type count

### Hightouch reverse ETL audit (sixth audit type)

Activated when `migration.reverse_etl_tool: hightouch` is set in `status.md`. Runs as a conditional sixth parallel subagent in `/wire:migration-audit-all`.

**Audit** (`/wire:reverse-etl-audit-generate`): enumerates Sources, Models, Destinations, and Syncs via the Hightouch REST API (CSV fallback when token is unavailable). Extracts warehouse object dependencies from rawSql model queries; cross-references dbtModel syncs against the dbt audit. Classifies each sync as Low / Medium / High complexity and assigns a migration approach: `repoint`, `rewrite_model`, `rebuild`, or `decommission`. Flags Lightning engine syncs requiring schema provisioning on the target warehouse.

**Migration** (`/wire:reverse-etl-migration-generate`): produces a step-by-step runbook for each sync. Repoint syncs get a PATCH API call with target sourceId and a validation query. Rewrite_model syncs get a translated SQL diff and a model PATCH call. Rebuild syncs (Customer Studio audiences, Journeys) get a schema mapping and full rebuild plan. Lightning schema provisioning SQL is included where needed.

**Integration with migration inventory**: `reverse_etl_sync` and `reverse_etl_destination` node types appear in the dependency graph. Effort weights: 0.5h (repoint), 2h (rewrite_model), 8h (rebuild). Phase breakdown updated to include reverse ETL between orchestration and equivalency.

### Extended lineage diagram

When `reverse_etl_audit.md` is present, `/wire:lineage-generate` adds two layers to the right of DB Objects:

| Layer | Colour | What it shows |
|---|---|---|
| Reverse ETL | Purple | Hightouch syncs; node colour = migration approach |
| Destinations | Coral | SaaS destinations (Salesforce, HubSpot, etc.) |

Node colours in the Reverse ETL layer: green = repoint, amber = rewrite_model, red = rebuild. Clicking any warehouse object node highlights the full chain from ingestion source through to SaaS destination.

## New Commands

| Command | Description |
|---|---|
| `/wire:reverse-etl-audit-generate` | Catalog Hightouch syncs, models, and destinations |
| `/wire:reverse-etl-audit-validate` | Validate reverse ETL audit completeness |
| `/wire:reverse-etl-audit-review` | Internal RA review gate |
| `/wire:reverse-etl-migration-generate` | Generate Hightouch migration runbook |
| `/wire:reverse-etl-migration-validate` | Validate migration runbook completeness |
| `/wire:reverse-etl-migration-review` | Internal RA review of migration runbook |

---

# Wire Framework v3.7.6 Release Notes

**Release date**: 2026-06-07

## Overview

Add wire-release skill and fix claude-plugin dist image paths and README

## What Changed

- `wire-release` skill: covers the full release lifecycle — bump type selection, pre-release cleanup, documentation updates, Wire Studio/VSCode updates, build, publish, and post-release verification
- `build-packages.sh`: README.md now copied to claude-plugin dist; image paths in USER_GUIDE.md and README.md rewritten from wire/docs/images/ to docs/images/ for correct resolution in the wire-plugin remote repo
- Version corrections: USER_GUIDE.md version header updated to 3.7.5; README.md heading corrected to v3.7.5



### New Techniques & Commands

- **Learn**: `wire-release` skill: covers the full release lifecycle — bump type selection, pre-release cleanup, documentation updates, Wire Studio/VSCode updates, build, publish, and post-release verification
- **Learn**: `build-packages.sh`: README.md now copied to claude-plugin dist; image paths in USER_GUIDE.md and README.md rewritten from wire/docs/images/ to docs/images/ for correct resolution in the wire-plugin remote repo
- **Learn**: Version corrections: USER_GUIDE.md version header updated to 3.7.5; README.md heading corrected to v3.7.5

---

# Wire Framework v3.7.5 Release Notes

**Release date**: 2026-06-06

## Overview

Adds a lineage visualisation step to the `platform_migration` release type. After the migration inventory is approved, `/wire:lineage-generate` produces a self-contained interactive HTML file showing the full dbt dependency graph — from raw source tables through to the physical warehouse objects each model creates. The view doubles as a client deliverable and as a planning tool for the migration strategy phase.

## What Changed

### New command: `/wire:lineage-generate`

Runs `wire/scripts/generate_lineage.py` against the dbt project and writes three files to `audit/lineage/`:

- **`lineage.html`** — interactive browser explorer, no external dependencies beyond CDN-loaded vis.js and Font Awesome
- **`lineage_nodes.csv`** — flat node catalogue for downstream analysis
- **`lineage_edges.csv`** — flat edge catalogue

Six layers are shown left-to-right, each in a distinct colour:

| Layer | Colour | What it shows |
|---|---|---|
| Ingestion | Steel blue | Raw source tables from connectors |
| Seeds | Amber | dbt seed CSV files |
| Staging | Mid blue | Staging models (`stg_*`) |
| Integration | Forest green | Integration / intermediate models |
| Warehouse | Sienna | Warehouse / mart models |
| DB Objects | Teal | Physical tables/views in the target warehouse |

The DB Objects layer is built from `config(alias='...')` in each warehouse model's SQL header — this is what the warehouse model actually creates in the target platform, not just the dbt model name.

Nodes are enriched with complexity, batch number, and platform-specific feature tags from `dbt_audit.csv` when present. Run `/wire:lineage-generate` again after a `dbt-audit-generate` refresh to pick up updated enrichment.

### Positioning: after `migration_inventory`, not after `dbt_audit`

The `lineage_view` artifact now sits after `migration_inventory` in the workflow. The inventory assigns batch numbers and finalises complexity ratings — running lineage before that would show placeholder or stale enrichment. The prerequisite for `/wire:lineage-generate` is `migration_inventory: review: approved`.

This affects the command order in `COMMANDS.md`, the artifact zone tables in both user guides, the `status_migration.md` template, and the spec's next-command pointer (now points to `/wire:migration-strategy-generate`).

---

# Wire Framework v3.7.4 Release Notes

**Release date**: 2026-06-06

## Overview

Closes a gap in the `agentic_data_stack` release type for Looker projects: the Build phase now has an explicit step for creating and updating LookML view files before the semantic layer metric build runs.

## What Changed

### New artifact: `lookml_views` (Looker only)

Three new commands sit between `canonical_models` and `semantic_layer` in the Build phase:

- **`/wire:ads_lookml-views-generate`** — reads `canonical_models_lineage.md`, scans the LookML project, and generates base view files (dimensions only, no measures) for new canonical models. Updates existing view files for renamed, removed, or added columns on modified models. Auto-skips with a status entry when `bi_tool` is not `looker`.
- **`/wire:ads_lookml-views-validate`** — runs lookml-lint, checks every canonical model has a corresponding view, verifies all `${TABLE}.<column>` references exist in the dbt schema.yml, confirms primary keys, and hard-blocks progression if any new view is not wired into an explore.
- **`/wire:ads_lookml-views-review`** — presents generated and updated view files to the Looker admin and data team for sign-off on explore coverage, naming conventions, and hidden fields before `ads_semantic-layer-generate` runs.

**Why this matters**: `ads_semantic-layer-generate` adds measure definitions to LookML view files. Without this step, there was no mechanism to create those view files for newly consolidated canonical models, leaving the semantic layer build with nothing to attach metrics to.

`lookml_project_path` is now a tracked field in the `agentic_data_stack` status template.

---

# Wire Framework v3.7.3 Release Notes

**Release date**: 2026-06-05

## Overview

One new release type: **Agentic Data Stack** — a structured six-week delivery sequence for building governed self-service analytics capabilities on top of Claude. The release type addresses the failure mode Anthropic identified in their own analytics agent build: accuracy failures are almost always governance failures (too many tables, conflicting metric definitions) rather than model failures.

## What Changed

### New release type: `agentic_data_stack`

41 new commands (`ads_` prefix) across five phases:

- **Audit** — three parallel audits (dataset, metric, query) via `/wire:ads-audit-all`
- **Design** — canonical dataset model and semantic layer specification
- **Build** — dbt refactor, semantic layer extension, `DOMAIN_REFERENCE.md` files colocated with mart models (with CI check), installable agent `SKILL.md`
- **Validation** — eval suite (min 10 Q&A pairs/domain, CI runner, accuracy thresholds) and adversarial review config — both first-class deliverables
- **Launch gate** — per-domain accuracy check (90% default); blocked domains get a fix cycle before announcement

**Key design choices:** `DOMAIN_REFERENCE.md` files live in the client's dbt repo, not Wire's engagement folder. The analytics agent is a Wire `SKILL.md` the client installs and runs after the engagement closes. The eval suite runs in CI — accuracy drift is caught before it reaches users.

---

# Wire Framework v3.7.2 Release Notes

**Release date**: 2026-06-05

## Overview

Two themes in this release:

1. **Ingestion-tool support broadens** — four new tools (RudderStack, Coupler.io, Segment, Airbyte) join Fivetran as recognised ingestion / event-tracking sources for `platform_migration` releases. Three of the four ship with MCP server entries in the plugin; Segment uses its Public API.
2. **Jira integration: a less noisy structure option.** A new `single_issue` Jira structure creates one Task per artifact (instead of one Task + three Sub-tasks) and transitions it through To Do → In Progress → In Review → Done as commands run. Useful when a sprint board would otherwise be drowning in Sub-tasks.

## What Changed

### New ingestion tools

| Tool | MCP server | Auth | Skill |
|---|---|---|---|
| RudderStack | `https://mcp.rudderstack.com/mcp` (via `mcp-remote`) | OAuth (browser) | `wire/skills/rudderstack/SKILL.md` |
| Coupler.io | `https://mcp.coupler.io/mcp/` | Personal access token from the Coupler.io app | `wire/skills/coupler-io/SKILL.md` |
| Segment | None — uses Segment Public API | Bearer token (`api.segmentapis.com` / `eu1.api.segmentapis.com`) | `wire/skills/segment/SKILL.md` |
| Airbyte | `https://mcp.airbyte.ai/mcp` (Agent MCP — OAuth) **and** `https://api.airbyte.com/v1` (deployment API — bearer) | OAuth or API key (different per surface) | `wire/skills/airbyte/SKILL.md` |

### Status-template change

The `platform_migration` status template now records `migration.ingestion_tool` alongside `source_platform`, `target_platform`, `dbt_project_path`, `orchestration_tool`, and `connectivity`. Valid values:

```yaml
migration:
  ingestion_tool: fivetran | rudderstack | coupler-io | segment | airbyte | other
```

`/wire:new` asks for this when scaffolding a platform_migration release; existing releases default to `fivetran` for backwards compatibility.

### `ingestion-audit-generate` is now tool-aware

The audit command branches on `migration.ingestion_tool` and follows the right discovery pattern per tool:

- **Fivetran (default)** — Fivetran MCP or CSV fallback (unchanged from 3.7.0)
- **RudderStack** — RudderStack MCP at `mcp.rudderstack.com/mcp` (OAuth)
- **Coupler.io** — Coupler.io MCP at `mcp.coupler.io/mcp/` (personal access token)
- **Segment** — Segment Public API (`SEGMENT_TOKEN` env var)
- **Airbyte** — Airbyte API at `api.airbyte.com/v1` (`AIRBYTE_TOKEN` env var); the Agent MCP at `mcp.airbyte.ai/mcp` is available as an alternative but designed for agent-driven SaaS data fetching rather than deployment inspection
- **Other** (Stitch, Estuary, custom) — CSV import at `audit/ingestion_sources_input.csv`

Each branch outputs the same audit shape (source / destination / schema / volume / migration approach) using the tool's own concept mapping.

### Companion plugins

For RudderStack workflows beyond MCP — CLI, Terraform, rudder-typer code generation — install the upstream [`rudderlabs/rudder-agent-skills`](https://github.com/rudderlabs/rudder-agent-skills) plugin. Wire's `rudderstack` skill covers the MCP surface; the upstream plugin covers the others.

### Segment → RudderStack migration

The most common Segment migration is to RudderStack. The new `segment` skill notes this and recommends the migration_strategy artifact capture the destination-by-destination "RudderStack equivalent" mapping. For migrations that swap CDP and warehouse at the same time, run two parallel `platform_migration` releases — one per change.

### Jira: single-issue structure option

A new `jira_structure` dimension complements the existing `jira_mode`:

| `jira_structure` | Behaviour |
|---|---|
| `subtasks` (default) | Epic per release → one Task per artifact → three Sub-tasks per artifact (generate / validate / review). Each command transitions its own Sub-task. Unchanged from v3.7.1. |
| `single_issue` | Epic per release → one Task per artifact. The single Task moves through workflow states as commands run. |

Under `single_issue` the state transitions are:

| Trigger | Task transitions to |
|---|---|
| Task created (by `/wire:utils-jira-create`) | **To Do** |
| `<artifact>-generate` completes | **In Progress** |
| `<artifact>-validate` passes | **In Review** |
| `<artifact>-validate` fails | **In Progress** (kept, with comment) |
| `<artifact>-review` approved | **Done** |
| `<artifact>-review` changes_requested | **In Progress** |

The Jira project's workflow must support those four states. `jira_create.md`'s pre-flight check verifies this before scaffolding — it inspects available transitions on an existing issue, maps flexibly (e.g. "In Review" matches "Review", "Code Review", "In QA"), and stops with clear remediation if any state is unreachable.

The choice surfaces on `/wire:new` as a three-way Jira setup question (sub-tasks per command / single issue per artifact / link to existing). Existing engagements default to `subtasks` for backwards compatibility — no migration needed for v3.7.1 projects.

**Why this exists**: under `subtasks`, an engagement with 15 artifacts creates 1 + 15 + ~45 = 61 Jira issues. On a busy sprint board that's noise. `single_issue` keeps the count at 16 (1 Epic + 15 Tasks) and uses Jira's native workflow states to surface artifact lifecycle progress instead of separate child issues.

---

# Wire Framework v3.7.1 Release Notes

**Release date**: 2026-06-05

## Overview

A patch release with one correctness fix and two additions that improve `platform_migration` engagements.

## What Changed

### Fix — `/wire:playbook-generate` no longer makes false claims about what Wire does

Previous generated playbooks ended with a bullet saying *"Wire does not run audits, does not attend workshops, does not resolve OQs, does not write Looker/dbt code, does not send emails."* Two of those five claims were wrong — Wire absolutely runs audits (via the `audit` artifacts and `/wire:utils-migration-audit-all`), and writes Looker, dbt, pipeline, and migration code (`/wire:dbt-generate`, `/wire:semantic_layer-generate`, `/wire:dashboards-generate`, `/wire:pipeline-generate`, `/wire:dbt_migration-generate`).

The spec at `wire/specs/playbook/generate.md` has been corrected. Playbook output now contains a two-paragraph "What Wire does and does not do" section that distinguishes generation (Wire writes artifacts) from decision-making (humans approve, workshop, resolve OQs, sign off).

**Action**: existing engagement playbooks contain the old wording. Re-run `/wire:playbook-generate <release>` for each active engagement to refresh.

### Addition — bundled worked examples for platform pairs

Each platform pair under `wire/platform_pairs/` now ships an `examples/` directory containing end-to-end before/after dbt model translations:

```
wire/platform_pairs/bigquery_to_snowflake/examples/
├── README.md
├── 01_unnest_to_flatten/    (before.sql + after.sql + notes.md)
├── 02_struct_to_object_construct/
├── 03_date_arithmetic/
└── 04_ml_predict_no_equivalent/

wire/platform_pairs/snowflake_to_bigquery/examples/
├── README.md
├── 01_flatten_to_unnest/
├── 02_object_construct_to_struct/
└── 03_date_arithmetic/
```

The examples are loaded by `/wire:dbt_migration-generate` as few-shot context when it translates dbt models. Each `notes.md` covers translation rationale, edge cases, dbt-config impact, and any Wire macro equivalent.

### Addition — per-engagement platform-pair override slot

`migration_strategy-generate` and `dbt_migration-generate` now read engagement-level overrides at `.wire/engagement/platform_pair_overrides/<pair>/` in addition to the canonical pair files. The override directory can contain its own `translation_guide.md` and `examples/` — engagement overrides win where they cover the same construct and supplement where they introduce new ones.

This lets teams carry forward bespoke translations from one engagement to the next at the same client without modifying the framework. The strategy artifact documents which decisions came from where under a "Translation overrides applied" section.

Documented in detail at `wire/platform_pairs/README.md` (also new in this release).

### Recommended workflow for overrides

During an engagement, capture novel translations as project-scope overrides. At engagement close, the team reviews the override directory and promotes anything reusable into the canonical guide via a PR to the framework repo. Anything genuinely client-specific stays in the override directory for the next engagement at the same client.

---

# Wire Framework v3.7.0 Release Notes

**Release date**: 2026-06-01

## Overview

3.7.0 adds the `platform_migration` release type — full lifecycle migration of a data platform from one warehouse stack to another. The initial target is BigQuery ↔ Snowflake migrations, with the spec structure designed to extend to Databricks and other platforms.

## What Changed

The release adds 14 new artifacts and 42 commands covering the migration lifecycle: source-platform audits (ingestion, db objects, security, dbt, orchestration) → migration inventory and strategy → target setup → parallel ingestion → batched dbt translation → orchestration migration → equivalency validation loop → cutover → final migration report.

### New release type

- `release_type: platform_migration` — selectable from `/wire:new`'s release-type picker. Sets up the 14-artifact scope in `status.md` and the migration-specific folder layout.

### Audit phase (parallel)

- `ingestion-audit-generate / validate / review` — Fivetran (and equivalents) connector inventory and cost analysis.
- `db_object-audit-generate / validate / review` — tables, views, procedures, UDFs, permissions inventory on the source platform.
- `security-audit-generate / validate / review` — IAM, masking, row-level security, audit logging.
- `dbt-audit-generate / validate / review` — existing dbt project inventory, dialect-specific patterns to translate, test coverage.
- `orchestration-audit-generate / validate / review` — Airflow / dbt Cloud / Dagster / Cloud Composer current-state inventory.

### Parallel-audit utility

- `/wire:utils-migration-audit-all <release>` — fans out the five audits as parallel subagents. Reduces total audit wall-clock from sequential hours to roughly the slowest individual audit.

### Planning artifacts

- `migration_inventory-generate / validate / review` — consolidated inventory across all audits.
- `migration_strategy-generate / validate / review` — sequencing, parallel-run window, cutover plan, rollback strategy.
- `target_setup-generate / validate / review` — target warehouse provisioning plan (IaC or manual).

### Migration artifacts

- `ingestion_migration-generate / validate / review` — repointing or rebuilding ingestion into the target platform.
- `dbt_migration-generate / validate / review` — batched dbt model translation (dialect, type system, macros).
- `orchestration_migration-generate / validate / review` — orchestration tool migration (or repointing to the new warehouse).

### Equivalency loop

- `equivalency-validate / investigate / fix` — automated row-count, schema, and value-level equivalency checks between source and target, with structured investigation and fix sub-actions until the parallel-run window closes.

### Cutover and report

- `cutover-generate / validate / review` — final go-live runbook with rollback gates.
- `migration_report-generate / validate / review` — post-migration summary, accepted deltas, lessons, decommissioning recommendations.

### Autopilot support

Autopilot recognises `platform_migration` releases and sequences the artifacts correctly. Safety gates are in place on `target_setup`, `ingestion_migration`, `orchestration_migration`, and `cutover` — autopilot will pause for human confirmation on each.

### Test suite

Structural and feature-detection tests for the migration release type ship under `wire/tests/platform_migration/`. Run with `bash wire/tests/platform_migration/validate_specs.sh`.

### Plugin / extension

The Claude Code plugin and Gemini CLI extension manifests are both at 3.7.0. After updating, run `/reload-plugins` in Claude Code to pick up the new commands.

---

# Wire Framework v3.6.4 Release Notes

**Release date**: 2026-05-26

## Overview

3.6.4

## What Changed

- Five finance skills added; user guide renamed to WIRE_WORK_USER_GUIDE.md
- New skill: cowork-monthly-management-accounts (Xero P&L, balance sheet, Google Doc, Slack DM to Lewis)
- New skill: cowork-weekly-cash-debtors-pack (aged debtors, top-3 chase, draft emails, Slack DM)
- New skill: cowork-quarterly-revenue-concentration (concentration ratios, YoY movement, risk assessment)
- New skill: cowork-project-profitability-reconciliation (Harvest vs Xero effective day rate, underwater flag)
- New skill: cowork-vat-return-prep-checklist (16-item UK VAT pre-submission checklist)
- Renamed CLAUDE_COWORK_USER_GUIDE.md to WIRE_WORK_USER_GUIDE.md



### New Techniques & Commands

- **Learn**: Five finance skills added; user guide renamed to WIRE_WORK_USER_GUIDE.md
- **Learn**: New skill: cowork-monthly-management-accounts (Xero P&L, balance sheet, Google Doc, Slack DM to Lewis)
- **Learn**: New skill: cowork-weekly-cash-debtors-pack (aged debtors, top-3 chase, draft emails, Slack DM)
- **Learn**: New skill: cowork-quarterly-revenue-concentration (concentration ratios, YoY movement, risk assessment)
- **Learn**: New skill: cowork-project-profitability-reconciliation (Harvest vs Xero effective day rate, underwater flag)
- **Learn**: New skill: cowork-vat-return-prep-checklist (16-item UK VAT pre-submission checklist)
- **Learn**: Renamed CLAUDE_COWORK_USER_GUIDE.md to WIRE_WORK_USER_GUIDE.md

---

# Wire Framework v3.6.3 Release Notes

**Release date**: 2026-05-25

## Overview

3.6.3

## What Changed

- Pipeline skill workspace-free; three new Cowork skills (daily briefing, delivery status, AI adoption)
- Pipeline deck mode generates HTML inline — no Python runtime or workspace required for text or deck output
- New skill: cowork-daily-briefing — context-aware daily briefing from Calendar, Gmail, Slack, Fathom, Drive
- New skill: cowork-client-delivery-status-report — SOW-anchored delivery status with Fathom, Slack, Atlassian
- New skill: cowork-weekly-ai-adoption-analysis — team AI adoption tracking with React dashboard



### New Techniques & Commands

- **Learn**: Pipeline skill workspace-free; three new Cowork skills (daily briefing, delivery status, AI adoption)
- **Learn**: Pipeline deck mode generates HTML inline — no Python runtime or workspace required for text or deck output
- **Learn**: New skill: cowork-daily-briefing — context-aware daily briefing from Calendar, Gmail, Slack, Fathom, Drive
- **Learn**: New skill: cowork-client-delivery-status-report — SOW-anchored delivery status with Fathom, Slack, Atlassian
- **Learn**: New skill: cowork-weekly-ai-adoption-analysis — team AI adoption tracking with React dashboard

---

# Wire Framework v3.6.2 Release Notes

**Release date**: 2026-05-25

## Overview

Wire Work plugin launch: Orca/Tuna/Shark/Minnow ICP assessment, call list prioritisation, weekly pipeline deck, deal qualification improvements, and user guide updates

## What Changed

- Wire Work plugin (wirework) — new separate Cowork plugin with 9 skills for sales, CEO, and engagement delivery
- cowork-rfp-assessment: replaced 6-dimension weighted scorecard with Orca/Tuna/Shark/Minnow ICP segmentation framework
- cowork-call-list: new skill for ranked daily call lists with talking points, calendar blocks, and follow-up drafts
- cowork-hubspot-sales-pipeline-weekly: new branded 5-slide pipeline deck replacing cowork-pipeline-report
- CLAUDE_COWORK_USER_GUIDE.md: new user guide covering all 9 Cowork skills
- Deal qualification user guide section: repositioned relative to RFP Assessment in the workflow



### New Techniques & Commands

- **Learn**: Wire Work plugin (wirework) — new separate Cowork plugin with 9 skills for sales, CEO, and engagement delivery
- **Learn**: cowork-rfp-assessment: replaced 6-dimension weighted scorecard with Orca/Tuna/Shark/Minnow ICP segmentation framework
- **Learn**: cowork-call-list: new skill for ranked daily call lists with talking points, calendar blocks, and follow-up drafts
- **Learn**: cowork-hubspot-sales-pipeline-weekly: new branded 5-slide pipeline deck replacing cowork-pipeline-report
- **Learn**: CLAUDE_COWORK_USER_GUIDE.md: new user guide covering all 9 Cowork skills
- **Learn**: Deal qualification user guide section: repositioned relative to RFP Assessment in the workflow

---

# Wire Framework v3.6.1 Release Notes

**Release date**: 2026-05-24

## Overview

Add 8 Cowork-native skills for sales, pipeline, and client intelligence (v3.6.0)

## What Changed

- New skill: cowork-rfp-assessment — ICP scoring and go/no-go for incoming RFPs with HubSpot deal lookup
- New skill: cowork-deal-qualify — MEDDIC qualification on HubSpot deals with Fathom transcript signals
- New skill: cowork-pipeline-report — CEO pipeline report with weighted forecast, Xero, Harvest, and Fathom
- Updated skill: cowork-client-meeting-intelligence — corrected Gmail tool names, fixed date handling
- Updated skill: cowork-sales-enquiry-follow-up-email — corrected tool names, preserved voice rules
- Updated skill: cowork-psf-sow-validator — native PDF reading, Google Drive optional
- Updated skill: cowork-google-doc-proposal-generator — pure MCP workflow, no Python scripts
- Updated skill: cowork-stakeholder-influence-network — corrected Looker tool, Cowork file output
- CLAUDE.md: added Cowork Skills section with connector conventions
- Plugin version bumped from 3.5.13 to 3.6.0



### New Techniques & Commands

- **Learn**: New skill: cowork-rfp-assessment — ICP scoring and go/no-go for incoming RFPs with HubSpot deal lookup
- **Learn**: New skill: cowork-deal-qualify — MEDDIC qualification on HubSpot deals with Fathom transcript signals
- **Learn**: New skill: cowork-pipeline-report — CEO pipeline report with weighted forecast, Xero, Harvest, and Fathom
- **Learn**: Updated skill: cowork-client-meeting-intelligence — corrected Gmail tool names, fixed date handling
- **Learn**: Updated skill: cowork-sales-enquiry-follow-up-email — corrected tool names, preserved voice rules
- **Learn**: Updated skill: cowork-psf-sow-validator — native PDF reading, Google Drive optional
- **Learn**: Updated skill: cowork-google-doc-proposal-generator — pure MCP workflow, no Python scripts
- **Learn**: Updated skill: cowork-stakeholder-influence-network — corrected Looker tool, Cowork file output
- **Learn**: CLAUDE.md: added Cowork Skills section with connector conventions
- **Learn**: Plugin version bumped from 3.5.13 to 3.6.0

---

# Wire Framework v3.5.13 Release Notes

**Release date**: 2026-05-23

## Overview

Add /wire:session-plan handoff offer at end of /wire:start navigational mode

## What Changed

- /wire:start now asks Y/N to hand off to /wire:session-plan after showing the navigation summary
- Handoff skipped in onboarding, explanation, and lightweight session-start modes



### New Techniques & Commands

- **Learn**: /wire:start now asks Y/N to hand off to /wire:session-plan after showing the navigation summary
- **Learn**: Handoff skipped in onboarding, explanation, and lightweight session-start modes

---

# Wire Framework v3.5.12 Release Notes

**Release date**: 2026-05-23

## Overview

Update USER_GUIDE to reflect /wire:start co-pilot functionality

## What Changed

- USER_GUIDE session lifecycle section updated with /wire:start co-pilot description
- USER_GUIDE install confirmation line updated with full /wire:start capability description
- USER_GUIDE status.md section updated to describe /wire:start navigation and optional arguments



### New Techniques & Commands

- **Learn**: USER_GUIDE session lifecycle section updated with /wire:start co-pilot description
- **Learn**: USER_GUIDE install confirmation line updated with full /wire:start capability description
- **Learn**: USER_GUIDE status.md section updated to describe /wire:start navigation and optional arguments

---

# Wire Framework v3.5.11 Release Notes

**Release date**: 2026-05-23

## Overview

Merge /wire:guide into /wire:start — one session entry point instead of two

## What Changed

- /wire:guide merged into /wire:start (plugin health check, onboarding, navigation, intent resolution)
- /wire:guide command and spec removed — reduces confusion about which entry point to use
- All internal references updated: help.md, wire-session-check.sh, CLAUDE.md, COMMANDS array



### New Techniques & Commands

- **Learn**: /wire:guide merged into /wire:start (plugin health check, onboarding, navigation, intent resolution)
- **Learn**: /wire:guide command and spec removed — reduces confusion about which entry point to use
- **Learn**: All internal references updated: help.md, wire-session-check.sh, CLAUDE.md, COMMANDS array

---

# Wire Framework v3.5.9 Release Notes

**Release date**: 2026-05-22

## Overview

Wire guide co-pilot, session-start hooks, status line, and custom command namespace fixes

## What Changed

- /wire:guide command with plugin health check (4 cases: not installed, outdated, current, legacy .dp/ structure), new-user onboarding, and navigational mode
- Session-start UserPromptSubmit hook outputs Wire project status on first prompt per repo per hour; fires from .claude/hooks/wire-session-check.sh installed by /wire:new
- Plugin CLAUDE.md first-message instruction covers users who have Wire installed but have not yet run /wire:new
- Wire-aware status line showing [Wire vX.Y.Z], active release, and context usage percentage
- Auto-approve Segment telemetry bash calls via permissions entry in claude-settings.json project template
- TEMPLATES directory now included in plugin distribution package (was silently excluded from the build)
- Fix: /wire:guide was missing from the COMMANDS array and therefore not generated as a slash command
- Fix: /wire:custom-define now writes command wrappers to .claude/commands/wire/ so they appear as /wire:<name> not /<name>
- /wire:migrate Case D: detect custom command wrappers in the wrong location and move them to .claude/commands/wire/ using git mv



### New Techniques & Commands

- **Learn**: /wire:guide command with plugin health check (4 cases: not installed, outdated, current, legacy .dp/ structure), new-user onboarding, and navigational mode
- **Learn**: Session-start UserPromptSubmit hook outputs Wire project status on first prompt per repo per hour; fires from .claude/hooks/wire-session-check.sh installed by /wire:new
- **Learn**: Plugin CLAUDE.md first-message instruction covers users who have Wire installed but have not yet run /wire:new
- **Learn**: Wire-aware status line showing [Wire vX.Y.Z], active release, and context usage percentage
- **Learn**: Auto-approve Segment telemetry bash calls via permissions entry in claude-settings.json project template
- **Learn**: TEMPLATES directory now included in plugin distribution package (was silently excluded from the build)
- **Learn**: Fix: /wire:guide was missing from the COMMANDS array and therefore not generated as a slash command
- **Learn**: Fix: /wire:custom-define now writes command wrappers to .claude/commands/wire/ so they appear as /wire:<name> not /<name>
- **Learn**: /wire:migrate Case D: detect custom command wrappers in the wrong location and move them to .claude/commands/wire/ using git mv

---

# Wire Framework v3.5.8 Release Notes

**Release date**: 2026-05-22

## Overview

Add Case D to /wire:migrate — detect and fix custom commands missing the /wire: prefix

## What Changed

- Detect Wire custom command wrappers in .claude/commands/ that were written without the wire/ subdirectory namespace (pre-v3.5.7 behaviour)
- Move misplaced wrappers to .claude/commands/wire/ using git mv so they gain the /wire: prefix
- Chain Case D automatically after any other migrate case, and run standalone on already-migrated repos



### New Techniques & Commands

- **Learn**: Detect Wire custom command wrappers in .claude/commands/ that were written without the wire/ subdirectory namespace (pre-v3.5.7 behaviour)
- **Learn**: Move misplaced wrappers to .claude/commands/wire/ using git mv so they gain the /wire: prefix
- **Learn**: Chain Case D automatically after any other migrate case, and run standalone on already-migrated repos

---

# Wire Framework v3.5.7 Release Notes

**Release date**: 2026-05-22

## Overview

Fix custom release type commands missing /wire: prefix

## What Changed

- Write custom command wrappers to .claude/commands/wire/ subdirectory so they get the wire: namespace prefix
- Update proposal table and activation notice to show /wire: prefix on custom commands



### New Techniques & Commands

- **Learn**: Write custom command wrappers to .claude/commands/wire/ subdirectory so they get the wire: namespace prefix
- **Learn**: Update proposal table and activation notice to show /wire: prefix on custom commands

---

# Wire Framework v3.5.6 Release Notes

**Release date**: 2026-05-22

## Overview

Fix /wire:guide missing from command registry and session-start message not firing

## What Changed

- Add guide to COMMANDS array in build-packages.sh so /wire:guide is generated as a slash command



### New Techniques & Commands

- **Learn**: Add guide to COMMANDS array in build-packages.sh so /wire:guide is generated as a slash command

---

# Wire Framework v3.5.5 Release Notes

**Release date**: 2026-05-22

## Overview

Add /wire:guide co-pilot, session-start hooks, Wire status line, and auto-approve telemetry

## What Changed

- /wire:guide command — interactive co-pilot spec covering plugin health check, new-user onboarding, and navigational mode
- Session-start UserPromptSubmit hook outputs Wire project status on first prompt per repo per hour
- Plugin CLAUDE.md first-message instruction covers users without a Wire project yet
- Wire-aware status line showing plugin version, active release, and context usage percentage
- Auto-approve Segment telemetry calls via permissions in claude-settings.json template
- TEMPLATES now included in plugin distribution package



### New Techniques & Commands

- **Learn**: /wire:guide command — interactive co-pilot spec covering plugin health check, new-user onboarding, and navigational mode
- **Learn**: Session-start UserPromptSubmit hook outputs Wire project status on first prompt per repo per hour
- **Learn**: Plugin CLAUDE.md first-message instruction covers users without a Wire project yet
- **Learn**: Wire-aware status line showing plugin version, active release, and context usage percentage
- **Learn**: Auto-approve Segment telemetry calls via permissions in claude-settings.json template
- **Learn**: TEMPLATES now included in plugin distribution package

---

# Wire Framework v3.5.4 Release Notes

**Release date**: 2026-05-17

## Overview

Add Custom release type — Wire analyses SoW/project docs and generates bespoke project-scoped specs for engagements not covered by standard release types

## What Changed

- Add /wire:utils-doc-analyze for deliverable extraction from PDFs and project documents
- Add /wire:custom-release-define command with deliverable mapping, workflow-mismatch detection, and timeline seeding
- Add /wire:custom-feature-request for raising framework extension proposals



### New Techniques & Commands

- **Learn**: Add /wire:utils-doc-analyze for deliverable extraction from PDFs and project documents
- **Learn**: Add /wire:custom-release-define command with deliverable mapping, workflow-mismatch detection, and timeline seeding
- **Learn**: Add /wire:custom-feature-request for raising framework extension proposals

---

# Wire Framework v3.5.3 Release Notes

**Release date**: 2026-05-16

## Overview

Add /wire:adopt, delivery_forecast, client_context utilities, and release automation script

## What Changed

- /wire:adopt — onboard any in-flight project into Wire regardless of prior usage; assesses repo, Slack, HubSpot, Harvest, Jira, Confluence, and Fathom; generates a four-state adoption playbook and per-release delivery forecast
- utils/client_context — reusable multi-source external data gathering (Slack, HubSpot, Harvest, Jira, Confluence, Fathom) returned as a structured ClientContext object; callable by any Wire command
- utils/delivery_forecast — calculates % delivered per release via weighted checklist/Jira/Harvest composite, projects ETA using Fathom sprint velocity or burn-rate extrapolation, and compares against HubSpot contractual dates
- wire/scripts/release.sh — release automation script: bumps patch version, updates all changelogs and READMEs, pushes wiki, builds packages, pushes to wire-plugin and wire-extension repos, and raises a PR



### New Techniques & Commands

- **Learn**: /wire:adopt — onboard any in-flight project into Wire regardless of prior usage; assesses repo, Slack, HubSpot, Harvest, Jira, Confluence, and Fathom; generates a four-state adoption playbook and per-release delivery forecast
- **Learn**: utils/client_context — reusable multi-source external data gathering (Slack, HubSpot, Harvest, Jira, Confluence, Fathom) returned as a structured ClientContext object; callable by any Wire command
- **Learn**: utils/delivery_forecast — calculates % delivered per release via weighted checklist/Jira/Harvest composite, projects ETA using Fathom sprint velocity or burn-rate extrapolation, and compares against HubSpot contractual dates
- **Learn**: wire/scripts/release.sh — release automation script: bumps patch version, updates all changelogs and READMEs, pushes wiki, builds packages, pushes to wire-plugin and wire-extension repos, and raises a PR

---

# Wire Framework v3.5.2 Release Notes

**Released:** 2026-05-14
**Plugin version:** 3.5.2
**Commands:** 142

---

## What's New in v3.5.2

### `/wire:playbook-generate` — BPMN delivery playbook for any release

New planning utility command that generates a step-by-step delivery playbook for any Wire release. The output has two parts: a `flowchart TD` BPMN-style Mermaid diagram followed by a narrative step-by-step guide.

The Mermaid diagram uses BPMN element conventions (`([])` start/end events, `{}` exclusive gateways, `{{}}` parallel gateways, `[]` tasks), classDef colouring for Wire commands / offline work / decisions / gateways / events, one subgraph per phase, decision gates for blocker OQs with chase-and-retry loops, and rework loops on every generate→validate→review cycle.

Ideal run point: after the first scope-setting artifact is complete (`engagement_brief` for `sop_discovery`, `problem_definition` for `discovery`, `requirements` for all delivery types). Can run immediately after `/wire:new` for a template-level playbook.

Output: `.wire/releases/<release>/planning/<release_name>_playbook.md`. Does not create a tracked artifact in `status.md`. Syncs to Confluence as a child page if `confluence_page_id` is configured.

---

## What's New in v3.5.1

### Backwards-compatible rename revert: `shape_up_discovery` → `discovery`

The `release_type` for the Shape Up discovery flow reverts to `discovery` — the value used in all pre-v3.5.0 engagements. The v3.5.0 rename to `shape_up_discovery` broke existing engagement repos and is reversed here.

No command names change. `/wire:migrate` Case C now normalises any `shape_up_discovery` identifiers back to `discovery` for engagements that ran on v3.5.0 briefly.

---

## What's New in v3.5.0

### `sop_discovery` release type — RA Canonical (SOP) discovery workflow

A second discovery release type for engagements where the problem cannot yet be shaped — wide-ranging structured discovery leading to a go/no-go decision on a programme of work. Models the [Canonical Discovery Playbook (RA Standard)](https://rittmananalytics.atlassian.net/wiki/spaces/RA/pages/3436642306).

The canonical exit deliverable is the sponsor-facing **Findings Playback slide deck**. The playback meeting is the Wire review gate — the release is `approved` only when the 7-item Sponsor Validation Checklist (Maturity pin, Hierarchy diagnosis, PPT diagnosis, Vision Statement, Solution Initiatives, preferred Delivery Option, conflicts resolved) is all-true.

**21 new commands** across 7 artifacts:

| Artifact | Commands | Notes |
|---|---|---|
| Engagement brief | `engagement-brief-{generate,validate,review}` | 2-page internal RA scoping doc |
| Stakeholder map | `stakeholder-map-{generate,validate,review}` | P0/P1/P2 priority + booking owners |
| Stakeholder interview | `stakeholder-interview-{generate,validate,review}` | **Repeatable per stakeholder**; mandatory four-tag rule enforced mechanically |
| Requirements matrix | `requirements-matrix-{generate,validate,review}` | Consolidates tagged themes from every interview |
| Discovery analyses | `discovery-analyses-{generate,validate,review}` | The three analyses: Hierarchy + PPT + Maturity Curve |
| Findings playback | `findings-playback-{generate,validate,review}` | **The sponsor playback gate.** Generate populates the bundled Claude Design HTML deck (91 placeholders). Review captures the Sponsor Validation Checklist from the Fathom recording. |
| Delivery roadmap | `delivery-roadmap-{generate,validate,review}` | Build / Pair / Coach options |

The kick-off uses the existing `/wire:kickoff-*` commands (now release-type aware).

**Mandatory four-tag rule**: every theme bullet on every stakeholder interview write-up carries one tag from each of four closed sets — `#<domain> #<type> #<hierarchy> #<ppt>`. `stakeholder-interview-validate` enforces this with a regex/parser check, not LLM judgement. The three analyses cannot run without it.

### `/wire:kickoff` is now release-type aware

Branches on `release_type` to pull from the right upstream artefacts:

- `discovery` → enriches from `problem_definition` / `pitch` / `sprint_plan`
- `sop_discovery` → enriches from `engagement_brief` / `stakeholder_map`

The SOP kick-off lands every stakeholder knowing whether they'll be interviewed, by whom, in which week, and what the exit deliverable will be.

### Sponsor validation gate on `/wire:release-spawn`

For `sop_discovery` releases, `/wire:release-spawn` refuses to chain into a delivery release until `sponsor_validation.playback_held == true` AND every Sponsor Validation Checklist item is `true`. The canonical playbook explicitly calls out the catastrophic recovery cost of skipping this — Wire now enforces it.

### Bundled deck template

`wire/decks/findings_playback/` is a Claude Design HTML handoff bundled with Wire (mirrors `wire/decks/kickoff/`). 91 inline `<<placeholder>>` spans and one `data-cond` flag. `findings-playback-generate` populates it from `discovery_analyses.md` and `requirements_matrix.md`.

### Documentation

- `USER_GUIDE.md` gains a "Discovery workflow (SOP / Canonical)" section walking through the full command sequence.
- `CHANGELOG.md`, this `RELEASE_NOTES.md`, root `README.md`, and `wire/README.md` all updated.

---

## What's New in v3.4.21

### Plugin install — `/reload-plugins` is the correct activation step

User-facing install docs across the framework now show `/reload-plugins` as the activation step after `/plugin install`, replacing the previous "Restart Claude Code" guidance. The reload command picks up the install in the current session and is the documented activation step in the Claude Code docs.

Updated: `README.md`, `USER_GUIDE.md` (Step 1 + §19), `CLAUDE.md` (repo-level), `wire/README.md`, the developer quick-reference, and the VS Code extension guide.

### dbt development skill — conventions refreshed

`wire/skills/dbt-development/` now reflects the current RA dbt coding conventions:

- Entity-group folder layout (`stg_core/`, `int_core/`, `wh_core/`, …) with `<layer>_<group>__<entity>.sql` file naming
- `_xa` cross-attribute / bridge model type alongside `_dim` and `_fact`
- New field-naming rules: `_was_` boolean prefix, `_amount` suffix for revenue, middle-position timezone for non-UTC timestamps (`created_cet_ts`), `_dt` for dates
- Mandatory use of `{{ dbt.type_*() }}` casting macros
- New field ordering — keys → attributes → indexes/ranks → metrics → booleans → temporal — with Jinja comment markers in staging models
- PK/FK macro updated to `dbt_utils.generate_surrogate_key`
- Schema YAML is auto-generated; do not hand-edit `schema.yml`
- Warehouse-layer columns must be documented; field descriptions live in `models/field_descriptions.md` doc blocks
- New canonical staging and warehouse model examples in `examples/`

### LookML content authoring skill — layered architecture documented

`wire/skills/lookml-content-authoring/SKILL.md` gains a major new section: **RA Layered LookML Architecture**, covering the canonical five-layer refinement pattern (`base/` → `staging/` → `aggregate/` → `int/` → `model/`), file-naming conventions (`.layer.lkml`, `.explore.lkml`), refinement worked example, `include:` ordering, and a quick-reference table mapping common tasks to the right layer.

The previous flat project structure is preserved as a "Legacy Project Structure (non-layered)" reference for older projects.

---

# Wire Framework v3.4.18 Release Notes

**Released:** 2026-05-05
**Plugin version:** 3.4.18
**Commands:** 119

---

## What's New in v3.4.18

### Wire Framework VS Code Extension — Now on the Marketplace

The Wire Framework VS Code extension is now available as a one-click install from the VS Code Extensions marketplace. Search for **Wire Framework** by Rittman Analytics and click **Install** — no manual VSIX download required.

After installation the **W** icon appears in the activity bar. For new projects a **Start a new Wire engagement** prompt is shown; click it or run `/wire:new` in Claude Code to scaffold the `.wire/` folder and create the first release.

Full step-by-step install documentation (with screenshots) has been added to:
- `wire-vscode/resources/WIRE_VSCODE_GUIDE.md` — new Section 1: Installing the VS Code Extension
- `USER_GUIDE.md` — Section 19: Wire Framework VS Code Extension, new "Installing the Extension" subsection

---

# Wire Framework v3.4.17 Release Notes

**Released:** 2026-05-04
**Plugin version:** 3.4.17
**Commands:** 119

---

## What's New in v3.4.17

### Fivetran Pipeline Integration

v3.4.17 makes `/wire:pipeline-generate`, `/wire:pipeline-validate`, and `/wire:pipeline-review` tool-aware. The pipeline design step now asks you to choose a replication tool — Fivetran, dlt, Airbyte, or custom — and that choice gates all downstream pipeline commands via a thin router pattern. Adding support for a new tool in future means adding a new sub-spec folder, with no changes to the router or any other part of the framework.

#### Pipeline tool selection in design

`/wire:pipeline_design-generate` now includes **Design Decision PD-1: Pipeline Replication Tool** — a comparison table of Fivetran, dlt, Airbyte, and custom approaches covering cost model, connector coverage, infrastructure footprint, and manageability. The chosen tool is written to `status.md` as `pipeline_tool` immediately, before any implementation work begins.

When Fivetran is the candidate tool, the design step calls the Fivetran MCP to verify the connector exists and retrieve its required config fields — so the implementation step is never blocked by missing credentials discovered late.

#### Fivetran implementation

| Command | What it does |
|---------|-------------|
| `/wire:pipeline-generate` | Creates Fivetran connections per the pipeline design; skips existing connections (idempotent); configures table/column selection and sync frequency via Fivetran MCP; writes `pipeline_connections.md` |
| `/wire:pipeline-validate` | Checks each connection: setup state, last sync result, table selection, PII column hashing, sync frequency, pause state; destination health check; PASS/FAIL report |
| `/wire:pipeline-review` | Fetches live connection state from Fivetran MCP; presents dashboard URLs, enabled tables, and outstanding issues; stakeholder sign-off |

#### Pipeline health in orchestration and deployment

- **`/wire:orchestration-generate`** — checks pipeline connection health at the start of Step 1 and warns if any connections are unhealthy
- **`/wire:deployment-validate`** — pipeline connection health is now a Critical pre-flight check; unhealthy connections block deployment approval

#### dlt and Airbyte stubs

Stub sub-specs for dlt and Airbyte are included under `wire/specs/development/pipeline/dlt/` and `wire/specs/development/pipeline/airbyte/`. Both are marked "Not yet implemented" — the router is already wired up so filling them in requires only new spec content, no structural changes.

---

# Wire Framework v3.4.10 Release Notes

**Released:** 2026-04-29
**Plugin version:** 3.4.10
**Commands:** 119

---

## What's New in v3.4.10

### Kickoff Deck

v3.4.10 adds three new engagement-level commands for generating a client kick-off presentation from the Statement of Work. The deck can be run immediately after `/wire:new` — before any discovery or delivery work begins.

| Command | Purpose |
|---------|---------|
| `/wire:kickoff-generate [release-folder]` | Build deck from SoW; optionally enrich with discovery artifacts |
| `/wire:kickoff-validate [release-folder]` | Validate JSON structure and content completeness |
| `/wire:kickoff-review [release-folder]` | Internal review; on approval, PDF export via headless Chrome |

**Discovery sprint mode**: when engagement type is `discovery`, the deck sets `engagementType: "Discovery"` automatically, switching slide wording to frame the kickoff as a discovery sprint opening rather than a delivery kick-off. No configuration needed.

**Re-run safe**: the generate command merges new content with existing manual edits on re-run — fields like `titlePhoto`, `accentColor`, and `presenters` are preserved unless a newer generated value is available.

**Template**: `wire/decks/kickoff/Project Kickoff.html` — blank EDITMODE block, Google Sans via CDN, no local font files, no hero video. All assets committed under `wire/decks/kickoff/` in the Wire repo.

---

# Wire Framework v3.4.9 Release Notes

**Released:** 2026-04-29
**Plugin version:** 3.4.9
**Commands:** 114

---

## What's New in v3.4.9

### Agentic Commerce Release Type

v3.4.9 introduces the **Agentic Commerce** release type (`project_type: agentic_commerce`) — a new delivery mode for building AI-powered ecommerce storefronts. Select it when running `/wire:new`.

The release type covers the full lifecycle from a blank Lovable project through to a GitHub-synced storefront with AI features layered on top via Claude Code. It adds **27 new commands** across 9 feature areas, all namespaced `/wire:ac_*`.

#### Architecture

```
Lovable Chat Interface
  → React 18 + Vite + Tailwind + TypeScript scaffold
  → Shopify Storefront API integration
  → Zustand cart state management
  → Supabase (Lovable Cloud) backend
  → GitHub bidirectional sync
      → Clone locally
      → Claude Code develops agentic features against the repo
```

#### Feature Commands

| Feature | Commands | What it builds |
|---------|----------|----------------|
| Base storefront | `/wire:ac_storefront-generate/validate/review` | Lovable scaffold + Shopify Storefront API + GitHub sync |
| Semantic search | `/wire:ac_semantic_search-generate/validate/review` | AI product search (Vertex AI / Algolia / pgvector) |
| Conversational assistant | `/wire:ac_conversational_assistant-generate/validate/review` | Multi-turn shopping assistant |
| Virtual try-on | `/wire:ac_virtual_tryon-generate/validate/review` | Photo upload + AI image generation |
| Visual similarity | `/wire:ac_visual_similarity-generate/validate/review` | "Find similar" via multimodal AI |
| LLM tools | `/wire:ac_llm_tools-generate/validate/review` | LLM with autonomous tool calling |
| Personalisation | `/wire:ac_personalisation-generate/validate/review` | User profiles + event tracking |
| UCP server | `/wire:ac_ucp_server-generate/validate/review` | Universal Commerce Protocol + Stripe |
| Demo orchestration | `/wire:ac_demo_orchestration-generate/validate/review` | Automated demo flows with personas |

**Dependency order**: `ac_storefront` must be approved before all other `ac_*` features. Features can otherwise be developed in parallel.

#### Prerequisites

- Active Lovable account with a new project created
- Shopify store with Storefront API access token (Headless channel)
- GitHub account with Lovable GitHub App authorised
- Supabase project enabled in Lovable (Lovable Cloud)
- GCP project with Vertex AI Retail API and BigQuery APIs enabled
- Stripe account (for `ac_ucp_server` only)

See `wire/docs/agentic_commerce/00a-prerequisites-and-worked-examples.md` for a complete service-by-service setup guide including account creation, API key configuration, and environment variable mapping.

---

# Wire Framework v3.4.3 Release Notes

**Released:** 2026-03-27
**Plugin version:** 3.4.3
**Commands:** 82

---

## What's New in v3.4.3

### `/wire:migrate` — Near-Wire Repo Migration (Case B)

`/wire:migrate` now handles a second migration path for engagement repos that evolved organically alongside the Wire framework — repos with `releases/`, `context/`, and `artifacts/` at the root but no `.wire/` directory.

**Before (near-wire root-level layout):**
```
releases/
  01-discovery/
    brief.md
    plan.md
    status.md           ← deliverable table format (D01, D02, …)
    deliverables/
context/
  engagement.md
  stakeholders.md
  decisions.md
  references/
    sow.pdf
artifacts/
  meetings/
    processed/          ← meeting transcripts
  notion/
  slack/
```

**After (Wire v3.4+ layout):**
```
.wire/
  engagement/
    context.md          ← translated from context/engagement.md
    stakeholders.md
    decisions.md
    glossary.md
    references/         ← SOW, contracts, requirements specs
    calls/              ← meeting transcripts (from artifacts/meetings/)
    org/
  releases/
    01-discovery/
      status.md         ← wire YAML frontmatter; original deliverable table preserved
      deliverables/
      brief.md
      plan.md
  research/
    sessions/
artifacts/              ← non-meeting reference materials stay at root
  notion/
  slack/
```

The command runs the migration on a **new git branch** (`wire/migrate-YYYYMMDD`) and automatically opens a **PR** with a full change log and review checklist — so nothing is merged until the team has reviewed it.

**Status mapping**: existing deliverable statuses are translated to wire artifact states:

| Old status | generate | validate | review |
|-----------|----------|----------|--------|
| `--` | not_started | not_started | not_started |
| `draft` | complete | not_started | not_started |
| `review` | complete | complete | in_progress |
| `approved` | complete | complete | complete |

The original deliverable table and session history are preserved verbatim in the body of the reformatted `status.md`.

---

## Previous Release Notes (v3.4.0)

# Wire Framework v3.4.0 Release Notes

**Released:** 2026-03-24
**Plugin version:** 3.4.0
**Commands:** 82

---

## What's New

### Engagement Planning Model

v3.4.0 restructures the `.wire/` directory to distinguish between engagement-wide context and individual delivery releases.

**Before (pre-v3.4.0):**
```
.wire/
  20260202_barton_peveril_live_pastoral/
    status.md
    artifacts/
  20260310_acme_marketing_analytics/
    status.md
    artifacts/
```

**After (v3.4.0):**
```
.wire/
  engagement/
    context.md          ← engagement objectives, stakeholders, architecture
    sow.md              ← statement of work
    calls/              ← meeting notes and transcripts
    org/                ← org charts
  releases/
    01-barton-peveril-live-pastoral/
      status.md
    02-acme-marketing-analytics/
      status.md
  research/
    sessions/           ← persisted research findings (auto-populated)
```

The `engagement/` folder is populated automatically by `/wire:new`. Existing engagements can be migrated with `/wire:migrate`.

---

### Discovery Release Type (Shape Up Planning)

A new `discovery` release type guides consultants through the pre-delivery scoping phase using the Shape Up methodology:

```
Problem Definition → Pitch → Release Brief → Sprint Plan → Spawn delivery releases
```

**12 new commands:**

| Command | Purpose |
|---------|---------|
| `/wire:problem-definition-generate` | Structure the problem, desired outcome, and boundaries |
| `/wire:problem-definition-validate` | Check completeness: problem, outcome, appetite |
| `/wire:problem-definition-review` | Stakeholder alignment on problem framing |
| `/wire:pitch-generate` | Write the 10-section Shape Up pitch |
| `/wire:pitch-validate` | Validate pitch structure and appetite budget |
| `/wire:pitch-review` | Betting table: approve, reject, or defer |
| `/wire:release-brief-generate` | Formalise approved pitch as a release brief |
| `/wire:release-brief-validate` | Verify brief matches pitch decisions |
| `/wire:release-brief-review` | Client sign-off on scope and deliverables |
| `/wire:sprint-plan-generate` | Break brief into epics, stories, and point estimates |
| `/wire:sprint-plan-validate` | Check estimates fit within the appetite budget |
| `/wire:sprint-plan-review` | Delivery team review and approval |

Once the sprint plan is approved, run `/wire:release:spawn` to create the delivery release folder structure.

---

### Session Lifecycle

Two new universal commands improve continuity across working sessions on any release type:

**`/wire:session:start [release-folder]`**
- Enters Plan Mode
- Scans the release's `status.md` for the last completed artifact and last session's next focus
- Checks `.wire/research/sessions/` for prior research relevant to today's planned work
- Proposes a focused session plan for your approval before any work begins

**`/wire:session:end [release-folder]`**
- Records a summary of what was accomplished
- Appends a row to the `Session History` table in `status.md`
- Suggests the next focus for the following session

Use these at the start and end of every working session for a clean audit trail without manual note-taking.

---

### Research Persistence

The research persistence skill (`skills/research/SKILL.md`) auto-activates during technical research tasks:

- **Before research**: checks `.wire/research/sessions/` for prior findings on the same topic so you don't repeat work already done
- **After research**: saves a structured summary to `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md`
- `session:start` automatically surfaces relevant prior research when beginning a session

---

### Migration Command

`/wire:migrate` migrates a pre-v3.4.0 flat layout to the new two-tier structure:

```
/wire:migrate
```

The command is interactive — it shows you what it will move and asks for confirmation before making any changes. It is safe to re-run (skips anything already migrated).

**What it does:**
1. Detects old-style release folders at `.wire/<folder>/`
2. Proposes clean release names (e.g. `20260202_barton_peveril_live_pastoral` → `01-barton-peveril-live-pastoral`)
3. Creates `.wire/engagement/`, `.wire/releases/`, `.wire/research/sessions/`
4. Moves each release folder to `.wire/releases/<new-name>/`
5. Finds SOW files → moves to `.wire/engagement/`
6. Finds meeting notes and transcripts → moves to `.wire/engagement/calls/`
7. Generates `.wire/engagement/context.md` from metadata in the migrated `status.md` files
8. Produces a migration report

---

### Wire Studio Updates

- All UI labels updated from "Project" to "Release" (dialogs, menus, buttons, tooltips, empty states)
- **Release Type** selector now includes `Discovery` as the first option
- **Migrate Layout** command added to the command palette
- **New Release** / **Open Release** / **Release Settings** in File and Release menus

---

## Upgrading

### From v3.3.x

**Plugin users:** reinstall the plugin to get the new command files:
```
/plugin install wire@rittman-analytics
```
Then restart Claude Code.

**Gemini CLI users:** update the extension:
```
gemini extensions update wire
```

### Migrating your `.wire/` directory

If you have existing engagements:
```
/wire:migrate
```
This is safe, interactive, and non-destructive. Review `.wire/engagement/context.md` after migrating and fill in any missing engagement details.

### Wire Studio

Deploy the latest image to Cloud Run:
```bash
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/ra-development/wire-studio/wire-studio:latest wire-web-ui/
docker push us-central1-docker.pkg.dev/ra-development/wire-studio/wire-studio:latest
gcloud run deploy wire-studio --image us-central1-docker.pkg.dev/ra-development/wire-studio/wire-studio:latest --region us-central1 --project ra-development
```

---

## Full Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the complete version history.
