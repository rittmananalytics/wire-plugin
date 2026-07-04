---
sidebar_position: 7
title: Release Notes
---

# Release Notes

Recent release history for the Wire Framework. For full changelog detail from v3.0.0 onwards, see [CHANGELOG.md](https://github.com/rittmananalytics/wire-plugin/blob/main/CHANGELOG.md).

---

## v3.10.4 — Cube, Omni, and OAC semantic-layer options; Wire Studio and agentic_commerce removed

**Released**: July 2026

Three new semantic-layer/reporting-tool options, a real bug fix from live migration feedback, and a cleanup pass removing two low-usage features and their remaining references.

**Cube.dev, Omni Analytics, and Oracle Analytics Cloud (OAC) join LookML as semantic-layer options.** Each ships as a `wire/skills/` entry activated when the engagement's semantic layer is that tool rather than Looker: `cube` encodes RA's own Cube modeling conventions and coding standards alongside Cube's core concepts and MCP server; `omni` wraps the official `exploreomni/omni-agent-skills` and adds `omni-audit`/`omni-migration` reporting-layer migration commands (gated on `migration.reporting_tool: omni`); `dbt-to-smml` and `smml-semantic-modeling` generate and hand-author OAC's SMML (Semantic Modeler Markup Language) semantic model from a dbt project, with `oac-audit`/`oac-migration` commands for reporting-layer migration (gated on `migration.reporting_tool: oac`). OAC's dialect-specific SQL concentrates in the physical layer (connection pools, physical tables, physical joins), so its migration classification happens at the physical-table level, mirroring how Omni's classification happens at the model-view level rather than per-tile.

**`dbt-audit-generate` no longer misclassifies conditionally-enabled models as disabled.** Models whose `enabled` config resolves from a `var(...)` — in-model `config()` blocks or folder-level `+enabled` in `dbt_project.yml` — are now classified `conditional:<var_name>` and kept in migration scope regardless of the var's default resolution, with dependency edges resolved via a flags-on re-parse or a documented fallback rule. `dbt-audit-validate` independently re-scans for var-driven config to catch a model still marked `true`/`false`/null-batch that should be `conditional`.

**Wire Studio (the `wire-web-ui` browser interface) and the `agentic_commerce` release type are removed entirely**, along with every reference across docs, build scripts, and tests — both showed effectively no engagement usage against BigQuery telemetry. `USER_GUIDE_droughty.md` and `USER_GUIDE_platform_migration.md`, which duplicated content already in `USER_GUIDE.md`, are also removed, along with three stale feature-design docs for work that had already shipped.

---

## v3.10.3 — dbt audit hardening, migration batching, PII/equivalency fixes

**Released**: July 2026

A round of fixes and a new command trio, each traced back to specific feedback from a live Snowflake → BigQuery migration. Additive and backward compatible.

**`dbt-audit-generate` hard-fails on an unresolvable project** — no more silently substituting a prior release's catalogue, the failure mode that produced a stale, wrong audit undetected. It resolves nested dbt projects one level down when the configured path has no `dbt_project.yml` of its own, orders batches with a real topological sort over a parsed manifest (replacing a `ref_count` heuristic that produced hundreds of forward-reference violations), scans the macro layer for platform-specific SQL — classifying each hit macro `translate` / `redesign` / `manual-review-out-of-scope` — and produces a tiered **batch-zero macro translation plan** as a first-class artifact. `dbt-audit-validate` gains a disk-reconciliation check that independently re-derives the catalogue rather than trusting generate's self-report.

**New `/wire:migration-batching-*` trio** — partitions the migration inventory into named domain batches (independently-schedulable, multi-layer slices, distinct from `dbt_audit`'s translation batches) checked against the real dependency graph. `-review` is the client adjudication gate for composition and schedule; `-validate` re-derives the graph independently, catching a batch plan drifting out of sync with reality the way a hand-drawn plan can once the true dependencies are known.

**PII policy tags resolve automatically** — `dbt-migration-generate` looks up a tag map with a case-normalised lookup instead of requiring manual per-column authoring, flagging unresolved policies `MANUAL REVIEW REQUIRED` rather than dropping them silently.

**Equivalency pins relative-date models in live mode too** — not just under the opt-in `--baseline` freeze — closing a false-divergence gap that cost a real investigation cycle on a pilot migration. Reports are now organised at the table level with explicit column-completeness and value-match lines per table.

**Housekeeping** — Atlassian MCP endpoint updated from the deprecated `/v1/sse` path to `/v1/mcp`.

---

## v3.10.2 — Platform-migration hardening

**Released**: June 2026

Hardening from a Snowflake → BigQuery lift-and-shift: migrate models faithfully, validate them deterministically, and keep them in sync with a moving source. Additive and backward compatible.

**Faithful materialisation + override hook** — `dbt-migration-generate` now preserves each model's resolved materialisation (incremental stays incremental with its strategy/partition/cluster; table stays table), instead of a blanket `materialized: table`. An engagement can diverge via a declarative override file (`migration.materialization_overrides_path`: `default: preserve` + `overrides[]` with `select`/`exclude`/`force_materialized`); the framework ships no path, no layer names, no rules.

**Deterministic, frozen-baseline equivalency** — `migration-strategy` defines the frozen baseline (instant `T`, Snowflake zero-copy clone, BigQuery Bronze watermark, expected type-translation allow-list). `equivalency-validate` gains a baseline-pin mode (`--baseline`), a deterministic-build switch, a tier-3 value-level comparator (per-column fingerprints + normalised cross-platform row hash), run-metadata capture, and `--batch` fan-out. `migration.equivalency_baseline` is a release-level field.

**Per-model register + scheduled drift gate** — `/wire:migration-register-*` records per model: source path, last-migrated commit, BigQuery target, state, and last equivalence result. `/wire:migration-drift-*` diffs the live source against each model's last-migrated commit (`dbt ls --select state:modified`), classifies new/modified/removed, flags downstream Hightouch syncs (via a new `model_sync_map.json` from `lineage-generate`), and triggers a policy-tag regeneration when a source `meta.masking_policy` changes. Ships with on-change and scheduled CI templates.

**Housekeeping** — client engagement records relocated out of the framework repo; the client name removed from all specs, docs, templates, and fixtures.

---

## v3.10.1 — Tenant carve-out variant + Metabase reporting layer

**Released**: June 2026

A tenant carve-out variant for the platform migration release type, plus Metabase reporting-layer support. Both are additive and backward compatible — a full migration with no Metabase behaves exactly as before.

**Tenant carve-out variant** — platform migration now runs in `tenant_carveout` scope as well as the default `full_migration`, set by `migration.scope` with a `migration.tenant_predicate` captured at `/wire:new`. The carve-out reuses the whole migration command set and threads tenant scoping through equivalency — the existing checks gain the predicate on both source and target, with no new check types (min/max already lives in value sampling; checksum and aggregate totals already exist; schema stays structural) — and through the security/IAM chain: tenant-scoped vs shared role classification → a two-project / tenant-scoped IAM model with a row-level security predicate → tenant-scoped GRANTs and the RLS policy in `04_security.sql`, reusing the existing PII policy-tag taxonomy.

**New carve-out commands** — `/wire:region-tagging-*` classifies in-scope items into confident-region / shared-row-level / global-deferred buckets (candidates for adjudication, never a binary include/exclude or auto-removal; `-review` is the human adjudication gate). `/wire:data-residency-assessment-*` produces the GDPR and data-residency assessment including the legal review of the historical data window — RA prepares it as data processor and flags every point needing the client's DPO/legal determination, with `-review` as the client sign-off gate. `/wire:bulk-copy-migration-*` does a Snowflake → BigQuery bulk historical copy (BigQuery Data Transfer Service / GCS-staged) in place of re-ingestion, two-stage with an equivalency gate between pilot partition and remainder, under a scoped service account with a tenant guard. `/wire:logical-access-uat-*` proves region-scoped access isolation — `-validate` requires at least one negative test per IAM boundary in `04_security.sql`, and `-review` is the isolation-proof sign-off before cutover.

**Metabase reporting-layer support** — Wire's reporting-layer support was Looker-only. Set `migration.reporting_tool: metabase` to enable `/wire:metabase-audit-*` and `/wire:metabase-migration-*`, a general capability for any migration where the client uses Metabase, not gated by `migration.scope`. The audit catalogues collections, dashboards, cards (with SQL), database connections, and permission groups; the migration translates card SQL to BigQuery, remaps permission groups, validates on a throwaway decoy collection, and repoints the Metabase database connection from Snowflake to BigQuery in two stages with per-stage rollback (it requires a client-supplied query inventory). Both build on the imported `metabase` skill, wrapping the upstream `metabase/agent-skills`.

---

## v3.10.0 — Platform-migration hardening

**Released**: June 2026

Platform-migration hardening ahead of a full Snowflake → BigQuery migration. A series of pilot calls turned up ways the reverse-ETL and dbt-migration commands would have misfired at estate scale; this release fixes them. All changes are additive and backward compatible.

**Reverse-ETL topology — additive PR-gated syncs in the existing repo** — the default was a parallel workspace, which is wrong when Hightouch is managed by GitHub Sync: GitHub Sync carries models and syncs but not destinations, so a new workspace forces re-authenticating every destination. The default is now additive — branch the existing config repo, add target-warehouse syncs alongside the source-warehouse ones, reuse destinations in place, and stage every change as a pull request the client reviews and merges. RA never enables/disables syncs directly. Cutover is two client-merged PRs (disable source-origin, enable target-origin). Parallel-workspace and in-place re-point remain documented alternatives.

**Decoy destination mapping** — destination safety is now a decoy ID-mapping table plus a scoped credential, not a "disabled" flag. Each test sync carries a decoy destination of the same type; production destination IDs are absent until the cutover PR swaps them back; the credential can write to decoy targets only.

**Drift-aware translation** — the command reads a per-release drift manifest and won't apply the generic `VARIANT → JSON` / `JSON_VALUE` mapping to a column that lands as `STRING` under BigLake Iceberg, mirroring any reconciliation a `dbt_migration` diff already recorded.

**Re-verified audit tags and scope gate** — approach tags are re-checked before translating (re-scanning `repoint` syncs for `::`, `FLATTEN`, `QUALIFY`, `IFF`, `NVL`, `CONVERT_TIMEZONE`, and variant-path access, reclassifying to `rewrite_model` when found), and any sync whose source model isn't built on target is deferred rather than silently included.

**Reverse-ETL audit — table/custom source resolution** — `table` and `custom` model types now have their source objects resolved (previously only some `rawSql` models did, leaving ~37% of active syncs with no recorded object). The audit reports source-resolution coverage and lists unresolved syncs explicitly.

**dbt-migration — per-model transformation log to BigQuery** — a structured record per migrated object (object, batch, dialect changes, manual-review flags, confidence) is persisted to a configurable BigQuery audit table. The `.diff.md` output is unchanged; this is additive.

**New — shared migration pre-flight gate** — a shared spec referenced by both migration generate commands confirms, before a batch starts, that the source dbt project was freshly re-synced for this batch, source objects exist and have data on target, the target environment is prepared (not a playground), and (reverse-etl) the decoy mapping and scoped credential are in place. Any failure stops the command before generating.

---

## v3.9.9 — Iterative migration loop, source registration, batch DAGs, acceptance packs

**Released**: June 2026

Four improvements to the platform migration release type, driven by observations from a live engagement pilot.

**Iterative translation+equivalency loop** — `/wire:dbt-migration-generate` now embeds a per-model closed loop directly. For each model: translate → compile-check (LIMIT 0) → run on target → three equivalency checks (row count ±0.5%, schema, 1000-row column value sampling) → auto-diagnose and fix on failure → repeat up to 5 iterations. Both source and target platform MCPs must be connected before the command starts. No mid-loop manual review prompts — the loop runs autonomously for all models in the batch, then prints a results table.

**Source repository management** — two new commands manage the source dbt project snapshot: `/wire:migration-source-register <release>` records the git repo URL (or local path), branch, and models path in `status.md`. `/wire:migration-source-refresh <release>` pulls or clones the repo into a local cache. `dbt-migration-generate` checks `migration_source.last_refreshed` at startup and warns if the snapshot is older than 24 hours.

**Mermaid batch DAGs** — `/wire:migration-strategy-generate` now generates one Mermaid flowchart per batch at `artifacts/migration_strategy/dag_batch_N.md`. Initial state: all nodes grey (not started). As `dbt-migration-generate` processes each model, nodes update in-place: orange = translated/in-progress, green = equivalency passed, red = failed after 5 iterations. DAG files are embedded in the strategy document.

**Migration acceptance packs** — after all models in a batch reach terminal state, `dbt-migration-generate` auto-generates `acceptance_pack_batch_N.md` with a per-model results table, confirmation statements, Mermaid DAG embed, and sign-off block. New command `/wire:migration-acceptance-pack-review <release> [--batch N]` presents the pack for stakeholder sign-off (Approve/Reject/Hold), appends the completed sign-off to the document, and syncs to Jira and the document store.

---

## v3.9.8 — dbt node selectors for migration translation; quieter telemetry

**Released**: June 2026

`/wire:dbt-migration-generate` gains `--select` and `--exclude` flags accepting dbt's full node-selection grammar — graph operators (`+vehicles`, `vehicles+`, `+vehicles+`, `2+vehicles`, `@vehicles`), space-separated unions, comma-separated intersections, and `tag:` / `config.materialized:` / `path:` set selectors. This scopes which models a migration translates by their graph relationships — for example `--select +vehicles` translates `vehicles` plus everything upstream of it, the natural shape for a lift-and-shift pilot slice.

Wire resolves the selector itself over the source project's dependency graph — **no dbt binary is required**. The graph is read from the source project's `target/manifest.json` (a plain JSON artifact, no warehouse connection), with a fallback that parses `ref()`/`source()` and YAML config when no manifest is present. Before translating, Wire prints the resolved model list for confirmation and aborts if the selector matches nothing. `--select` cannot be combined with `--batch`/`--model`/`--models`; a bare `--select vehicles` behaves exactly like `--model vehicles`.

**Quieter telemetry** — anonymous usage tracking no longer runs as visible Bash tool calls inside every command. On the Claude Code plugin it moves to a `UserPromptExpansion` hook that fires when a `/wire:` command runs, so nothing clutters the console. Behaviour is unchanged: still anonymous, still opt-out with `WIRE_TELEMETRY=false`. The Gemini CLI extension, which has no hook system, uses a single backgrounded call instead.

---

## v3.9.7 — Migration reliability: post-execution hooks, stale artifact detection, Data Safety blocks, ingestion pre-flight

**Released**: June 2026

Post-execution hooks are now on every migration spec. All 16 migration generate and 16 migration validate commands run execution log → Jira sync → docstore sync → auto-commit after every run, bringing them into line with non-migration commands. A new `specs/utils/commit.md` utility handles the git commit step.

**Stale artifact detection** — all 16 migration generate commands now prompt before overwriting an already-complete artifact. If `generate: complete` is set in `status.md` or the output file already exists, the command asks for confirmation. First-time runs see no friction.

**Data Safety blocks** — `/wire:dbt-migration-generate`, `/wire:ingestion-migration-generate`, `/wire:equivalency-validate`, and `/wire:reverse-etl-migration-generate` now emit a named READ ONLY reminder before starting, listing blocked production project IDs from `data_safety.production_projects`. Production project IDs are collected during `/wire:new` setup for `platform_migration` releases.

**Ingestion pre-flight expanded** — `/wire:ingestion-migration-generate` now probes all ingestion tools in scope before starting, not just Fivetran. It reads the audit for every distinct tool with `include_in_migration: true` connectors and checks each one's MCP server or API credentials. Coverage: Fivetran, RudderStack, Coupler.io (MCP); Airbyte, Segment (API env vars); Stitch/other (runbook-only). Auth failures halt the run; unconfigured tools fall to the runbook path.

**`/wire:mcp` simplified** — `update` and `auth` subcommands removed (wrappers around `claude mcp` with no Wire-specific value). Now `list`, `view`, and `check` only. New `check [release-folder]` subcommand probes all MCP servers required by a release and reports CONNECTED / AUTH_REQUIRED / UNAVAILABLE / NOT_CONFIGURED per server. The platform_migration playbook session start sequence is now: `/wire:start` → `/wire:mcp check` → next command.

Other improvements: `/wire:start` adds a Recent Activity table from `execution_log.md`; `/wire:new` detects duplicate releases before creating; `/wire:target-setup-generate` outputs a `~/.dbt/profiles.yml` block to the console; Jira `state_mapping` in `status.md` overrides default workflow transition labels.

---

## v3.9.6 — MCP-driven ingestion migration, parallel dbt agents, Looker mockup refinements

**Released**: June 2026

**Ingestion migration is now MCP-driven.** `/wire:ingestion-migration-generate` probes the relevant ingestion tool's MCP server (Fivetran, Airbyte, etc.), creates new connectors on the target destination, and generates connect card URLs for credential entry — no manual UI steps beyond opening each link. Wire always creates new connectors; it never edits or re-points a source connector mid-parallel-run. The runbook fallback applies when the MCP server is unreachable.

**dbt migration now uses parallel agents within each batch.** Models are split into groups of ~5 and one `wire:migration-specialist` agent is spawned per group simultaneously — a 20-model batch runs as 4 agents in parallel. Translated models preserve the source project's folder structure (`models/staging/stripe/stg_x.sql` → `migration/dbt/staging/stripe/stg_x.sql`).

**Looker dashboard mockup** visual refinements: PNG image assets replace SVG placeholders for the logo, Create button, and toolbar strip; chart colours use the Google standard palette (`#4285F4`, `#EA4335`, `#FBBC04`, `#34A853`, `#FF6D00`, `#7E57C2`); font weight 400 globally on labels, tabs, table headers, and chart axes; KPI tile accent bars removed; tiles centred; no freshness label; no filter count badges.

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
