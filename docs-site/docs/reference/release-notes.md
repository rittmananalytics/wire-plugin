---
sidebar_position: 7
title: Release Notes
---

# Release Notes

Recent release history for the Wire Framework. For full changelog detail from v3.0.0 onwards, see [CHANGELOG.md](https://github.com/rittmananalytics/wire-plugin/blob/main/CHANGELOG.md).

---

## v3.9.5 — Auto-delegation for all generate commands + docs expansion

**Released**: June 2026

Every generate command now auto-delegates to its specialist agent — not just migration commands. v3.9.5 extends the delegation protocol to all 44 remaining generate specs across requirements, discovery, design, development, testing, deployment, and enablement.

**Key changes**:
- 11 new shared utility specs (`specs/utils/*_delegate.md`) — same 4-step protocol as the migration delegate: check agent definition, re-entrancy guard, dispatch to specialist, inline fallback
- Auto-delegation preamble added to all 44 non-migration generate specs
- Docs site: [How Wire Works](../getting-started/how-wire-works) page added to Getting Started
- Docs site: mermaid diagrams now centred sitewide
- Docs site: "First release?" info admonition added before `/wire:new` block in all 12 release-type tutorials
- Docs site: [Platform Migration](../release-types/platform-migration) `## MCP server connections` section — Snowflake, BigQuery, Fivetran, RudderStack, Coupler.io, Segment, Airbyte, Hightouch, VPC tunnel
- Homepage colour updated to `#4F60FF`, feature highlights corrected to 50+ slash commands
- `LICENSE` now included in the wire-plugin dist package

---

## v3.9.4 — Docs cleanup and bundling fix

**Released**: June 2026

Version strings and documentation pages updated to reflect v3.9.3/v3.9.4 changes. Docusaurus docs-site bundled into the plugin release via `build-packages.sh`. No spec or behaviour changes beyond v3.9.3.

---

## v3.9.3 — Migration generate commands auto-delegate to `migration-specialist`

**Released**: June 2026

All 16 migration `generate` commands now check for the `wire:migration-specialist` agent definition and dispatch to it automatically — closing the gap where `delegate.md` documented per-command auto-delegation but no individual migration spec implemented it.

**Key changes**:
- New shared utility spec `specs/utils/migration_agent_delegate.md` — 4-step delegation protocol: check for agent definition, re-entrancy guard, dispatch to `wire:migration-specialist`, inline fallback
- Auto-delegation preamble added to all 16 migration generate specs: `target-setup`, `dbt-migration`, `ingestion-migration`, `migration-strategy`, `migration-inventory`, `cutover`, `db-object-audit`, `dbt-audit`, `ingestion-audit`, `orchestration-audit`, `orchestration-migration`, `reverse-etl-audit`, `reverse-etl-migration`, `security-audit`, `migration-report`, `lineage`
- `utils/migration-agent-delegate` compiled as a registered command in the plugin so installed instances resolve the spec reference at runtime

See [Wire Agents](../advanced/wire-agents) and [Platform Migration](../release-types/platform-migration) for full details.

---

## v3.9.2 — `dashboard-mock-developer` and `mock-data-developer` agents

**Released**: June 2026

Two new specialist agents activate exclusively for `dashboard_first` releases, bringing the total to 14.

**`dashboard-mock-developer`** owns the interactive mockup phase. It generates an HTML mock immediately from requirements, iterates with you until approved, then produces three derived artifacts atomically: `dashboard_visualization_catalog.csv`, `dashboard_spec.md`, and `data_model_requirements.md`. The last file is the primary input for `data-designer` and `mock-data-developer`.

**`mock-data-developer`** handles seed data and data refactor — two time-separated phases. Phase 1: CSV seed files with referential integrity and domain-realistic distributions, allowing `dbt seed && dbt run` before any client data access. Phase 2: repoints staging models from seeds to real client sources once access is confirmed, with a written refactor plan before any code changes.

See [Wire Agents](../advanced/wire-agents) and [Dashboard-First](../release-types/dashboard-first) for full details.

---

## v3.9.1 — Fan-out parallelism for large dbt model sets

**Released**: June 2026

`/wire:delegate` gains fan-out parallelism: when a dbt layer has more than 5 models, it splits the layer into batches of 5 and runs one `dbt-developer` agent per batch in parallel. Layers remain sequential (staging → integration → warehouse); agents within each layer wave run concurrently. The same fan-out applies to `semantic-layer-developer` (by explore) and `migration-specialist` (by source system).

---

## v3.9.0 — Wire Agents Phase 1: 12 Specialists + `/wire:delegate`

**Released**: June 2026

The agent taxonomy expands to 12 specialists covering every Wire release type. The orchestration command is rewritten for local execution — no managed agents API required, no external API key beyond the user's existing Claude Code subscription.

### New specialist agents

| Agent | Release types |
|---|---|
| `discovery-analyst` | discovery, sop_discovery |
| `data-designer` | full_platform, pipeline_only, dbt_development |
| `pipeline-engineer` | full_platform, pipeline_only |
| `dbt-developer` | full_platform, pipeline_only, dbt_development |
| `semantic-layer-developer` | full_platform, dbt_development |
| `orchestration-engineer` | full_platform, pipeline_only |
| `data-quality-engineer` | full_platform, dbt_development |
| `migration-specialist` | platform_migration |
| `delivery-lead` | all release types |
| `agentic-data-stack-developer` | agentic_data_stack |
| `agentic-commerce-developer` | agentic_commerce |
| `qa-agent` | all release types |

### Key changes

- **`/wire:delegate`** replaces `/wire:orchestrate` — dispatches pending release work to specialist subagents using Claude Code's native Agent tool. Runs on the user's workstation, using their existing API key. No managed agents service needed.
- Each agent appends non-obvious decisions to `decisions.md` as it works — downstream agents and human reviewers use this as a lightweight audit trail.
- **Auto-delegation**: individual generate and validate commands now delegate to the appropriate specialist automatically. Review commands stay in the main session.
- All 12 agent definitions are bundled into the distributed plugin under `agents/`.

See [Wire Agents](../advanced/wire-agents) for full usage.

---

## v3.8.6 — Wire Agents Phase 1: Initial Eight Agents

**Released**: June 2026

First cut of the specialist agent system. Superseded by v3.9.0 which expanded the taxonomy and replaced the orchestration model.

- Eight initial agents: `dbt-developer`, `lookml-developer`, `dashboard-prototyper`, `migration-auditor`, `qa-agent`, `data-quality-agent`, `stakeholder-interviewer`, `playbook-generator`
- `/wire:orchestrate` command (replaced by `/wire:delegate` in v3.9.0)
- `status.md` gains an agents block: mode, active sessions, completed sessions
- `/wire:upgrade` surfaces `/wire:orchestrate` for releases created before v3.8.6

---

## v3.8.5 — Wire-Aware PR Template

**Released**: June 2026

- New **`/wire:utils-pr-create`** command — reads `execution_log.md` and `status.md` to auto-populate a pull request body
- `/wire:new` Step 10.5 now scaffolds `.github/pull_request_template.md` at engagement setup
- PR template sections: release folder, artifacts changed, Wire commands run, Wire commands next, Jira/Linear links

---

## v3.8.4 — dbt Migration Companion YAML Coverage

**Released**: June 2026

`dbt-migration-generate` and `dbt-migration-validate` now cover the companion schema/properties YAML alongside the model SQL.

- Explicit repointing of `sources.yml` to the target namespace (parameterised `database`/`schema`)
- Translation of source-dialect SQL inside singular tests, `where:` filters, and `dbt_utils`/`dbt_expectations` arguments
- Column-level `policy_tags`/`meta` authored into the YAML when column protection is dbt-managed
- New validate **Check 7**: enforces companion-YAML coverage — un-repointed `sources.yml`, untranslated test SQL, or dropped policy-tag config all fail

---

## v3.8.3 — Reverse ETL Parallel-Workspace Migration

**Released**: June 2026

Hightouch migration defaults changed to reduce production risk during warehouse migrations.

- **Parallel-workspace topology** (new default): clone the Hightouch config repo into a fresh workspace pointed at the target warehouse, validate with syncs disabled, then enable — leaving the source-backed workspace untouched until cutover. In-place source re-point retained as a fallback.
- Validation is now **preview-based against a frozen source baseline**: destination connections present but disabled; sync previews and record-level inspection only.
- Added **sync-level transformation review**: field mappings, computed fields, sync filters, match/identity-resolution rules, and audience inclusion/exclusion per sync — a matching model output doesn't guarantee a matching sync.

---

## v3.8.2 — `/wire:upgrade` and Wire Adoption Review

**Released**: June 2026

### `/wire:upgrade`

Brings an existing release `status.md` up to date with the current plugin version's schema.

- Adds missing YAML sections and keys from the canonical template for the release type
- Stamps `wire_plugin_version` and `last_upgraded_at`
- Surfaces new commands that weren't available when the release was created
- `--dry-run` flag to preview changes without modifying files
- Idempotent — safe to re-run. Complements `/wire:migrate` (which handles layout changes); `/wire:upgrade` handles schema drift within an already-correct layout.

### `cowork-wire-adoption-review` skill

New Wire Work plugin skill — generates structured Wire and Claude Code adoption reports from BigQuery telemetry (`ra-development.analytics.coding_agent_prompts_fact`).

Three report types:
- **Project-level**: adoption rate, command usage, session lifecycle compliance, discovery phase gap analysis, recurring manual patterns, recommendations
- **Consultant-level**: individual usage patterns across engagements, comparison to RA average
- **Company-wide**: cross-engagement analysis — what worked, what didn't, standardisation progress

Enriches from GitHub delivery repos, Jira, and Fathom meeting context when available.

---

## v3.8.1 — Platform Migration Translation Improvements

**Released**: June 2026

- Two new platform-pair translation examples: array-membership joins (`FLATTEN` / `IN UNNEST` / `ARRAY_CONTAINS`) and `ARRAY_AGG` null and struct-array semantics
- New `dbt_neutral_translation.md`: macro-first hierarchy (dbt built-in → `dbt_utils` → dispatched macro → `target.type` last) and equivalence-testing backbone for dual-target projects
- New `snowflake_to_bigquery/translation_reference.md`: exhaustive deep reference with a 25-item silent-behaviour-change checklist
- New **`/wire:dbt-migration-lint`**: static, offline pre-warehouse equivalence lint (dialect parse-check + silent-behaviour-change rules) run before the live equivalency loop
- New feature-detection tags: `flatten_join`, `array_agg`, `in_unnest`

---

## v3.8.0 — Droughty Integration

**Released**: June 2026

Integrates the Droughty schema-introspection toolkit as a first-class Wire release type. Droughty is a bottom-up, schema-driven complement to Wire's top-down document-driven workflow.

Nine new `/wire:droughty-*` commands:

| Command | What it does |
|---|---|
| `/wire:droughty-setup` | Install pinned Droughty, generate `profile.yaml` and `droughty_project.yaml` |
| `/wire:droughty-introspect` | Schema inventory: tables, columns, estimated row counts, PK/FK coverage |
| `/wire:droughty-dbml` | DBML entity-relationship diagram from live warehouse schema |
| `/wire:droughty-docs` | AI-generated field descriptions for all warehouse columns (requires OpenAI key) |
| `/wire:droughty-qa` | LangGraph data quality agent report (requires OpenAI key) |
| `/wire:droughty-stage` | dbt staging SQL + `sources.yml` from a BigQuery dataset |
| `/wire:droughty-dbt-tests` | Pattern-based `schema.yml` tests from deployed table schema |
| `/wire:droughty-lookml` | Base LookML views from deployed dbt tables; writes to `views/generated/` |
| `/wire:droughty-generate` | Full Droughty phase in sequence |

Two operating modes: **discovery/audit** (maps an existing warehouse — no dbt deployment needed) and **post-dbt** (generates the base LookML and test layer from deployed dbt models, feeding into `/wire:semantic_layer-generate`).

See the [Droughty release type](../release-types/droughty) for a full walkthrough.

---

## v3.7.x — Platform Migration, Agentic Data Stack, Snowflake

**Released**: June 2026

Major features added across the v3.7 series:

- **v3.7.7** — Full Snowflake support: estate audit via Snowflake MCP server; all Snowflake-native object types catalogued (Dynamic Tables, Streams, Tasks, Pipes, Semantic Views, masking/row-access policies). Hightouch reverse ETL audit added as a sixth `platform_migration` audit track.
- **v3.7.5** — Interactive lineage visualisation: `/wire:lineage-generate` produces a self-contained HTML dependency explorer showing the full dbt graph from raw source to warehouse object. Six layers: Ingestion → Seeds → Staging → Integration → Warehouse → DB Objects.
- **v3.7.4** — `agentic_data_stack` gains an explicit LookML views step (`/wire:ads_lookml-views-generate/validate/review`) between canonical models and the semantic layer build.
- **v3.7.3** — **Agentic Data Stack** release type: 41 new `ads_` commands across five phases (Audit, Design, Build, Validate, Deploy). Addresses governance failures — accuracy failures in analytics agents are almost always caused by too many tables or conflicting metric definitions.
- **v3.7.0** — **Platform Migration** release type: full warehouse-to-warehouse migration lifecycle (BigQuery ↔ Snowflake ↔ Databricks) with six parallel audit tracks: database objects, dbt models, dashboards, pipelines, orchestration, and reverse ETL.

---

## v3.5.x — Agentic Commerce, Droughty Preview

**Released**: May 2026

- **v3.5.0** — **Agentic Commerce** release type: AI-powered ecommerce storefront delivery. Uses Lovable for rapid base storefront generation (React 18 + Vite + Tailwind + Shopify Storefront API), GitHub bidirectional sync, and Supabase as the backend. Nine feature commands: `storefront`, `semantic_search`, `conversational_assistant`, `virtual_tryon`, `visual_similarity`, `llm_tools`, `personalisation`, `ucp_server`, `demo_orchestration`.

---

## v3.4.x — Discovery SOP, Jira/Linear, Dashboard-First

**Released**: March–May 2026

- **v3.4.9** — Dashboard-First release type: rapid Looker dashboard development from business questions without full upstream dbt build
- **v3.4.3** — Discovery SOP (canonical) release type: structured discovery following the RA Standard Operating Procedure
- **v3.4.0** — Jira and Linear issue tracking integration: one Epic per project, Tasks per artifact, Sub-tasks per lifecycle step; `/wire:utils-linear-create` for Linear project setup

---

## v3.3.x — Document Store Integration

**Released**: January–February 2026

- **v3.3.0** — Confluence and Notion document store integration: all generate commands publish artifacts to the configured store; review commands surface reviewer comments and document edits as review context. Configured at engagement setup via `/wire:new` Step 9.5.

---

## v3.0.0 — Initial Release

**Released**: October 2025

Wire Framework initial release.

- Six-phase delivery lifecycle: Requirements → Design → Development → Testing → Deployment → Enablement
- 12 release types covering the full data platform delivery scope
- Claude Code (Anthropic) and Gemini CLI (Google) runtimes
- Artifact generate/validate/review pattern with execution log and decision audit trail
- Fathom MCP integration for surfacing meeting context during reviews
