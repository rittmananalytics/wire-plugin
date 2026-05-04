# Wire Framework — Claude Code Plugin

This plugin provides the **Wire Framework**, an AI-accelerated delivery system for data platform engagements. It encodes 20+ years of analytics engineering methodology as executable workflow specifications, enabling an AI agent to produce production-grade artifacts across the full project lifecycle.

## Usage

All commands are available after installing and restarting Claude Code. Commands are namespaced under `/wire:*`:

```
/wire:start              — See all releases and available commands
/wire:new                — Create a new engagement or add a release
/wire:help [<command>]   — List all commands, or man-page help for one command
/wire:mcp [list|view|update|auth] [server]  — Manage MCP server connections
/wire:session:start      — Start a focused working session on any release
/wire:session:end        — Close a session and record what was accomplished
/wire:autopilot [sow]    — Autonomous end-to-end engagement: discovery sprint → all delivery releases
/wire:status <release>   — Check release status
```

### Session commands (universal — all release types)

```
/wire:session:start [release-folder]   — Enter Plan Mode, scan release state and research, propose session plan
/wire:session:end   [release-folder]   — Summarise session, update status.md, suggest next focus
```

### Kickoff deck commands

Run immediately after `/wire:new`. Primary source is the Statement of Work. Pass a release-folder argument to enrich with approved discovery artifacts.

```
/wire:kickoff-generate [release-folder]   — Build kick-off deck from SoW; enrich with discovery artifacts if available
/wire:kickoff-validate [release-folder]   — Check JSON structure and content completeness
/wire:kickoff-review   [release-folder]   — Internal review; on approval, instructs PDF export via headless Chrome
```

Set `engagementType: "Discovery"` automatically when engagement type is discovery — the deck frames the kickoff as a discovery sprint opening. Re-run with a release folder after discovery artifacts are approved to enrich the content.

Deck template: bundled with the plugin at `decks/kickoff/Project Kickoff.html` (also at `wire/decks/kickoff/Project Kickoff.html` in the Wire source repo). The generate command searches both locations automatically.

### Discovery release commands

```
/wire:problem-definition-generate <release>   — Generate structured problem framing
/wire:problem-definition-validate <release>   — Validate problem definition completeness
/wire:problem-definition-review <release>     — Review with stakeholders

/wire:pitch-generate <release>   — Generate 10-section Shape Up pitch
/wire:pitch-validate <release>   — Validate pitch structure and quality
/wire:pitch-review <release>     — Review pitch (betting table)

/wire:release-brief-generate <release>   — Formalise approved pitch as release brief
/wire:release-brief-validate <release>   — Validate brief against pitch
/wire:release-brief-review <release>     — Client sign-off

/wire:sprint-plan-generate <release>   — Generate sprint plan with point estimates
/wire:sprint-plan-validate <release>   — Validate points vs appetite budget
/wire:sprint-plan-review <release>     — Team review and approval

/wire:release:spawn <discovery-release>   — Create downstream delivery release folders
```

### Delivery commands

```
/wire:requirements-generate <release>   — Extract requirements from SOW
/wire:requirements-validate <release>   — Validate requirements
/wire:requirements-review <release>     — Stakeholder review

/wire:conceptual_model-generate <release>
/wire:data_model-generate <release>
/wire:dbt-generate <release>
/wire:semantic_layer-generate <release>
/wire:dashboards-generate <release>
... (and -validate/-review for each)
```

### Agentic Commerce commands

Commands for `project_type: agentic_commerce` releases — building AI-powered ecommerce storefronts via Lovable and GitHub.

```
/wire:ac_storefront-generate <release>              — Build base storefront via Lovable + GitHub sync
/wire:ac_storefront-validate <release>              — Pre-flight checklist verification (Shopify, cart, Supabase)
/wire:ac_storefront-review <release>                — Stakeholder sign-off on base storefront

/wire:ac_semantic_search-generate <release>         — Implement AI semantic search (Vertex AI / Algolia / pgvector)
/wire:ac_semantic_search-validate <release>         — Functional, performance, and resilience tests
/wire:ac_semantic_search-review <release>           — Demo and stakeholder approval

/wire:ac_conversational_assistant-generate <release>  — Build multi-turn shopping assistant chat interface
/wire:ac_conversational_assistant-validate <release>  — Conversation flow, intent detection, cart integration tests
/wire:ac_conversational_assistant-review <release>    — Demo and stakeholder approval

/wire:ac_virtual_tryon-generate <release>           — Add AI virtual try-on with photo upload and image generation
/wire:ac_virtual_tryon-validate <release>           — Try-on quality, timeout, retry, and error handling tests
/wire:ac_virtual_tryon-review <release>             — Demo and stakeholder approval

/wire:ac_visual_similarity-generate <release>       — Add "Find similar" product discovery via multimodal AI
/wire:ac_visual_similarity-validate <release>       — Similarity relevance, performance, and integration tests
/wire:ac_visual_similarity-review <release>         — Demo and stakeholder approval

/wire:ac_llm_tools-generate <release>               — Implement LLM with autonomous tool calling (function calling)
/wire:ac_llm_tools-validate <release>               — Tool call accuracy, reasoning quality, and resilience tests
/wire:ac_llm_tools-review <release>                 — Demo and stakeholder approval

/wire:ac_personalisation-generate <release>         — Build personalisation engine: profiles, event tracking, dynamic UX
/wire:ac_personalisation-validate <release>         — Profile storage, event logging, greeting, privacy (no PII) tests
/wire:ac_personalisation-review <release>           — Demo and stakeholder approval

/wire:ac_ucp_server-generate <release>              — Implement Universal Commerce Protocol merchant server
/wire:ac_ucp_server-validate <release>              — Discovery, checkout lifecycle, Stripe, idempotency, security tests
/wire:ac_ucp_server-review <release>                — Demo and stakeholder approval

/wire:ac_demo_orchestration-generate <release>      — Add automated demo flows with phase state machine
/wire:ac_demo_orchestration-validate <release>      — Phase progression, timer guards, and persona tests
/wire:ac_demo_orchestration-review <release>        — Live demo run-through and stakeholder approval
```

**Agentic Commerce spec location**: `wire/specs/agentic_commerce/`

**Dependency order**: `ac_storefront` must be approved before all other `ac_*` features. Features can otherwise be developed in parallel, though `ac_personalisation` enriches `ac_conversational_assistant` and `ac_semantic_search` when completed.

### Migration

```
/wire:migrate   — Migrate any engagement repo to Wire v3.4+ structure (auto-detects source layout)
```

Handles two cases: **(A)** pre-v3.4.0 flat `.wire/` layout — renames project folders to `releases/<name>/`, moves SOW and meeting files, generates `engagement/context.md`; **(B)** near-wire root-level repos (`releases/`, `context/`, `artifacts/` at root, no `.wire/`) — creates a new git branch, moves all content into `.wire/`, reformats `status.md` files to wire YAML frontmatter, updates `CLAUDE.md`, commits, pushes, and opens a PR. Safe to re-run.

### Engagement data

Engagement data is stored in `.wire/` using a two-tier structure:

```
.wire/
  engagement/        — Engagement-wide context (SOW, calls, org charts)
  releases/          — Delivery releases (01-discovery, 02-data-foundation, etc.)
  research/          — Persisted research findings (auto-populated by research skill)
```

This directory is created automatically when you run `/wire:new`.

## MCP Integrations

This plugin configures optional MCP servers for:
- **Atlassian** — Jira issue tracking and Confluence document search
- **Linear** — Linear issue tracking (alternative to Jira)
- **Fathom** — Meeting transcript context for reviews
- **Context7** — Library documentation lookups
- **Notion** — Document store for client artifact review (`https://mcp.notion.com/mcp`, HTTP, OAuth)

Authenticate via `/mcp` in Claude Code.

### MCP Management Command

`/wire:mcp` provides an interactive interface for managing MCP server connections without editing JSON manually:

```
/wire:mcp                  — Interactive menu
/wire:mcp list             — Table of all configured servers + Wire purpose
/wire:mcp view <server>    — Full details: URL, transport, which Wire commands use it
/wire:mcp update <server>  — Change the server URL (e.g. point Atlassian at a custom on-prem endpoint)
/wire:mcp auth <server>    — Guided re-authentication walkthrough with exact CLI commands
```

Server keys: `atlassian`, `linear`, `fathom`, `context7`, `notion`.

## Issue Tracking

Wire Framework supports **Jira** and **Linear** as issue trackers. Both are optional and additive — the framework works fully without either. When both are configured, they are synced in parallel.

**Jira** (via Atlassian MCP):
- `/wire:utils-jira-create <release>` — Set up Jira Epic + Tasks + Sub-tasks
- `/wire:utils-jira-sync <release> <artifact> <action>` — Sync one artifact step (called automatically)
- `/wire:utils-jira-status-sync <release>` — Full reconciliation (called by `/wire:status`)

**Linear** (via Linear MCP):
- `/wire:utils-linear-create <release>` — Set up Linear Project + Issues + Sub-issues
- `/wire:utils-linear-sync <release> <artifact> <action>` — Sync one artifact step (called automatically)
- `/wire:utils-linear-status-sync <release>` — Full reconciliation (called by `/wire:status`)

Both trackers store their keys in `status.md` under `jira:` and `linear:` frontmatter sections respectively. `/wire:new` will offer to set up either or both during project creation.

## Document Store

The Wire Framework optionally replicates generated artifacts to Confluence or Notion for client review:

- **Setup**: Configured during `/wire:new` (Step 9.5) — choose Confluence or Notion as the document store for the engagement.
- **On generate commands**: The generated artifact is automatically published or updated in the configured document store.
- **On review commands**: Reviewer comments and any edits made directly in the document store are surfaced as review context before feedback is gathered.
- **Confluence**: Uses the existing Atlassian MCP server (`https://mcp.atlassian.com/v1/sse`).
- **Notion**: Uses the Notion MCP server (`https://mcp.notion.com/mcp`).

Three utility commands support document store operations:
- `utils/docstore-setup` — Set up document store (Confluence/Notion) for a project
- `utils/docstore-sync` — Sync a generated artifact to the document store
- `utils/docstore-fetch` — Fetch document store content and comments for review

## User Guide

The full user guide is available at `USER_GUIDE.md`. It covers all six project types, worked examples, Wire Studio setup, Autopilot, and troubleshooting. Reference it when answering questions about how to run engagements.

## Wire Studio

Wire Studio is a web-based visual interface for the Wire Framework, available as an alternative to the CLI. Install it locally by running:

```
/wire:studio-install
```

This command checks prerequisites (Node.js 18+), downloads and builds Wire Studio, and installs a `wire-studio` CLI. After install, run `wire-studio start` to open at http://localhost:3000. No Docker required.

## Two-Tier Engagement Structure

Every Wire engagement uses a two-tier structure:

- **Engagement level** (`engagement/`): SOW, call transcripts, stakeholders, current-state architecture — context that belongs to the whole engagement, not any specific release.
- **Release level** (`releases/`): Scoped, time-boxed delivery units. Release types: `discovery`, `full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `dashboard_first`, `enablement`.

### Repo mode options

- **Combined** (default): `.wire/` lives directly in the client's code repo.
- **Dedicated delivery repo**: A separate repo for Wire artifacts; client code repo details stored in `engagement/context.md`.

### Discovery release type

The `discovery` release type represents the pre-delivery scoping phase (Shape Up methodology). Its artifact workflow:

```
Problem Definition → Pitch → Release Brief → Sprint Plan → Spawn delivery releases
```

A discovery release ends by running `/wire:release:spawn` to create the folder structure and status files for each planned downstream delivery release.

## Research Persistence Skill

The research persistence skill (`skills/research/SKILL.md`) auto-activates during technical research tasks:
- **Before research**: checks `.wire/research/sessions/` for prior findings on the same topic
- **After research**: saves structured summaries to `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md`
- Session:start automatically surfaces relevant prior research at the start of each working session

## Ad-hoc Development Skills

This plugin includes contextual skills that activate automatically when working outside of Wire commands:

- **dbt Development** (`skills/dbt-development/SKILL.md`): Activates when working with dbt models. Provides naming conventions, SQL style rules, testing patterns, and multi-source framework support.
- **LookML Content Authoring** (`skills/lookml-content-authoring/SKILL.md`): Activates when creating or modifying LookML views, explores, and dashboards.
- **LookML Content Authoring (MCP)** (`skills/lookml-content-authoring (local and mcp-server)/SKILL.md`): LookML authoring with Looker MCP server integration for live schema validation.
- **Looker Dashboard Mockup** (`skills/looker-dashboard-mockup/SKILL.md`): Activates when the user asks to mock up, prototype, or visualise a Looker dashboard. Generates pixel-accurate, interactive HTML mockups with full Looker UI chrome (teal sidebar, filter pills, KPI tiles), Chart.js charts, and data tables — no external tools required. Used automatically by `/wire:mockups-generate` for dashboard-first projects.

- **Dagster** (`skills/dagster/SKILL.md`): Activates when creating or modifying Dagster assets, schedules, sensors, or components. Covers the assets-first pattern, dagster-dbt integration, CLI usage, and Wire-specific group naming conventions.
- **Dignified Python** (`skills/dignified-python/SKILL.md`): Activates when writing or reviewing Python code. Enforces modern type syntax (3.10+ unions), LBYL exception handling, pathlib for file operations, Click CLI patterns, and clean module design.
- **dbt Fusion Migration** (`skills/dbt-fusion/SKILL.md`): Activates when migrating a dbt project from dbt Core to the Fusion runtime. Classifies errors into 4 categories (auto-fixable, guided, needs input, blocked), runs dbt-autofix first, and guides progressive resolution.
- **dbt MCP Server** (`skills/dbt-mcp-server/SKILL.md`): Activates when setting up the dbt MCP server for Claude Code. Covers local vs remote server modes, configuration templates for Wire projects, and credential security.
- **dbt Analytics Q&A** (`skills/dbt-analytics-qa/SKILL.md`): Activates when answering business data questions against a dbt project. Uses a 4-level escalation: Semantic Layer → modified compiled SQL → model discovery → manifest analysis.
- **dbt DAG Visualisation** (`skills/dbt-dag/SKILL.md`): Activates when visualising dbt model lineage. Generates Mermaid flowcharts using MCP get_lineage tools, manifest.json parsing, or direct code parsing as fallbacks.

These skills provide coding standards and validation rules as context, even when you are not running `/wire:*` commands.
