# Wire Framework Changelog

## [3.9.0] - 2026-06-12

### Added

- Twelve specialist agent definitions covering all Wire release types: discovery-analyst, data-designer, pipeline-engineer, dbt-developer, semantic-layer-developer, orchestration-engineer, data-quality-engineer, migration-specialist, delivery-lead, agentic-data-stack-developer, agentic-commerce-developer, qa-agent
- New /wire:delegate command replaces /wire:orchestrate — dispatches batch pending work to specialist local subagents using Claude Code's native Agent tool (no managed agents API or external key required)
- Each agent appends non-obvious choices to decisions.md; downstream agents and reviewers use this as the lightweight decision audit trail
- All 12 agent definitions bundled into the distributed plugin under agents/

### Changed

- Renamed /wire:orchestrate → /wire:delegate; spec rewritten for local Agent tool execution pattern
- Agent taxonomy expanded from 8 to 12 to cover all release types including platform_migration, agentic_commerce, agentic_data_stack, and droughty
- dbt-developer and qa-agent updated with correct cross-agent references and decisions.md convention

### Removed

- /wire:orchestrate spec (replaced by /wire:delegate)
- Eight v3.8.6 placeholder agent definitions (dashboard-prototyper, lookml-developer, migration-auditor, data-quality-agent, stakeholder-interviewer, playbook-generator) replaced by correct agent taxonomy

---

## [3.8.6] - 2026-06-12

### Added

- Eight specialist agents (dbt-developer, lookml-developer, dashboard-prototyper, migration-auditor, qa-agent, data-quality-agent, stakeholder-interviewer, playbook-generator) defined in wire/agents/
- New /wire:orchestrate command decomposes pending release work and dispatches to parallel Claude Managed Agent sessions
- Build script bundles wire/agents/ into the distributed plugin
- status.md gains an agents block tracking mode, active sessions, and completed sessions
- /wire:upgrade surfaces /wire:orchestrate for releases created before v3.9


All notable changes to the Wire Framework are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---


## [3.8.5] - 2026-06-12

### Added

- New /wire:utils-pr-create command auto-populates PR body from execution_log.md and status.md
- wire:new Step 10.5 scaffolds .github/pull_request_template.md during engagement setup
- Wire-aware PR template covers release folder, artifacts changed, commands run/next, and issue links

## [3.8.4] - 2026-06-12

### Changed

- `dbt-migration-generate` and `-validate` now cover the **companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`), not just the model `.sql`. Adds an explicit step to: repoint `sources.yml` to the target namespace (parameterised `database`/`schema`); translate source-dialect SQL inside singular/custom tests, `where:` filters, and `dbt_utils`/`dbt_expectations` arguments; and author column-level `policy_tags`/`meta` into the YAML when column protection is dbt-managed (or record it as deferred to the security workstream). New validate Check 7 enforces it.

## [3.8.3] - 2026-06-12

### Changed

- Reverse ETL migration (`/wire:reverse-etl-migration-generate` and `-validate`) and the `hightouch` skill now default to a **parallel-workspace** topology for a warehouse migration: clone the Hightouch config repo into a new workspace pointed at the target warehouse, configure its GitHub Sync, translate models, validate there with syncs disabled, then enable — leaving the production source-backed workspace untouched. In-place source re-point is retained as a documented fallback for plans that don't support multiple workspaces.
- Reverse ETL validation is now **preview-based against a frozen source baseline**, with destination connections present-but-disabled (sync previews and record-level inspection), instead of enabling syncs and triggering live runs against downstream systems during validation.
- Added a **sync-level transformation review** step — field mappings, computed fields, sync filters, match/identity-resolution rules, and audience inclusion/exclusion — since a matching model output does not prove a matching sync.
- `reverse-etl-migration-validate` checks updated to match: topology recorded, preview-based validation with syncs disabled, per-sync sync-level review, and source left active until cutover.


## [3.8.2] - 2026-06-11

### Added

- New `/wire:upgrade [release-folder]` command — brings an existing release folder's `status.md` up to date with the current plugin version's schema. Adds missing YAML sections and keys from the canonical template for the release type, stamps `wire_plugin_version` and `last_upgraded_at`, surfaces new commands that weren't available when the release was created. Supports `--dry-run` to preview changes without modifying files. Safe to re-run (idempotent). Complements `/wire:migrate` (which handles layout changes) — `/wire:upgrade` handles schema drift within an already-correct layout.
- New `cowork-wire-adoption-review` Cowork skill (Wire Work plugin) — generates structured Wire Framework and Claude Code adoption reports from BigQuery telemetry (`ra-development.analytics.coding_agent_prompts_fact`). Three report types: **project-level** (full engagement deep-dive — adoption rate, command usage, session lifecycle compliance, discovery phase gap analysis, recurring manual patterns, recommendations), **consultant-level** (individual usage patterns across all engagements, comparison to RA average), and **company-wide** (cross-engagement analysis — what worked, what didn't, top opportunities, standardisation progress). Enriches from GitHub delivery repos, Jira, and Fathom meeting context when available.

## [3.8.1] - 2026-06-11

### Added

- Two new platform_pairs translation examples in both directions: array-membership joins (FLATTEN / IN UNNEST / ARRAY_CONTAINS) and ARRAY_AGG null and struct-array semantics
- New shared dbt_neutral_translation.md: macro-first hierarchy (dbt built-in to dbt_utils to dispatched macro to target.type last) and the equivalence-testing backbone for dual-target dbt projects
- New snowflake_to_bigquery/translation_reference.md: exhaustive deep reference with a 25-item silent-behaviour-change checklist; corrected PARSE_JSON and QUALIFY entries in the quick translation guide
- New /wire:dbt-migration-lint command: static, offline pre-warehouse equivalence lint (dialect parse-check plus silent-behaviour-change rules) run before the live equivalency loop
- New feature-detection tags: flatten_join, array_agg, in_unnest

## [3.8.0] - 2026-06-10

### Added

- New `droughty` release type — schema introspection and base-layer generation using the Droughty toolkit (BigQuery and Snowflake)
- `/wire:droughty-setup` — install pinned Droughty version, generate `profile.yaml` from Wire context, generate `droughty_project.yaml` with Wire-aligned output paths
- `/wire:droughty-introspect` — schema inventory report: tables, columns, estimated row counts, PK/FK coverage from `INFORMATION_SCHEMA`
- `/wire:droughty-dbml` — DBML entity-relationship diagram from live warehouse schema via `droughty dbml`
- `/wire:droughty-docs` — AI-generated field descriptions for all warehouse columns via `droughty docs` (requires OpenAI API key)
- `/wire:droughty-qa` — LangGraph data quality agent report via `droughty qa` (requires OpenAI API key)
- `/wire:droughty-stage` — dbt staging SQL + `sources.yml` from a BigQuery dataset via `droughty stage` (BigQuery only)
- `/wire:droughty-dbt-tests` — pattern-based `schema.yml` tests from deployed table schema via `droughty dbt`; merges with existing Wire-generated tests
- `/wire:droughty-lookml` — base LookML views, explores, and measures from deployed dbt tables via `droughty lookml`; writes to `views/generated/`, Wire extensions go in `views/extended/`
- `/wire:droughty-generate` — full Droughty phase in sequence; mode-aware (discovery/audit vs post-dbt deploy)
- `wire/droughty/pinned_version.txt` — pinned Droughty version (`0.20.1`)
- `wire/droughty/refresh_version.sh` — Wire repo owner script to pull latest Droughty version from PyPI and update the pin
- `wire/skills/droughty/SKILL.md` — auto-activating skill for Droughty configuration, command reference, LookML convention, and troubleshooting
- User guide section 19: full Droughty release walkthrough (both discovery/audit and post-dbt deployment modes)

## [3.7.9] - 2026-06-10

### Added

- Six Google Cloud skills (bigquery-basics, cloud-run-basics, gcloud, recipe-auth, two WAF pillars) from google/skills
- 26 Amplitude product-analytics skills plus the Amplitude MCP server registered in Wire's MCP catalog
- platform_migration: BigQuery Migration Service documented as an optional first-pass DDL/SQL translator
- platform_migration: new row-level checksum and business-invariant equivalency checks plus edge-case canonicalisation
- platform_migration: cutover rehearsal step, rollback decision tree, and 7-14 day rollback window with separate decommission
- platform_migration: AI-translation safeguards in dbt_migration (confidence rating, record-loss and hallucination guards)

## [3.7.8] - 2026-06-08

### Added

- Hightouch reverse ETL audit can now source config from a Git repo (audit/hightouch_git/) as an alternative to the REST API or CSV fallback
- Full model SQL available from Git source — no 200-character truncation as with the API
- Validation checks 6 and 8 auto-pass with informative skip messages when data source is Git
- Three-option data source waterfall in generate spec: API → Git → CSV, with clear user guidance at each fallback

## [3.7.7] - 2026-06-08

### Added

- **Snowflake support across Wire Framework**: two new skills and a significantly expanded `db_object_audit` spec for Snowflake as a migration source.
  - `wire/skills/snowflake-development/SKILL.md` — general Snowflake skill covering MCP server connection (`mcp__claude_ai_Snowflake__sql_exec`), SQL conventions, all Snowflake-native object types (Dynamic Tables, Streams, Tasks, Pipes, Stages, Semantic Views, masking/row-access policies, shares), and structured AI-readiness assessment (Clean / Contextual / Consumable / Current / Compliant factors with scored output).
  - `wire/skills/snowflake-semantic-views/SKILL.md` — dedicated skill for Cortex Analyst semantic views: FastGen, SQL DDL, and YAML creation workflows; VQR validation; audit checklist; debug table for common Cortex Analyst failures.
  - `wire/specs/migration/db_object_audit/generate.md` — Snowflake section expanded with ten explicit MCP queries covering every object type, `GET_DDL` for views/procedures, `SHOW SEMANTIC VIEWS`, a default migration approach table per Snowflake object type, and updated `status.md` YAML with new count fields.

- **Hightouch reverse ETL as sixth audit type** for `platform_migration` releases.
  - `wire/skills/hightouch/SKILL.md` — Hightouch REST API connection, object hierarchy (Source → Model → Sync → Destination, Customer Studio audiences/Journeys), CDC and Lightning sync engine, migration impact classification (repoint / rewrite_model / rebuild), read-only safety rules.
  - `wire/specs/migration/reverse_etl_audit/{generate,validate,review}.md` — full audit lifecycle: Hightouch API enumeration with CSV fallback, warehouse object dependency extraction from model SQL, eight validation checks (dependency coverage, Lightning engine flagging, dbt model cross-reference), internal RA review gate.
  - `wire/specs/migration/reverse_etl_migration/{generate,validate,review}.md` — migration runbook generation for all three approaches: source connection re-point, SQL dialect rewrite with before/after diff, Customer Studio full rebuild; Lightning schema provisioning SQL; parallel-run procedure; rollback per approach.
  - `wire/TEMPLATES/migration/reverse_etl_audit.md` — output template with sync catalog, warehouse dependency map, dbt model sync dependencies, Lightning engine section, decommission candidates, and recommended re-point order.

- **Reverse ETL integrated into migration inventory**: `migration_inventory/generate.md` now treats `reverse_etl_audit` as a conditional prerequisite (required when `migration.reverse_etl_tool` is set); adds `reverse_etl_sync` and `reverse_etl_destination` node types to the dependency graph; adds effort weights for repoint (0.5h), rewrite_model (2h), rebuild (8h); Mermaid diagram now shows six layers including Hightouch Syncs and Destinations.

- **Lineage diagram extended with Reverse ETL and Destinations layers**: `lineage/generate.md` updated to accept `--reverse-etl-audit` flag; when present, the diagram adds two rightmost layers — Reverse ETL (one node per sync, coloured by migration approach: green=repoint, amber=rewrite_model, red=rebuild) and Destinations (one node per unique destination type). Clicking a warehouse object highlights the full chain through to SaaS destinations.

- **`migration_audit_all` updated**: conditional sixth subagent launches when `migration.reverse_etl_tool` is set in `status.md`; token cost confirmation prompt reflects 5 or 6 audits dynamically.

- **Build script**: 6 new commands registered (`reverse-etl-audit/generate`, `reverse-etl-audit/validate`, `reverse-etl-audit/review`, `reverse-etl-migration/generate`, `reverse-etl-migration/validate`, `reverse-etl-migration/review`); PLATFORM MIGRATION lambda updated; command count updated to 49 for the migration release type.

## [3.7.6] - 2026-06-07

### Added

- `wire-release` skill: covers the full release lifecycle — bump type selection, pre-release cleanup, documentation updates, Wire Studio/VSCode updates, build, publish, and post-release verification
- `build-packages.sh`: README.md now copied to claude-plugin dist; image paths in USER_GUIDE.md and README.md rewritten from wire/docs/images/ to docs/images/ for correct resolution in the wire-plugin remote repo
- Version corrections: USER_GUIDE.md version header updated to 3.7.5; README.md heading corrected to v3.7.5

## [3.7.5] - 2026-06-06

### Added

- **`/wire:lineage-generate` command** for `platform_migration` releases — generates a self-contained interactive HTML visualisation of the full dbt model lineage, from raw source tables through seeds, staging, integration, and warehouse layers to the physical DB objects each warehouse model creates. No external dependencies: the output file runs in any browser. Powered by `wire/scripts/generate_lineage.py` and `wire/scripts/lineage_template.html` (vis.js Network v9.1.2 + Font Awesome, CDN-loaded).
- **`lineage_view` artifact** added to the `platform_migration` status template. Generate-only — no validate or review step.
- **Six-layer visual** with colour-coded node types: Ingestion (steel blue), Seeds (amber), Staging (mid blue), Integration (forest green), Warehouse (sienna), DB Objects (teal). DB Objects layer shows the physical table/view name from `config(alias='...')` in each warehouse model; falls back to the model filename where no alias is set.
- **Interactive controls**: click any node to isolate its full upstream and downstream lineage; click canvas to restore all nodes; filter by layer, complexity tier, or migration batch; drag a node to reposition its folder group; search by name.
- **dbt_audit enrichment**: nodes pick up complexity, batch number, and platform-specific feature tags from `dbt_audit.csv` when present.
- **Platform variant resolution**: where a warehouse folder contains both platform-specific and agnostic subdirectories, BigQuery files are preferred over agnostic, agnostic over Snowflake — matching the source platform for a BigQuery migration.
- **`/wire:lineage-generate` spec** at `wire/specs/migration/lineage/generate.md`.

### Changed

- **`lineage_view` is now positioned after `migration_inventory`**, not after `dbt_audit`. The inventory must be approved first so batch assignments and complexity ratings are finalised — the lineage view then shows that enrichment accurately. Updated in: `status_migration.md` template, `COMMANDS.md`, `USER_GUIDE.md`, `USER_GUIDE_platform_migration.md`.

---

## [3.7.4] - 2026-06-06

### Added

- **`ads_lookml-views` artifact** for `agentic_data_stack` releases — three new commands (`/wire:ads_lookml-views-generate`, `/wire:ads_lookml-views-validate`, `/wire:ads_lookml-views-review`) that run between `canonical_models` and `semantic_layer` in the Build phase. Generates or updates LookML view files for new and restructured canonical models in Looker projects, so views exist before `ads_semantic-layer-generate` adds metric definitions. Auto-skips with a status entry when `bi_tool` is not `looker`.
- **`lookml_project_path`** field in the `agentic_data_stack` status template.

---

## [3.7.3] - 2026-06-05

### Added

- **`agentic_data_stack` release type** — 41 new commands (`ads_` prefix) covering the full lifecycle for building a governed self-service analytics capability. Five phases: Audit (dataset, metric, query), Design (governance, semantic layer), Build (canonical models, semantic layer, knowledge skill, agent config), Validation (eval suite with per-domain accuracy gates, adversarial review), Launch Gate and Enablement.
- **`/wire:ads-audit-all`** — parallel fan-out utility running all three audit commands concurrently.
- **Per-domain `DOMAIN_REFERENCE.md` knowledge skill files** — generated by `/wire:ads_knowledge-skill-generate` and colocated alongside dbt mart models. Includes a CI check template that flags when a model PR doesn't update the collocated reference file.
- **Eval suite as a first-class deliverable** — `/wire:ads_eval-suite-generate` produces YAML Q&A pairs per domain, a CI runner script, and per-domain accuracy thresholds. The launch gate blocks domains below threshold.
- **Analytics agent Wire skill** — `/wire:ads_agent-config-generate` produces an installable `SKILL.md` encoding three-tier routing (semantic → curated → raw fallback), built-in adversarial review, and provenance footer on every response.
- **Blog post** at `docs/blog-analytics-agent.md`.

---

## [3.7.2] - 2026-06-05

### Added

- **RudderStack as a recognised ingestion source + event tracker**, with MCP server connection (`https://mcp.rudderstack.com/mcp` via `mcp-remote` proxy, OAuth). New skill at `wire/skills/rudderstack/` covering MCP-driven workflows; complements the upstream `rudderlabs/rudder-agent-skills` plugin for CLI / Terraform / Typer surfaces.
- **Coupler.io as a recognised ingestion + reverse ETL tool**, with MCP server at `https://mcp.coupler.io/mcp/` (personal access token). New skill at `wire/skills/coupler-io/` covering dataflow management and the `data`-table query pattern.
- **Segment as a recognised ingestion source + event tracker**. No MCP server available; new skill at `wire/skills/segment/` documents driving the Segment Public API (`api.segmentapis.com` / `eu1.api.segmentapis.com` with a bearer token).
- **Airbyte as a recognised ingestion source**. Two surfaces documented separately in the skill: the Agent MCP at `https://mcp.airbyte.ai/mcp` (OAuth, agent-driven SaaS data fetching) and the Airbyte API at `api.airbyte.com/v1` (bearer token, deployment management — used by `ingestion-audit-generate`). New skill at `wire/skills/airbyte/`. Pairs with the upstream `airbytehq/airbyte-agent-sdk` plugin for agent-building patterns.
- **`migration.ingestion_tool` field** in the platform_migration status template, with valid values `fivetran` / `rudderstack` / `coupler-io` / `segment` / `airbyte` / `other`. Set during `/wire:new` for platform_migration releases.
- **Tool-aware branches in `ingestion_audit-generate`**: separate Step 2 sub-sections for Fivetran (default), RudderStack (MCP), Coupler.io (MCP), Segment (Public API), Airbyte (API), and Other (CSV import).
- **Jira integration: single-issue structure option.** New `jira_structure` dimension on the Jira setup question — `subtasks` (default, unchanged behaviour) or `single_issue`. Under `single_issue`, Wire creates one Task per artifact (no Sub-tasks) and transitions it through workflow states as commands run: **To Do** (created) → **In Progress** (generate complete) → **In Review** (validate pass) → **Done** (review approved). Failed validation or changes-requested review takes the Task back to **In Progress**. Pre-flight check in `jira_create.md` verifies the project's workflow supports those four states before scaffolding. Stored as `jira.structure: subtasks | single_issue` in status.md (defaults to `subtasks` for backwards compatibility).

### Changed

- `/wire:new` now asks six questions for platform_migration setup (was five) — added the ingestion tool question. The Jira setup question now offers three options (sub-tasks-per-command, single-issue-per-artifact, link-to-existing) instead of two.
- `wire/packaging/claude-plugin/.mcp.json` and the Gemini extension manifest now register `rudderstack`, `coupler-io`, and `airbyte` MCP servers alongside Atlassian, Fathom, and Context7.
- `wire/specs/utils/jira_sync.md` branches on `jira.structure`: under `single_issue`, transitions the single Task; under `subtasks`, transitions the relevant Sub-task (existing behaviour). The "In Review" state is now recognised by the flexible transition matcher (matches "In Review", "Review", "Code Review", "In QA", "QA", "Awaiting Review").
- All six status templates (`status-template.md`, `agentic-commerce-status-template.md`, `discovery-status-template.md`, `sop-discovery-status-template.md`, `migration/status_migration.md`, `custom-status-template.md`) now record `structure: subtasks` as the default in their `jira:` block.

### Fixed

- **Build script: the non-cowork skills copy was dropping skills.** The `cp -r` call was missing the `%/` trailing-slash strip, so each skill's *contents* were being copied into `dist/skills/` directly with each subsequent skill overwriting the previous one. The plugin dist now correctly contains 24 skill directories (was effectively one). v3.7.0 and v3.7.1 shipped with this bug — skills weren't actually reachable from the deployed plugin paths.

---

## [3.7.1] - 2026-06-05

### Fixed

- **`/wire:playbook-generate` no longer claims Wire "does not run audits" or "does not write Looker/dbt code".** Both are false — Wire's audit, `dbt-generate`, `semantic_layer-generate`, `dbt_migration-generate` and related commands write code and run audits. Replaced the misleading bullet in the playbook spec with a two-paragraph "What Wire does and does not do" section that accurately describes generation vs decision-making. Existing engagement playbooks need to be regenerated to pick up the new wording (`/wire:playbook-generate <release>`).

### Added

- **`examples/` worked translations bundled with each platform pair** at `wire/platform_pairs/<pair>/examples/`. Each example is a before/after pair of dbt model files plus a `notes.md` covering rationale, edge cases, and dbt-config impact. Currently shipped: 4 examples for BigQuery → Snowflake (UNNEST/FLATTEN, STRUCT/OBJECT_CONSTRUCT, date arithmetic, ML.PREDICT) and 3 examples for Snowflake → BigQuery. Used by `/wire:dbt_migration-generate` as few-shot context.
- **Per-engagement platform-pair override slot** at `.wire/engagement/platform_pair_overrides/<pair>/`. `migration_strategy-generate` and `dbt_migration-generate` now read engagement-level overrides on top of the canonical guide. Lets teams carry bespoke translations from one engagement to the next at the same client without modifying the framework. Documented in `wire/platform_pairs/README.md`.

---

## [3.7.0] - 2026-06-01

### Added

- **`platform_migration` release type** — full lifecycle migration of a data platform from one warehouse stack to another (BigQuery ↔ Snowflake initially). Adds 14 migration artifacts and 42 new commands across the audit, planning, build, validation, and cutover phases.
- Five parallel audit commands: `ingestion-audit`, `db_object-audit`, `security-audit`, `dbt-audit`, `orchestration-audit` (each with generate / validate / review).
- Planning artifacts: `migration_inventory`, `migration_strategy`, `target_setup`.
- Migration artifacts: `ingestion_migration`, `dbt_migration`, `orchestration_migration`.
- Validation loop: `equivalency` with `validate`, `investigate`, and `fix` sub-actions.
- Cutover and `migration_report` for the final deliverable.
- `utils-migration-audit-all` — runs all 5 source-platform audits in parallel via subagents to compress audit wall-clock time.
- Autopilot support for `platform_migration` releases with safety gates on `target_setup`, `ingestion_migration`, `orchestration_migration`, and `cutover`.
- Test suite under `wire/tests/platform_migration/` covering spec structure and feature detection.

### Changed

- `/wire:new` adds `Platform Migration` to the release-type picker.
- Plugin and Gemini extension manifests bumped to 3.7.0.












## [3.6.4] - 2026-05-26

### Added

- Five finance skills added; user guide renamed to WIRE_WORK_USER_GUIDE.md
- New skill: cowork-monthly-management-accounts (Xero P&L, balance sheet, Google Doc, Slack DM to Lewis)
- New skill: cowork-weekly-cash-debtors-pack (aged debtors, top-3 chase, draft emails, Slack DM)
- New skill: cowork-quarterly-revenue-concentration (concentration ratios, YoY movement, risk assessment)
- New skill: cowork-project-profitability-reconciliation (Harvest vs Xero effective day rate, underwater flag)
- New skill: cowork-vat-return-prep-checklist (16-item UK VAT pre-submission checklist)
- Renamed CLAUDE_COWORK_USER_GUIDE.md to WIRE_WORK_USER_GUIDE.md

## [3.6.3] - 2026-05-25

### Added

- Pipeline skill workspace-free; three new Cowork skills (daily briefing, delivery status, AI adoption)
- Pipeline deck mode generates HTML inline — no Python runtime or workspace required for text or deck output
- New skill: cowork-daily-briefing — context-aware daily briefing from Calendar, Gmail, Slack, Fathom, Drive
- New skill: cowork-client-delivery-status-report — SOW-anchored delivery status with Fathom, Slack, Atlassian
- New skill: cowork-weekly-ai-adoption-analysis — team AI adoption tracking with React dashboard

## [3.6.2] - 2026-05-25

### Added

- Wire Work plugin (wirework) — new separate Cowork plugin with 9 skills for sales, CEO, and engagement delivery
- cowork-rfp-assessment: replaced 6-dimension weighted scorecard with Orca/Tuna/Shark/Minnow ICP segmentation framework
- cowork-call-list: new skill for ranked daily call lists with talking points, calendar blocks, and follow-up drafts
- cowork-hubspot-sales-pipeline-weekly: new branded 5-slide pipeline deck replacing cowork-pipeline-report
- CLAUDE_COWORK_USER_GUIDE.md: new user guide covering all 9 Cowork skills
- Deal qualification user guide section: repositioned relative to RFP Assessment in the workflow

## [3.6.1] - 2026-05-24

### Added

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

## [3.5.13] - 2026-05-23

### Added

- /wire:start now asks Y/N to hand off to /wire:session-plan after showing the navigation summary
- Handoff skipped in onboarding, explanation, and lightweight session-start modes

## [3.5.12] - 2026-05-23

### Added

- USER_GUIDE session lifecycle section updated with /wire:start co-pilot description
- USER_GUIDE install confirmation line updated with full /wire:start capability description
- USER_GUIDE status.md section updated to describe /wire:start navigation and optional arguments

## [3.5.11] - 2026-05-23

### Added

- /wire:guide merged into /wire:start (plugin health check, onboarding, navigation, intent resolution)
- /wire:guide command and spec removed — reduces confusion about which entry point to use
- All internal references updated: help.md, wire-session-check.sh, CLAUDE.md, COMMANDS array

## [3.5.9] - 2026-05-22

### Added

- /wire:guide command with plugin health check (4 cases: not installed, outdated, current, legacy .dp/ structure), new-user onboarding, and navigational mode
- Session-start UserPromptSubmit hook outputs Wire project status on first prompt per repo per hour; fires from .claude/hooks/wire-session-check.sh installed by /wire:new
- Plugin CLAUDE.md first-message instruction covers users who have Wire installed but have not yet run /wire:new
- Wire-aware status line showing [Wire vX.Y.Z], active release, and context usage percentage
- Auto-approve Segment telemetry bash calls via permissions entry in claude-settings.json project template
- TEMPLATES directory now included in plugin distribution package (was silently excluded from the build)
- Fix: /wire:guide was missing from the COMMANDS array and therefore not generated as a slash command
- Fix: /wire:custom-define now writes command wrappers to .claude/commands/wire/ so they appear as /wire:<name> not /<name>
- /wire:migrate Case D: detect custom command wrappers in the wrong location and move them to .claude/commands/wire/ using git mv

## [3.5.8] - 2026-05-22

### Added

- Detect Wire custom command wrappers in .claude/commands/ that were written without the wire/ subdirectory namespace (pre-v3.5.7 behaviour)
- Move misplaced wrappers to .claude/commands/wire/ using git mv so they gain the /wire: prefix
- Chain Case D automatically after any other migrate case, and run standalone on already-migrated repos

## [3.5.7] - 2026-05-22

### Added

- Write custom command wrappers to .claude/commands/wire/ subdirectory so they get the wire: namespace prefix
- Update proposal table and activation notice to show /wire: prefix on custom commands

## [3.5.6] - 2026-05-22

### Added

- Add guide to COMMANDS array in build-packages.sh so /wire:guide is generated as a slash command

## [3.5.5] - 2026-05-22

### Added

- /wire:guide command — interactive co-pilot spec covering plugin health check, new-user onboarding, and navigational mode
- Session-start UserPromptSubmit hook outputs Wire project status on first prompt per repo per hour
- Plugin CLAUDE.md first-message instruction covers users without a Wire project yet
- Wire-aware status line showing plugin version, active release, and context usage percentage
- Auto-approve Segment telemetry calls via permissions in claude-settings.json template
- TEMPLATES now included in plugin distribution package

## [3.5.4] - 2026-05-17

### Added

- Add /wire:utils-doc-analyze for deliverable extraction from PDFs and project documents
- Add /wire:custom-release-define command with deliverable mapping, workflow-mismatch detection, and timeline seeding
- Add /wire:custom-feature-request for raising framework extension proposals
- User Guide Section 17 — Running a Custom Release; release type table updated (9 → 10); README release type counts and descriptions updated

## [3.5.3] - 2026-05-16

### Added

- /wire:adopt — onboard any in-flight project into Wire regardless of prior usage; assesses repo, Slack, HubSpot, Harvest, Jira, Confluence, and Fathom; generates a four-state adoption playbook and per-release delivery forecast
- utils/client_context — reusable multi-source external data gathering (Slack, HubSpot, Harvest, Jira, Confluence, Fathom) returned as a structured ClientContext object; callable by any Wire command
- utils/delivery_forecast — calculates % delivered per release via weighted checklist/Jira/Harvest composite, projects ETA using Fathom sprint velocity or burn-rate extrapolation, and compares against HubSpot contractual dates
- wire/scripts/release.sh — release automation script: bumps patch version, updates all changelogs and READMEs, pushes wiki, builds packages, pushes to wire-plugin and wire-extension repos, and raises a PR

## [3.5.2] — 2026-05-14

### Added

**`/wire:playbook-generate` — BPMN delivery playbook for any Wire release**

New planning utility command. Generates a `flowchart TD` BPMN-style Mermaid control-flow diagram followed by a narrative step-by-step guide. Extracts open questions, named owners, target dates, team members, and risks from completed artifacts; inserts decision gates for blocker OQs with chase-and-retry loops; emits parallel fork/join gateways for `sop_discovery` and other parallel-stream release types; applies classDef colouring (`wireCmd` / `offline` / `decision` / `gate` / `event`).

Does not create a tracked artifact in `status.md`. Writes to `.wire/releases/<release>/planning/<release_name>_playbook.md`. Syncs to Confluence if `confluence_page_id` is configured.

- `wire/specs/playbook/generate.md`
- Commands: **142** (was 141)

---

## [3.5.1] — 2026-05-14

### Changed

**Reverted `release_type: shape_up_discovery` → `discovery` for backwards compatibility**

The rename introduced in v3.5.0 broke existing engagements and muscle memory. The Shape Up discovery flow reverts to its original `release_type: "discovery"` identifier. All 12 Shape Up commands (`problem-definition-*`, `pitch-*`, `release-brief-*`, `sprint-plan-*`) are unchanged.

- `wire/specs/shape_up_discovery/` → `wire/specs/discovery/`
- `wire/TEMPLATES/shape-up-discovery-status-template.md` → `wire/TEMPLATES/discovery-status-template.md`

`/wire:migrate` Case C updated: now catches the briefly-used `shape_up_discovery` identifier and normalises it back to `discovery`.

---

## [3.5.0] — 2026-05-14

### Added

**`sop_discovery` release type — RA Canonical (SOP) discovery workflow**

A second discovery release type for engagements where the problem cannot yet be shaped — wide-ranging structured discovery leading to a go/no-go decision on a programme of work. Models the [Canonical Discovery Playbook (RA Standard)](https://rittmananalytics.atlassian.net/wiki/spaces/RA/pages/3436642306).

The canonical exit deliverable is the sponsor-facing **Findings Playback slide deck**. The playback meeting is the Wire review gate — the release is `approved` only when the 7-item **Sponsor Validation Checklist** is all-true (Maturity Curve pin, Hierarchy of Needs diagnosis, PPT diagnosis, Vision Statement, Solution Initiatives, preferred Delivery Option, conflicts resolved).

New commands (21):

- `engagement-brief-{generate,validate,review}` — 2-page internal RA scoping doc drawn from SoW + deal record
- `stakeholder-map-{generate,validate,review}` — P0/P1/P2 priority, influence/interest, sentiment, booking owners
- `stakeholder-interview-{generate,validate,review}` — **repeatable per stakeholder** (one file per interviewee); validate mechanically enforces the mandatory four-tag rule (`#<domain> #<type> #<hierarchy> #<ppt>`) on every theme bullet
- `requirements-matrix-{generate,validate,review}` — Discovery Requirements Matrix consolidating tagged themes from every interview
- `discovery-analyses-{generate,validate,review}` — the three analyses: Hierarchy of Needs, PPT, Maturity Curve, plus per-axis word clouds, quote bank, and MoSCoW/Phase layering
- `findings-playback-{generate,validate,review}` — the canonical sponsor-facing exit deliverable. Generate populates the bundled Claude Design HTML deck template (91 inline placeholders, `data-cond` flags). Review pulls the Fathom recording of the playback meeting and captures the Sponsor Validation Checklist.
- `delivery-roadmap-{generate,validate,review}` — Build / Pair / Coach options; feeds `/wire:release-spawn`

New supporting files:

- `wire/TEMPLATES/sop-discovery-status-template.md` — with `interviews: []` array and `sponsor_validation:` block (7 checklist booleans, Maturity pin, Vision Statement excerpt, Fathom URL, preferred Delivery Option)
- `wire/decks/findings_playback/` — Claude Design HTML deck handoff bundled with Wire (matches the existing `wire/decks/kickoff/` pattern)
- `wire/specs/sop_discovery/{7 artifact dirs}/{generate,validate,review}.md`

### Changed

**`/wire:kickoff` is now release-type aware**

Enriches from `problem_definition` / `pitch` / `sprint_plan` for `discovery` (existing behaviour), and from `engagement_brief` / `stakeholder_map` for `sop_discovery`. The SOP kick-off lands every stakeholder knowing whether they'll be interviewed, by whom, in which week, and what the exit deliverable will be.

**`/wire:migrate` gains Case C — release-type normalisation**

In-place migration for engagements using the briefly-used `shape_up_discovery` identifier → `discovery`. Idempotent re-run-safe.

**`/wire:status` sponsor_validation gate**

For `sop_discovery` releases, `/wire:release-spawn` cannot chain forward until `sponsor_validation.playback_held == true` AND every `sponsor_validation.checklist.*` is `true`. The playbook's failure-mode table is explicit that the recovery cost of skipping this is catastrophically higher post-build.

**USER_GUIDE.md** has a new "Discovery workflow (SOP / Canonical)" section walking through the full command sequence.

### Build

- Commands: **141** (was 119)
- Release types: **9** (was 8)

---

## [3.4.21] — 2026-05-12

### Fixed

**Plugin installation docs — missing `/reload-plugins` activation step**

User-facing install instructions across the framework documented "restart Claude Code" as the post-install activation step, but the correct action per the Claude Code docs is `/reload-plugins` (which picks up the install in the current session without a restart). Corrected in:

- `README.md` — root install snippet
- `USER_GUIDE.md` — §"Step 1: Install the plugin or extension" and §19 VS Code Extension install walkthrough
- `CLAUDE.md` — repo-level install summary (also removed the misleading "All commands work immediately after install — no setup step required" claim)
- `wire/README.md` — Claude Code Plugin section and publishing-tail install-command summary
- `wire/docs/enablement/wire_developer_quick_reference.md` — Installation block and troubleshooting row
- `wire-vscode/resources/WIRE_VSCODE_GUIDE.md` — marketplace install picker flow

### Changed

**dbt development skill — coding conventions refreshed**

`wire/skills/dbt-development/` updated to reflect current RA dbt conventions:

- **Directory structure** — models organised by entity group (`stg_core/`, `stg_entity/`, `int_core/`, `wh_core/`, `wh_entity_group/`, …) with `<layer>_<group>__<entity>.sql` file naming
- **Warehouse model types** — added `_xa` cross-attribute / bridge model alongside `_dim` and `_fact`
- **Field naming** — `_was_` boolean prefix added; revenue columns use `_amount` suffix; non-UTC timestamps now use middle-position timezone (`created_cet_ts` not `created_ts_cet`); `_dt` for dates; `_natural_key` example simplified to remove source-system prefix
- **Type casting** — must use `{{ dbt.type_string() }}` / `{{ dbt.type_numeric() }}` / `{{ dbt.type_boolean() }}` / `{{ dbt.type_timestamp() }}` / `{{ type_date() }}` macros, not raw SQL types
- **Field ordering** — new sequence: keys → attributes → indexes/ranks → metrics → booleans → temporal data types, with `{# keys #}` etc. Jinja comment markers grouping each block in staging models
- **PK/FK macro** — `dbt_utils.generate_surrogate_key` (older `surrogate_key` is deprecated in dbt_utils)
- **Schema YAML** — auto-generated; do not hand-create or hand-edit `schema.yml`
- **Documentation** — warehouse-layer columns must be documented; field descriptions centralised in `models/field_descriptions.md` as `{% docs %}` blocks referenced via `{{ doc('...') }}`; coverage can be enforced via dbt-meta-testing
- **Canonical staging-model example** updated in `SKILL.md`, `conventions-reference.md`, and `examples/staging-model-example.sql` to show the `s_<source>` / `rename_and_cast` / `final` CTE pattern with Jinja field-group markers
- **Canonical warehouse-model example** updated in `examples/warehouse-model-example.sql` to match the new entity-group naming, `_amount` revenue suffix, `was_*` booleans, and `dbt.type_*()` casting

**LookML content authoring skill — added layered architecture**

`wire/skills/lookml-content-authoring/SKILL.md` gains a new "RA Layered LookML Architecture" section describing the canonical five-layer refinement pattern:

- **base/** — generated LookML mapping directly to warehouse tables
- **staging/** — dimension refinements (labels, group labels, hide, parameters) via `+` view prefix
- **aggregate/** — measure refinements and new aggregate measures (with `_calculated` suffix for semantic-layer-only measures) via `+` view prefix
- **int/** — Explores with joins, `.explore.lkml` files
- **model/** — project connection, `.model.lkml` file

Includes file-naming conventions (`.layer.lkml`, `.explore.lkml`), refinement worked example, `include:` ordering rules (base first, then refinements), and a quick-reference table mapping common tasks to the right layer/file. The previous flat structure is preserved as "Legacy Project Structure (non-layered)" for working with older projects. Critical Rule §3 updated to point at the layered architecture and to call out layer-placement mistakes (e.g. don't put measures in the staging layer).

---

## [3.4.20] — 2026-05-11

### Changed

**Session lifecycle — replaced explicit commands with implicit state management**

Telemetry analysis across six Wire engagements showed that `/wire:session:end` was almost never invoked in practice, meaning session history was rarely written. The root cause: placing session lifecycle in explicit commands puts the burden on the user at the moments (start and end of sessions) when they are least likely to comply.

- **`/wire:session:start` — deprecated.** Context loading is now handled by the new **engagement-context skill**, which activates automatically whenever Claude detects a `.wire/` directory and has not yet established engagement context in the current conversation. No invocation required.

- **`/wire:session:end` — deprecated.** Session state is now written incrementally — each generate, validate, and review command automatically appends a session history row to `status.md` on completion. State is never lost if a consultant closes their session without an explicit close command.

- **`/wire:plan` — new optional command.** For consultants who want a structured 3–5 step session plan before starting work, this command provides the planning ritual that `session:start` previously offered — but as an on-demand tool, not a mandatory gate.

- **Skill self-logging — all SKILL.md files updated.** Every skill now appends an activation entry to `execution_log.md` as its first action. This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing regardless of whether work was triggered by an explicit command or an auto-activated skill.

- **`execution_log.md` spec extended** to document skill activation entry format and identifiers.

- **New `engagement-context` skill** added to `wire/skills/engagement-context/SKILL.md`.

Deprecation stubs remain at `wire/specs/session/start.md` and `wire/specs/session/end.md` explaining the change and migration path.

---

## [3.4.19] — 2026-05-06

### Fixed

**VS Code extension — release contents not displayed for releases with numbered artifact keys**

- `wire-vscode/src/readers/WireProjectReader.ts` — artifact-name regex broadened from `[a-z_]+` to `[a-z0-9_]+` in both the frontmatter parser (line 87) and the autopilot YAML-block parser (line 152). Without this, releases that use numbered discovery deliverable keys (e.g. `d01_business_structure_review`, `d10a_funnel_reporting_use_cases`) would parse to an empty artifacts map and the release would render in the tree with no contents underneath.

---

## [3.4.18] — 2026-05-05

### Added

**Wire Framework VS Code Extension** — published to VS Code Marketplace

- VS Code extension (`rittman-analytics.wire-framework`) now available via the VS Code Extensions marketplace — search "Wire Framework" and click Install
- New "Installing the VS Code Extension" section in `wire-vscode/resources/WIRE_VSCODE_GUIDE.md` with four step-by-step screenshots covering marketplace search, trust dialog, sidebar activation, and first-run via `/wire:new`
- Same install walkthrough added to `USER_GUIDE.md` section 19 (Wire Framework VS Code Extension)

---

## [3.4.17] — 2026-05-04

### Added

**Fivetran pipeline integration** — tool-aware pipeline commands

- `/wire:pipeline-generate`, `/wire:pipeline-validate`, `/wire:pipeline-review` rewritten as thin routers: read `pipeline_tool` from `status.md` and delegate to the appropriate tool-specific sub-spec
- `wire/specs/development/pipeline/fivetran/generate.md` — full Fivetran workflow: resolve destination group, idempotency check against existing connections, create connections via Fivetran MCP, configure schema/table/column sync, set sync frequency, trigger initial sync, write `pipeline_connections.md`
- `wire/specs/development/pipeline/fivetran/validate.md` — 7 checks per connection (setup state, last sync result, setup tests, table selection, PII column hashing, sync frequency, pause state) plus destination health check; produces PASS/FAIL report
- `wire/specs/development/pipeline/fivetran/review.md` — builds live connection summary from Fivetran MCP (`get_connection_details`, `get_connection_url`) for stakeholder sign-off
- `wire/specs/development/pipeline/dlt/` — generate/validate/review stubs for future dlt (data load tool) support
- `wire/specs/development/pipeline/airbyte/` — generate/validate/review stubs for future Airbyte support
- `wire/specs/utils/pipeline_tool_status.md` — tool-agnostic router utility: checks `pipeline_tool`, delegates to the right status utility, returns `healthy`/`degraded`/`unhealthy`; used by orchestration and deployment pre-flight checks
- `wire/specs/utils/fivetran_status.md` — Fivetran-specific connection health check; optionally triggers and polls sync completion
- `wire/skills/fivetran/SKILL.md` — activates for all Fivetran connection, destination, transformation, and webhook management tasks; covers all 78 Fivetran MCP tools

### Changed

- **`/wire:pipeline_design-generate`** — new Step 3 prompts selection of the pipeline replication tool (Fivetran / dlt / Airbyte / custom) as Design Decision PD-1, with a comparison table of cost model, connector coverage, infrastructure footprint, and manageability; uses Fivetran MCP to verify connector availability and required config fields at design time; writes chosen `pipeline_tool` to `status.md` so downstream commands route correctly without re-reading the design document
- **`/wire:orchestration-generate`** — calls `pipeline_tool_status` utility in Step 1 to warn if connections are unhealthy before wiring orchestration
- **`/wire:deployment-validate`** — pipeline connection health (`pipeline_tool_status`) is now a Critical pre-flight check; `unhealthy` result blocks deployment approval

### Fixed

- `wire/specs/development/pipeline/fivetran/generate.md` and `fivetran/validate.md` — `run_connection_setup_tests` demoted from primary health signal to supplementary check; `get_connection_details` (`setup_state`) is now the authoritative source; known MCP wrapper `400` error documented and handled gracefully

---

## [3.4.10] — 2026-04-29

### Added

**Kickoff deck** — three new engagement-level commands
- `/wire:kickoff-generate [release-folder]` — reads `engagement/context.md` and the SoW; populates the EDITMODE JSON block in the deck HTML template; optionally enriches with approved discovery artifacts when a release folder is supplied
- `/wire:kickoff-validate [release-folder]` — enforces JSON validity, array lengths (`slide6Problems` = 8, `slide8Outcomes` = 5, `slide12W*Items` = 6, `slide14Categories` = 4), count field bounds, and hex colour format
- `/wire:kickoff-review [release-folder]` — surfaces Fathom meeting context, presents slide-by-slide summary, collects reviewer feedback, and on approval provides headless Chrome PDF export command

**Deck template** (`wire/decks/kickoff/`)
- `Project Kickoff.html` — 253 KB blank template with default title photo as base64; EDITMODE block populated by the generate command
- `colors_and_type.css` — Google Sans loaded via CDN (`@import` from Google Fonts); Beatrice and local `.ttf` `@font-face` declarations removed; system-ui fallback declared
- `deck-stage.js`, `deck.css`, `mermaid.min.js` — vendored assets (offline rendering)
- `tweaks-panel.jsx`, `tweaks.example.json`, `CLAUDE.md` — LLM contract with full JSON schema, editing rules, and worked example
- SVG brand assets: `logo-black-blue.svg`, `logo-white-blue.svg`, `partner_logos.svg`, `people-process-technology.svg`, `google-cloud-partner-card.svg`

Hero video (`we-are-ra.mp4`, ~9.6 MB) excluded — replaced with a static RA branded interstitial slide.

**Discovery mode**: `engagementType` is set to `"Discovery"` automatically when `engagement_type` is `discovery` in `context.md`, switching deck slide wording to frame the kickoff as a discovery sprint opening.

**Status template**: `wire/TEMPLATES/discovery-status-template.md` updated with `kickoff_deck` artifact block.

**Consultant handbook**: Section 8 added — "Generating a Client Kick-off Deck" with full workflow, slide-by-slide content source table, re-run/merge behaviour, and PDF export instructions. Sections 8–23 renumbered to 9–24.

---

## [3.4.9] — 2026-04-29

### Added

**Agentic Commerce release type** (`project_type: agentic_commerce`)
- New specialised release type for building AI-powered ecommerce storefronts using Lovable, GitHub, Supabase, Google Cloud, and Stripe
- 27 new commands across 9 feature areas, namespaced `/wire:ac_*`
- Each feature follows the standard Wire lifecycle: generate → validate → review
- **`ac_storefront`** — guided Lovable prompt sequence for base scaffold (React 18 + Vite + Tailwind) + Shopify Storefront API + GitHub bidirectional sync
- **`ac_semantic_search`** — AI semantic search using Vertex AI Retail API, Algolia, or pgvector
- **`ac_conversational_assistant`** — multi-turn shopping assistant built on Google Cloud Retail API Conversational Search
- **`ac_virtual_tryon`** — photo upload + AI image generation via Lovable AI Gateway (Gemini Flash)
- **`ac_visual_similarity`** — "find similar" product discovery via Gemini multimodal embeddings
- **`ac_llm_tools`** — LLM with autonomous tool calling (Gemini 2.5 Flash function calling)
- **`ac_personalisation`** — user profiles, event tracking, and dynamic UX stored in Supabase/BigQuery
- **`ac_ucp_server`** — Universal Commerce Protocol merchant server with Stripe payments
- **`ac_demo_orchestration`** — automated demo flows with phase state machine and persona switching

**Supporting files**
- `wire/TEMPLATES/agentic-commerce-status-template.md` — lifecycle status template for Agentic Commerce releases
- `wire/docs/agentic_commerce/` — setup playbooks and prerequisites guide (GCP, Shopify, Supabase, Stripe, Lovable)

---

## [3.4.8] — 2026-04-14

### Added

**`looker-dashboard-mockup` skill** (`wire/skills/looker-dashboard-mockup/`)
- New skill for generating pixel-accurate, interactive Looker dashboard HTML mockups directly inside Claude Code
- Produces a single self-contained HTML file with Looker UI chrome (teal sidebar, header, filter pills, tab bar), Chart.js interactive charts, KPI stat cards, and data tables
- Bundled design system reference (`references/design-system.md`) with all CSS custom properties, component class patterns, Chart.js configs, and table markup — read verbatim before generating HTML
- Activates automatically when the user asks to mock up, prototype, or visualise a Looker dashboard

### Changed

**`/wire:mockups-generate` — Dashboard-First Mode replaces Lovable/getmock workflow**
- Removed dependency on `getmock.rittmananalytics.com` and the Lovable external prototyping service
- Dashboard-first mode now generates interactive Looker HTML mockups directly using the bundled `looker-dashboard-mockup` skill — no browser, no external account, no manual steps
- The command reads requirements, plans dashboard structure, reads the bundled design system reference, and generates complete self-contained HTML file(s) saved to `design/mockups/`
- Simultaneously generates `design/dashboard_visualization_catalog.csv` and `design/dashboard_spec.md` automatically — no Lovable prompt needed
- Standard mode (ASCII wireframes for non-dashboard-first projects) is unchanged

**`/wire:viz_catalog-generate` — Source description updated**
- Description updated to reflect that the CSV and markdown inputs now come from `/wire:mockups-generate` rather than a Lovable session

**User Guide** (`USER_GUIDE.md`)
- Section 12 (Dashboard-First Rapid Development) rewritten to describe the new automated HTML mockup workflow
- FAQ updated: removed "Do I need a Lovable account?" — replaced with "Do I need any external tools?" (answer: no)
- Autopilot FAQ updated: fully automated mockup generation replaces the two-mode wireframe/pause approach
- Version bumped to 3.4.8

### Migration

No `.wire/` structure changes in this patch. Existing `dashboard_first` projects with previously saved Lovable files can continue using `/wire:viz_catalog-generate` as before — the command accepts the same CSV and markdown inputs regardless of how they were produced.

Run `bash wire/scripts/build-packages.sh` and push updated packages.

---

## [3.4.3] — 2026-03-27

### Changed

**`/wire:migrate` — Case B: near-wire root-level repo migration**
- Extended `/wire:migrate` to handle engagement repos that evolved organically alongside the Wire framework with `releases/`, `context/`, and `artifacts/` at the repo root and no `.wire/` directory (e.g. `rittmananalytics/liberis-delivery`)
- Auto-detects the source layout: Case A (pre-v3.4.0 flat `.wire/`) or Case B (near-wire root-level structure)
- Case B migration workflow:
  - Creates a new git branch (`wire/migrate-YYYYMMDD`) before making any changes
  - Moves `context/` → `.wire/engagement/` (stakeholders, decisions, glossary, references all preserved)
  - Generates `.wire/engagement/context.md` by translating the YAML frontmatter from `context/engagement.md` and preserving all rich content
  - Moves `releases/` → `.wire/releases/` with folder names preserved
  - Reformats each release `status.md` to wire YAML frontmatter: maps deliverable table statuses (`draft`/`review`/`approved`) to wire generate/validate/review states; preserves the original deliverable table and session history in the body
  - Moves `artifacts/meetings/` → `.wire/engagement/calls/`; non-meeting artifacts (`notion/`, `slack/`, etc.) stay at root
  - Rewrites `CLAUDE.md` to wire v3.4+ conventions; legacy `.claude/commands/` preserved with a compatibility note
  - Commits all changes, pushes the branch, and opens a PR with a full change log and review checklist
  - Handles repos with no git remote or no `gh` CLI gracefully (local migration only with push instructions)

**`wire/packaging/claude-plugin/CLAUDE.md`**
- Updated `/wire:migrate` description to mention both cases and the new branch + PR behaviour

### Migration

No `.wire/` structure changes in this patch. Run `bash wire/scripts/build-packages.sh` and push updated packages.

---

## [3.4.2] — 2026-03-25

### Changed

**Wire Studio — engagement model**
- All user-facing "Release" labels updated to "Engagement" in menus, dialogs, buttons, and empty states to align with the v3.4.0 two-tier structure
- Users open and manage engagements (git repos with `.wire/` directories) rather than individual release folders

**Wire Studio — release switcher**
- New dropdown above the file explorer lists all `.wire/releases/` subfolders for the active engagement
- Selecting a release updates the file tree context and re-fetches the artifact workflow diagram for that release

**Wire Studio — workflow diagram bug fix**
- Fixed: opening a multi-release engagement left the artifact diagram empty because `fetchHistory` was called before releases were discovered
- Fix: release discovery now runs first (in the same `async` effect), passing the first release folder name to `fetchHistory`
- `fetchHistory` now also tries `.wire/releases/{id}/status.md` as a path candidate (v3.4+ engagement structure)
- Release dropdown change triggers an immediate `fetchHistory` re-fetch
- `onRefreshStatus` (View Status) now resolves the correct status.md path using `activeRelease`

### Migration

No `.wire/` structure changes. Wire Studio users: restart with `wire-studio update` to pick up the new build.

---

## [3.4.1] — 2026-03-24

### Changed

- **`/wire:autopilot`** — Complete redesign for the v3.4.0 engagement/releases structure. The command now runs a full discovery sprint (problem_definition → pitch → release_brief → sprint_plan) autonomously before any delivery work. Downstream delivery releases are identified from the sprint_plan output, created (spawned), and executed in sequence — each with the artifact set appropriate for its release type. No longer requires an upfront project type selection.
- **Root README** — Added problem statement, engagement/release model overview, and release type table at the top
- **Build script** — Removed 4 duplicate command registrations; updated autopilot description

### Migration

No structural changes to `.wire/` in this patch. Re-run `bash wire/scripts/build-packages.sh` and push updated packages to the plugin and extension repos.

---

## [3.4.0] — 2026-03-24

### Highlights

Wire v3.4.0 introduces the **engagement planning** model: a two-tier `.wire/` structure that separates engagement-wide context from individual delivery releases, adds a `discovery` release type based on the Shape Up methodology, and adds session lifecycle commands to improve continuity across working sessions.

### Added

**Two-tier engagement structure**
- `.wire/engagement/` — engagement-wide context (SOW, call transcripts, org charts, objectives)
- `.wire/releases/` — delivery releases (previously project folders directly under `.wire/`)
- `.wire/research/sessions/` — persisted research findings, auto-populated by the research persistence skill
- `engagement/context.md` — generated by `/wire:new`, captures client name, objectives, stakeholders, architecture, and working agreements

**Discovery release type** (`release_type: discovery`)
- 12 new commands covering the pre-delivery Shape Up planning cycle:
  - `/wire:problem-definition-generate|validate|review`
  - `/wire:pitch-generate|validate|review`
  - `/wire:release-brief-generate|validate|review`
  - `/wire:sprint-plan-generate|validate|review`
- `/wire:release:spawn` — creates downstream delivery release folders from an approved discovery release brief

**Session lifecycle commands**
- `/wire:session:start [release-folder]` — enters Plan Mode, scans release status and prior research, proposes a focused session plan
- `/wire:session:end [release-folder]` — records session accomplishments in `status.md` session history, suggests next focus

**Research persistence skill** (`skills/research/SKILL.md`)
- Auto-activates during technical research tasks
- Saves structured summaries to `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md`
- `session:start` automatically surfaces prior research on the same topic

**Migration command**
- `/wire:migrate` — migrates a pre-v3.4.0 flat `.wire/<folder>/` layout to the new two-tier structure; moves SOW files to `engagement/`, meeting notes to `engagement/calls/`, generates `engagement/context.md`; safe to re-run

**Wire Studio — Release terminology**
- All UI labels, dialog titles, button text, and tooltips updated from "Project" to "Release"
- `discovery` added as the first entry in the Release Type selector
- `Migrate Layout` command added to the command palette

**Consultant handbook**
- Complete rewrite of Sections 4–18 for v3.4.0 terminology and workflows
- New Section 7: Running a Discovery Release (Shape Up Planning)
- Updated worked examples, FAQ (8 new entries), and session lifecycle documentation

### Changed

- Release folder naming: sequential `01-client-name/` convention replaces `YYYYMMDD_client_name/` date prefix
- `status.md` now includes a `Session History` table (auto-populated by `session:end`)
- `engagement/` folder is the canonical location for SOW files and meeting transcripts; release folders contain only delivery artifacts
- Build script command count: 81 → 82

### Migration

Users with existing engagements using the old flat layout can migrate automatically:

```
/wire:migrate
```

See the consultant handbook FAQ for details.

---

## [3.3.2] — 2026-02-01

### Added

- **dbt Fusion Migration skill** (`skills/dbt-fusion/SKILL.md`): auto-activates when migrating dbt projects to the Fusion runtime; classifies errors into 4 categories and runs `dbt-autofix` first
- **dbt MCP Server skill** (`skills/dbt-mcp-server/SKILL.md`): auto-activates when setting up the dbt MCP server for Claude Code; covers local vs remote modes and credential security
- **dbt Analytics Q&A skill** (`skills/dbt-analytics-qa/SKILL.md`): auto-activates when answering business data questions against a dbt project; uses a 4-level escalation from Semantic Layer to manifest analysis
- **dbt DAG Visualisation skill** (`skills/dbt-dag/SKILL.md`): auto-activates when visualising dbt model lineage; generates Mermaid flowcharts using MCP get_lineage tools with fallbacks

---

## [3.3.1] — 2026-01-15

### Added

- **Dagster orchestration** (`specs/development/orchestration/`): full generate/validate/review workflow for Dagster and dbt Cloud orchestration layers
- **Dagster skill** (`skills/dagster/SKILL.md`): activates when creating or modifying Dagster assets, schedules, sensors, or components; covers assets-first pattern and dagster-dbt integration
- **Wire Studio orchestration support**: `orchestration` artifact added to the workflow graph and artifact catalog
- Three new commands: `orchestration:generate`, `orchestration:validate`, `orchestration:review`

---

## [3.3.0] — 2026-01-01

### Added

- **dbt Semantic Layer skill** (`skills/dbt-semantic-layer/SKILL.md`): MetricFlow semantic model authoring for dbt Core 1.6+; covers both latest (1.12+/Fusion) and legacy spec formats
- **dbt Unit Testing skill** (`skills/dbt-unit-testing/SKILL.md`): Model-Inputs-Outputs pattern, format selection, BigQuery caveats
- **dbt Migration skill** (`skills/dbt-migration/SKILL.md`): cross-platform migration (BigQuery, Snowflake, Databricks) and dbt version upgrades
- **dbt Troubleshooting skill** (`skills/dbt-troubleshooting/SKILL.md`): systematic diagnosis of dbt job failures and test errors

---

## [3.2.0] — 2025-12-01

### Added

- Wire Studio GKE runtime (`src/lib/runtime/gke-runtime.ts`): Kubernetes Jobs backed by PVCs for workspace isolation; file-server sidecar eliminates cold starts for file operations
- Wire Studio workspace lifecycle state machine: `provisioning → ready → busy → suspended / failed / deleting → deleted`
- `session:start` / `session:end` predecessor commands introduced as `/wire:start` project opener

### Changed

- Wire Studio: Docker runtime retained for local dev; GKE runtime used in production via `RUNTIME_BACKEND=gke`

---

## [3.1.0] — 2025-11-01

### Added

- Wire Studio initial release (`wire-web-ui/`): Next.js browser IDE for multi-user Wire command execution
- Artifact workflow graph (pan/zoom, PNG/JPEG/PDF export)
- Atlassian MCP integration: Jira Epic/Task/Sub-task hierarchy per project; Confluence search during reviews
- `dashboard_first` release type: seed data → mockup → real data refactor workflow

---

## [3.0.0] — 2025-10-01

### Added

- Wire Framework v3: Claude Code Plugin + Gemini CLI Extension distribution model
- 6-phase delivery lifecycle: Requirements → Design → Development → Testing → Deployment → Enablement
- 53 embedded commands (self-contained workflow specs, no install step)
- Fathom MCP integration: meeting transcript context surfaced during artifact reviews
- `seed_data`, `data_refactor`, `viz_catalog` artifact types for `dashboard_first` projects
- Telemetry via Segment (opt-out with `WIRE_TELEMETRY=false`)
- LookML Content Authoring skill (cloud and local/MCP variants)
- dbt Development skill with 3-layer naming conventions, sqlfluff integration, multi-source framework

---

## Version History

| Version | Date | Commands | Key Addition |
|---------|------|----------|-------------|
| 3.4.10 | 2026-04-29 | 119 | Kickoff deck: `/wire:kickoff-generate/validate/review` — SoW-driven kick-off presentation |
| 3.4.9 | 2026-04-29 | 116 | Agentic Commerce release type — 27 new `/wire:ac_*` commands |
| 3.4.8 | 2026-04-14 | 87 | Looker dashboard mockup skill; dashboard-first HTML mockup workflow |
| 3.4.3 | 2026-03-27 | 82 | `/wire:migrate` Case B: near-wire root-level repo migration |
| 3.4.1 | 2026-03-24 | 82 | Autopilot redesign: discovery sprint + multi-release execution |
| 3.4.0 | 2026-03-24 | 82 | Engagement planning, discovery release type, session lifecycle, `/wire:migrate` |
| 3.3.2 | 2026-02-01 | 79 | 4 new dbt agent skills |
| 3.3.1 | 2026-01-15 | 79 | Dagster orchestration |
| 3.3.0 | 2026-01-01 | 76 | dbt Semantic Layer, Unit Testing, Migration, Troubleshooting skills |
| 3.2.0 | 2025-12-01 | 65 | Wire Studio GKE runtime, workspace lifecycle |
| 3.1.0 | 2025-11-01 | 65 | Wire Studio initial release, Atlassian MCP |
| 3.0.0 | 2025-10-01 | 53 | Plugin/extension distribution model |
