# Wire Framework — Claude Code Plugin

This plugin provides the **Wire Framework**, an AI-accelerated delivery system for data platform engagements. It encodes 20+ years of analytics engineering methodology as executable workflow specifications, enabling an AI agent to produce production-grade artifacts across the full project lifecycle.

## Session Start Behaviour

At the start of each new conversation (the user's first message), check whether `.wire/` exists in the current directory:

- **`.wire/` exists**: The project has a session-check hook configured. Do not duplicate its output — the hook fires automatically. If for any reason the hook did not fire, output: `[Wire] Run /wire:start to check project status and get next steps.`
- **No `.wire/` directory**: Output a single line before responding to the user's message: `Wire Framework is active — run /wire:start new to start a new engagement, or /wire:adopt if joining a project already in progress.`
- **`.wire/` exists but no releases**: Output: `[Wire] Engagement set up — no releases started yet. Run /wire:new to create your first release.`

Keep these messages to one line. Do not output them on subsequent turns in the same conversation — only on the first user message.

## Optional: Wire Status Line

Wire includes a status line script that replaces the default Claude Code status bar with a Wire-aware version showing plugin version, active release, and context usage:

```
[Wire v3.7.1] yourname@macbook:~/client-repo > halocollar-sales-dashboard ctx:42%
```

To install (one-time, per user):

```bash
# Copy the script from the Wire templates
cp ~/.claude/plugins/wire/TEMPLATES/wire-statusline.sh ~/.claude/wire-statusline.sh
chmod +x ~/.claude/wire-statusline.sh

# Add the statusLine config to your ~/.claude/settings.json:
# "statusLine": {
#   "type": "command",
#   "command": "sh /Users/YOUR_USERNAME/.claude/wire-statusline.sh"
# }
```

Replace `YOUR_USERNAME` with your macOS username (`whoami`). The script reads Wire version from the installed plugin manifest and the active release from `.wire/releases/` in the current directory — no additional configuration needed.

## Usage

All commands are available after installing and restarting Claude Code. Commands are namespaced under `/wire:*`:

```
/wire:start [new|resume|explain] — Session entry point and co-pilot: orients new users and surfaces the right next action
/wire:new                — Create a new engagement or add a release
/wire:help [<command>]   — List all commands, or man-page help for one command
/wire:mcp [list|view|update|auth] [server]  — Manage MCP server connections
/wire:session:start      — Start a focused working session on any release
/wire:session:end        — Close a session and record what was accomplished
/wire:autopilot [sow]    — Autonomous end-to-end engagement: discovery sprint → all delivery releases
/wire:delegate <release>     — Decompose pending work and dispatch to specialist local subagents
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

Wire supports two discovery release types — Shape Up (scoped problem-shaping) and SOP / Canonical (wide-ranging structured discovery with sponsor playback exit).

#### Discovery (Shape Up) (`release_type: discovery`)

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

/wire:release-spawn <discovery-release>   — Create downstream delivery release folders
```

#### SOP / Canonical discovery (`release_type: sop_discovery`)

Models the [Canonical Discovery Playbook (RA Standard)](https://rittmananalytics.atlassian.net/wiki/spaces/RA/pages/3436642306). The exit deliverable is the sponsor-facing **Findings Playback slide deck**; the playback meeting is the Wire review gate.

```
/wire:engagement-brief-generate <release>    — Internal RA scoping doc from SoW + deal record
/wire:engagement-brief-validate <release>
/wire:engagement-brief-review <release>      — Internal RA (Head of Delivery)

/wire:stakeholder-map-generate <release>     — P0/P1/P2 priority, influence/interest, sentiment
/wire:stakeholder-map-validate <release>
/wire:stakeholder-map-review <release>       — Sponsor confirms list

/wire:stakeholder-interview-generate <release> --stakeholder <slug>
                                              — Repeatable per stakeholder; pulls Fathom transcript
/wire:stakeholder-interview-validate <release> [--stakeholder <slug> | --all]
                                              — Enforces mandatory four-tag rule mechanically
/wire:stakeholder-interview-review <release> --stakeholder <slug>
                                              — Internal RA peer review

/wire:requirements-matrix-generate <release> — Consolidate tagged themes from every interview
/wire:requirements-matrix-validate <release>
/wire:requirements-matrix-review <release>   — Internal RA review

/wire:discovery-analyses-generate <release>  — The three analyses: Hierarchy + PPT + Maturity
/wire:discovery-analyses-validate <release>
/wire:discovery-analyses-review <release>    — HoD + peer consultant; challenges Maturity pin

/wire:findings-playback-generate <release>   — Populate the bundled HTML deck template
/wire:findings-playback-validate <release>
/wire:findings-playback-review <release>     — ⭐ The sponsor playback gate. Captures the
                                                7-item Sponsor Validation Checklist from
                                                the Fathom recording of the meeting.

/wire:delivery-roadmap-generate <release>    — Build / Pair / Coach options
/wire:delivery-roadmap-validate <release>
/wire:delivery-roadmap-review <release>      — Sponsor sign-off on Release 1 scope

/wire:release-spawn <discovery-release>      — Refuses to chain forward until the
                                                Sponsor Validation Checklist is all-true
```

**Mandatory four-tag rule**: every theme bullet on every stakeholder interview write-up carries one tag from each of four closed sets — `#<domain> #<type> #<hierarchy> #<ppt>`. `stakeholder-interview-validate` enforces this with a regex/parser check, not LLM judgement. The three analyses cannot run without it.

The kick-off uses the existing `/wire:kickoff-*` commands — release-type aware, enriches from `engagement_brief` + `stakeholder_map` for SOP discovery, and from `problem_definition` / `pitch` / `sprint_plan` for Shape Up.

### Delivery commands

```
/wire:requirements-generate <release>   — Extract requirements from SOW
/wire:requirements-validate <release>   — Validate requirements
/wire:requirements-review <release>     — Stakeholder review

/wire:conceptual_model-generate <release>
/wire:conceptual_model-validate <release>
/wire:conceptual_model-review <release>

/wire:pipeline_design-generate <release>
/wire:pipeline_design-validate <release>
/wire:pipeline_design-review <release>

/wire:data_model-generate <release>
/wire:data_model-validate <release>
/wire:data_model-review <release>

/wire:mockups-generate <release>
/wire:mockups-review <release>

/wire:pipeline-generate <release>
/wire:pipeline-validate <release>
/wire:pipeline-review <release>

/wire:dbt-generate <release>
/wire:dbt-validate <release>
/wire:dbt-review <release>

/wire:orchestration-generate <release>   — Generate orchestration layer; choose Dagster, dbt Cloud, or Airflow
/wire:orchestration-validate <release>   — Validate DAG/job config and dbt model coverage
/wire:orchestration-review <release>     — Review orchestration design with technical lead

/wire:semantic_layer-generate <release>
/wire:semantic_layer-validate <release>
/wire:semantic_layer-review <release>

/wire:dashboards-generate <release>
/wire:dashboards-validate <release>
/wire:dashboards-review <release>
```

### Droughty commands

Commands for `project_type: droughty` releases and for the optional Droughty phase within any delivery release. Droughty is a bottom-up schema-introspection toolkit: it reads the live warehouse and generates LookML base views, dbt tests, DBML diagrams, AI field descriptions, and data quality reports. It complements Wire's top-down document-driven workflow.

```
/wire:droughty-setup <release>       — Install Droughty (pinned version), generate profile.yaml
                                       and droughty_project.yaml from Wire context
/wire:droughty-introspect <release>  — Schema inventory: tables, columns, PK/FK coverage report
/wire:droughty-dbml <release>        — DBML entity-relationship diagram from live warehouse schema
/wire:droughty-docs <release>        — AI-generated field descriptions for all columns (OpenAI)
/wire:droughty-qa <release>          — LangGraph data quality agent report (OpenAI)
/wire:droughty-stage <release>       — Staging SQL + sources.yml from a BigQuery dataset (BigQuery only)
/wire:droughty-dbt-tests <release>   — Pattern-based schema.yml tests from deployed table schema
/wire:droughty-lookml <release>      — Base LookML views, explores, and measures from deployed tables
/wire:droughty-generate <release>    — Full Droughty phase in sequence (mode-aware: discovery or post-dbt)
```

**Droughty spec location**: `wire/specs/droughty/`

**Pinned version**: `wire/droughty/pinned_version.txt` — Wire repo owners update this file to refresh the pinned version; consultants re-run `/wire:droughty-setup --force` to install the new version.

**Droughty release type** (`release_type: droughty`): For engagements where the primary goal is schema introspection or warehouse audit. Two sub-modes:
- **Discovery / audit** — maps an existing warehouse: `introspect → dbml → docs → qa`. No dbt deployment needed. Use as a standalone release or as discovery evidence feeding into `problem-definition-generate`.
- **Post-dbt deploy** — generates the base layer from deployed dbt models: `dbt-tests → stage → lookml → docs → qa`. Precedes `/wire:semantic_layer-generate`, which extends the base views with business logic.

**LookML file organisation**: Droughty writes base views to `views/generated/`. Wire extensions (explores, refinements, business logic) go in `views/extended/` using LookML refinements. Never hand-edit `views/generated/` — it is regenerated on each `/wire:droughty-lookml` run.

**Droughty as an optional phase in delivery releases**: Add a Droughty release to any `full_platform` or `dbt_development` engagement by running `/wire:new` and selecting "Droughty" as the release type, or invoke the commands directly within any release after `dbt run`.

### Platform Migration release commands

Commands for `release_type: platform_migration` — full lifecycle migration of a data platform from one warehouse stack to another (BigQuery ↔ Snowflake).

**Source repository management** (new in v3.9.9):

```
/wire:migration-source-register <release> <source_type> <github_url>
    — Register a source repo by type (dbt | ingestion | reverse_etl | orchestration | security)
      and GitHub URL (repo root or /tree/<branch>/<subfolder> path); multiple types can be
      registered independently, including subfolders of a shared monorepo.

/wire:migration-source-refresh <release> [source_type]
    — Refresh local snapshot(s); omit source_type to refresh all registered sources.
```

**Audit zone** (read-only — no writes to any external system):

```
/wire:migration-audit-all <release>              — Fan out all five audit commands as parallel subagents

/wire:ingestion-audit-generate <release>         — Catalog Fivetran/Airbyte connectors (MCP or CSV fallback)
/wire:ingestion-audit-validate <release>
/wire:ingestion-audit-review <release>

/wire:db-object-audit-generate <release>         — Enumerate databases, schemas, tables, views, procedures
/wire:db-object-audit-validate <release>
/wire:db-object-audit-review <release>

/wire:security-audit-generate <release>          — Catalog roles, permissions, users, service accounts
/wire:security-audit-validate <release>
/wire:security-audit-review <release>

/wire:dbt-audit-generate <release>               — Catalog dbt models, classify by migration complexity
/wire:dbt-audit-validate <release>
/wire:dbt-audit-review <release>

/wire:orchestration-audit-generate <release>     — Catalog orchestration jobs, schedules, dependencies
/wire:orchestration-audit-validate <release>
/wire:orchestration-audit-review <release>

/wire:reverse-etl-audit-generate <release>       — Catalog reverse ETL syncs (Hightouch, Census, etc.)
/wire:reverse-etl-audit-validate <release>
/wire:reverse-etl-audit-review <release>

/wire:migration-inventory-generate <release>     — Synthesise all audits into phased migration catalogue
/wire:migration-inventory-validate <release>
/wire:migration-inventory-review <release>
```

**Migration zone** (writes to target platform; ⚠ = safety gate requiring explicit confirmation):

```
/wire:migration-strategy-generate <release>      — Translation approach, phases, Mermaid batch DAGs, rollback plan
/wire:migration-strategy-validate <release>
/wire:migration-strategy-review <release>

/wire:target-setup-generate <release>            — ⚠ Target warehouse DDL, schemas, roles, service accounts
/wire:target-setup-validate <release>
/wire:target-setup-review <release>

/wire:ingestion-migration-generate <release>     — ⚠ Migrate connectors to target via MCP (new connectors only)
/wire:ingestion-migration-validate <release>
/wire:ingestion-migration-review <release>

/wire:dbt-migration-generate <release> [--batch N] [--model name] [--select selector] [--exclude selector]
                                                 — Iterative per-model loop: translate → compile → run →
                                                   3-check equivalency (row count, schema, value sample) →
                                                   auto-fix → repeat up to 5× per model. Both platform MCPs
                                                   mandatory. Generates Mermaid batch DAG + acceptance pack.
/wire:dbt-migration-validate <release>
/wire:dbt-migration-review <release>

/wire:migration-acceptance-pack-review <release> [--batch N]
                                                 — Present batch acceptance pack for stakeholder sign-off.
                                                   Human-in-the-loop gate between batches.

/wire:orchestration-migration-generate <release> — ⚠ Recreate orchestration jobs on target platform
/wire:orchestration-migration-validate <release>
/wire:orchestration-migration-review <release>

/wire:reverse-etl-migration-generate <release>   — Migrate reverse ETL syncs to target platform
/wire:reverse-etl-migration-validate <release>
/wire:reverse-etl-migration-review <release>

/wire:lineage-generate <release>                 — Cross-platform lineage view (source → target mapping)

/wire:equivalency-validate <release>             — Full equivalency loop: 7 check types across all tables
/wire:equivalency-investigate <release> --object <name>
/wire:equivalency-fix <release> --object <name> --approach <description>

/wire:cutover-generate <release>                 — ⚠ Go-live runbook (point of no return)
/wire:cutover-validate <release>
/wire:cutover-review <release>

/wire:migration-report-generate <release>        — Post-migration record
/wire:migration-report-validate <release>
/wire:migration-report-review <release>
```

**Spec location**: `wire/specs/migration/`

**Dependency order**: all audit zone artifacts must be approved before `migration-inventory-generate`. All inventory → strategy → target-setup → ingestion-migration (with safety gate reviews) before `dbt-migration-generate`. `cutover-review` blocked until `equivalency_validation.checks_failing == 0`.

**Source repo setup** (recommended before running the first `dbt-migration-generate`): register each source type with `/wire:migration-source-register <release> <source_type> <github_url>` (e.g. `dbt`, `orchestration`, `ingestion` — each can be a different repo or a different subfolder of the same monorepo). Then run `/wire:migration-source-refresh <release>` to pull all snapshots at once, or `/wire:migration-source-refresh <release> dbt` to refresh a single type. The `dbt-migration-generate` command checks `migration_sources.dbt.last_refreshed` at Step 0b and warns if older than 24 hours.

**Iterative translation+equivalency loop** (v3.9.9+): each model in a batch goes through up to 5 translate-run-test iterations automatically with no mid-loop manual review prompts. Both source and target platform MCPs must be connected. After all models in a batch reach terminal state (PASSED or FAILED), an acceptance pack is generated and the `migration-acceptance-pack-review` gate activates.

**Mermaid batch DAGs** (v3.9.9+): `migration-strategy-generate` creates one Mermaid DAG file per batch in `artifacts/migration_strategy/`. Each DAG shows model states: grey = not started, orange = translated/in-progress, green = passed, red = failed. States update in-place as `dbt-migration-generate` processes each model.

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
- **Amplitude** — Product analytics: charts, dashboards, experiments, session replay, instrumentation, and taxonomy (`https://mcp.amplitude.com/mcp`, HTTP, OAuth)

Authenticate via `/mcp` in Claude Code.

## Companion Plugins

**Wire Work** (Claude Cowork) — sales intelligence, pipeline management, deal qualification, client meeting intelligence, and CRM workflow automation using live MCP connectors. Runs in Claude Cowork (claude.ai), not Claude Code.

```
/plugin marketplace add rittmananalytics/wirework-plugin
/plugin install wirework@rittman-analytics
```

Skills: pipeline report, deal qualification (MEDDIC), RFP assessment, call list, sales follow-up email, client meeting intelligence, stakeholder influence network, SOW generator, PSF validator.

**HubSpot Admin Skills** (Claude Code) — 32 slash commands for HubSpot CRM administration: deduplication, lifecycle stage cleanup, lead scoring setup, workflow automation, quarterly cleanup routines. Requires Python 3.10+ and a HubSpot private app token.

```
/plugin marketplace add tomgranot/hubspot-admin-skills
/plugin install hubspot-admin@hubspot-admin-skills
```

Source: https://github.com/TomGranot/hubspot-admin-skills (MIT licence)

### MCP Management Command

`/wire:mcp` provides an interactive interface for managing MCP server connections without editing JSON manually:

```
/wire:mcp                  — Interactive menu
/wire:mcp list             — Table of all configured servers + Wire purpose
/wire:mcp view <server>    — Full details: URL, transport, which Wire commands use it
/wire:mcp update <server>  — Change the server URL (e.g. point Atlassian at a custom on-prem endpoint)
/wire:mcp auth <server>    — Guided re-authentication walkthrough with exact CLI commands
```

Server keys: `atlassian`, `linear`, `fathom`, `context7`, `notion`, `amplitude`.

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
- **Confluence**: Uses the existing Atlassian MCP server (`https://mcp.atlassian.com/v1/mcp`).
- **Notion**: Uses the Notion MCP server (`https://mcp.notion.com/mcp`).

Three utility commands support document store operations:
- `utils/docstore-setup` — Set up document store (Confluence/Notion) for a project
- `utils/docstore-sync` — Sync a generated artifact to the document store
- `utils/docstore-fetch` — Fetch document store content and comments for review

## Pull Request Workflow

Every Wire engagement repo includes a `.github/pull_request_template.md` scaffolded by `/wire:new`. The template is Wire-aware: it references the release folder, artifacts changed, Wire commands run and next, and links to Jira/Linear issues.

To create a PR pre-populated from session artifacts:
- `/wire:utils-pr-create [release-folder]` — reads `execution_log.md` and `status.md` to fill in the PR body, then calls `gh pr create`

If the release folder is omitted, the command infers it from the most recently modified `status.md`.

## Wire Agents

Wire Agents (v3.9+) replaces the single-agent pattern with eleven named specialist agents dispatched by `/wire:delegate`. Each agent has a focused role, a bounded spec scope, and explicit out-of-scope declarations. Agents run locally as Claude Code subagents — no separate API key or managed agent service required.

**The eleven agents**: `discovery-analyst`, `data-designer`, `pipeline-engineer`, `dbt-developer`, `semantic-layer-developer`, `orchestration-engineer`, `data-quality-engineer`, `migration-specialist`, `delivery-lead`, `agentic-data-stack-developer`, `qa-agent`.

Agent definitions live in `wire/agents/<name>/AGENT.md` (bundled into the plugin). Each definition sets the agent's role, Wire specs it runs, skills it loads, MCP requirements, and output contract.

**Auto-delegation**: individual generate/validate commands automatically delegate to the appropriate specialist subagent when the agent definition is available. Review commands always stay in the main session.

**Batch delegation**:
- `/wire:delegate <release-folder>` — read `status.md`, compute parallel/sequential execution plan, dispatch to specialist local subagents

**How `/wire:autopilot` relates**: autopilot calls `/wire:delegate` internally. Run `/wire:delegate` directly to review and confirm the plan before subagents start.

**Review gates remain human-in-the-loop**: delegation pauses before every `*-review` step. Run the review command, approve, then re-run `/wire:delegate` to continue.

Full documentation: `wire/docs/AGENTS.md`

## User Guide

The full user guide is available at `USER_GUIDE.md`. It covers all six project types, worked examples, Autopilot, and troubleshooting. Reference it when answering questions about how to run engagements.

## Two-Tier Engagement Structure

Every Wire engagement uses a two-tier structure:

- **Engagement level** (`engagement/`): SOW, call transcripts, stakeholders, current-state architecture — context that belongs to the whole engagement, not any specific release.
- **Release level** (`releases/`): Scoped, time-boxed delivery units. Release types: `discovery`, `sop_discovery`, `full_platform`, `pipeline_only`, `dbt_development`, `dashboard_extension`, `dashboard_first`, `enablement`, `droughty`.

### Repo mode options

- **Combined** (default): `.wire/` lives directly in the client's code repo.
- **Dedicated delivery repo**: A separate repo for Wire artifacts; client code repo details stored in `engagement/context.md`.

### Discovery release types

Wire has two discovery release types. Both end by running `/wire:release-spawn` to create the folder structure and status files for each planned downstream delivery release.

**`discovery`** — Shape Up scoping flow:

```
Problem Definition → Pitch → Release Brief → Sprint Plan → Spawn delivery releases
```

Use when the problem to solve is reasonably understood and you need to shape a single bet.

**`sop_discovery`** — RA Canonical (SOP) discovery, modelled on the [Canonical Discovery Playbook (RA Standard)](https://rittmananalytics.atlassian.net/wiki/spaces/RA/pages/3436642306):

```
Engagement Brief → Stakeholder Map → Kick-off → Stakeholder Interviews (×N)
   → Requirements Matrix → Discovery Analyses (Hierarchy / PPT / Maturity)
   → Findings Playback Deck → Sponsor Playback (the gate)
   → Delivery Roadmap → Spawn Release 1 (or close as no-go)
```

Use when scope is unclear at SoW signature or a new analytical domain is being introduced. The canonical exit deliverable is the sponsor-facing **Findings Playback slide deck**, presented to the sponsor. The release is `approved` only when the 7-item **Sponsor Validation Checklist** (Maturity pin, Hierarchy diagnosis, PPT diagnosis, Vision Statement, Solution Initiatives, preferred Delivery Option, conflicts resolved) is all-true on the playback meeting notes.

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
