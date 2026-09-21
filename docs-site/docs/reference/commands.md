---
sidebar_position: 1
title: Commands Reference
---

# Commands Reference

Sooner or later on any engagement you will want to know exactly what Wire ran on your behalf, or you will want to run one step yourself rather than ask for it, and for either of those you need the names. This page is the catalogue of them. Every Wire command follows the pattern `/wire:<artifact>-<action> <release-folder>`, and every artifact has three lifecycle commands, `generate`, `validate` and `review`, except where noted in the tables below, so that once you know an artifact's name you can usually work out its commands without looking them up.

```
/wire:dbt-generate    20240115_barton_peveril_full_platform
/wire:dbt-validate    20240115_barton_peveril_full_platform
/wire:dbt-review      20240115_barton_peveril_full_platform
```

---

## You do not have to type any of these

**Since v4.0.0, on Claude Code.** Say what you want done and Wire works out which command that is, runs it, names it in the closing line of its report and stops where a decision is yours. This page therefore stays the reference for what each command does, and typing one always works, but knowing the catalogue by heart is no longer the price of entry. See [The Release Director Model](../advanced/release-director).

Two commands behave differently under it:

- **`/wire:start`** computes the next action as before, then offers to run it rather than only printing it. It still prints the command name, so that you learn it as you go. Under `orchestration.mode: manual` it prints and stops, exactly as in 3.x.
- **`/wire:delegate`** checks the release claim before dispatching, enforces the `budget` block in `status.md` (concurrent lanes, warehouse spend) and carries the lane contract in every dispatch.

---

## Session and management commands

Before any artifact can be generated a release has to exist, and once several releases are under way you will want to see where each one stands, hand work out to agents or close one down when it is finished. The commands in this table do that housekeeping, and they operate on the session or the engagement as a whole rather than on individual artifacts.

| Command | Description |
|---|---|
| `/wire:new` | Create a new release. Prompts for release type, client name, optional Jira/Linear/document store setup. Always the first command for a new engagement. |
| `/wire:start` | Load session context, show current engagement state and suggest the next action (and, in orchestrated mode, offer to run it). Run at the start of any session or whenever you're unsure what to do next. |
| `/wire:status [release]` | Show completion status across all active releases (or a specific release). Reconciles Jira/Linear state when integrations are configured. |
| `/wire:autopilot <release>` | Run all pending generate → validate cycles autonomously, answering its own review gates and pausing only at safety gates and validation failures. The unattended end of the range; for client work, direct the release instead. |
| `/wire:delegate <release>` | Build a parallel/sequential delegation plan across specialist subagents and dispatch it, within the release's budget and after resolving the release claim. Called internally by Autopilot and by the orchestrating session; run directly to review the plan before agents start. |
| `/wire:playbook-generate <release>` | Generate a visual BPMN-style delivery plan with dependency order, team assignments and target dates for the release. |
| `/wire:delivery-roadmap-generate <release>` | Generate a multi-release delivery roadmap across an entire engagement. |
| `/wire:archive <release>` | Mark a release as complete or cancelled, write a final status snapshot and optionally export a client-facing artifact package. |
| `/wire:release-spawn <release>` | Spawn one or more new delivery releases from an approved discovery release. Reads the discovery outputs to pre-populate the new release context. |
| `/wire:session-plan <release>` | Enter Plan Mode and propose a 3–5 step session plan in which every step names the Wire command or skill that performs it. Optional, and never required. |
| `/wire:work <release> [ticket]` | Work a ticket inside an existing release: read the release for what bears on it, refuse requests larger than a ticket, plan with a command per step, run only the approved plan, publish through the client's PR, then patch stale release documents and reconcile the record. The ticket is recorded as an iteration of the release. |
| `/wire:mcp [list/view/update/auth]` | Manage MCP server connections: list configured servers, view details, update URLs or guide re-authentication. |
| `/wire:help` | Display available commands for the current release type and phase. |
| `/wire:migrate <release>` | Migrate a release from an older Wire spec format to the current version. |
| `/wire:remove <release>` | Remove a release folder after confirming with the user. Irreversible, so it prompts for confirmation. |

---

## Discovery — Shape Up

If your engagement begins with a Shape Up discovery, the four artifacts below are what it produces: a problem definition, a pitch, a release brief and a sprint plan. Each has its own generate, validate and review commands, and together they feed directly into `/wire:release-spawn`, which reads them to create the delivery releases that follow.

| Artifact | Commands | What it produces |
|---|---|---|
| `problem-definition` | `generate` `validate` `review` | Structured problem statement: context, pain points, proposed data domains, named metrics |
| `pitch` | `generate` `validate` `review` | Shape Up pitch: problem, appetite, solution sketch, rabbit holes, no-gos |
| `release-brief` | `generate` `validate` `review` | Scoped release brief with success criteria, out-of-scope items and dependencies |
| `sprint-plan` | `generate` `validate` `review` | Sprint plan with task breakdown, effort estimates and delivery order |

```
/wire:problem-definition-generate 20240115_acme_discovery
/wire:problem-definition-validate 20240115_acme_discovery
/wire:problem-definition-review   20240115_acme_discovery
/wire:pitch-generate              20240115_acme_discovery
# ... and so on through sprint-plan
/wire:release-spawn               20240115_acme_discovery
```

---

## Discovery — SOP / Canonical

Where the discovery instead follows Rittman Analytics' canonical discovery methodology, the "SOP" discovery, the work is that of a structured engagement: structured interviews, a stakeholder map, discovery analyses, a findings playback deck and a sponsor validation checklist. The table below lists the artifacts and the commands behind each of them, and note that `workshops` has no validate step.

| Artifact | Commands | What it produces |
|---|---|---|
| `requirements` | `generate` `validate` `review` | Requirements document with business questions, data domains and success metrics |
| `requirements-matrix` | `generate` `validate` `review` | Traceability matrix mapping requirements to proposed artifacts |
| `stakeholder-interview` | `generate` `validate` `review` | Interview guide and structured notes for each stakeholder session |
| `stakeholder-map` | `generate` `validate` `review` | Stakeholder map with influence, interest and engagement approach |
| `workshops` | `generate` `review` | Workshop facilitation guide and output notes |
| `discovery-analyses` | `generate` `validate` `review` | Data analysis outputs surfaced during discovery |
| `findings-playback` | `generate` `validate` `review` | Findings playback deck for stakeholder presentation |
| `engagement-brief` | `generate` `validate` `review` | Engagement brief summarising scope, team, timeline and success criteria |

```
/wire:requirements-generate          20240115_acme_discovery
/wire:requirements-validate          20240115_acme_discovery
/wire:requirements-review            20240115_acme_discovery
/wire:stakeholder-interview-generate 20240115_acme_discovery
# ...
/wire:findings-playback-generate     20240115_acme_discovery
/wire:findings-playback-validate     20240115_acme_discovery
/wire:findings-playback-review       20240115_acme_discovery
```

---

## Design artifacts

Once the requirements are approved, the design phase turns them into a technical shape, and because that shape is needed whatever you go on to build, the design artifacts are shared across the `full_platform`, `pipeline_only`, `dbt_development` and `dashboard_first` release types. The one exception to the three-command pattern here is `viz_catalog`, which has a generate command only.

| Artifact | Commands | What it produces |
|---|---|---|
| `conceptual_model` | `generate` `validate` `review` | Entity-relationship diagram, domain definitions and grain decisions |
| `pipeline_design` | `generate` `validate` `review` | Source-system selection, ingestion tool choice (Fivetran/Airbyte/dlt/custom), connector config |
| `data_model` | `generate` `validate` `review` | Full dbt project structure design: staging schemas, integration layer, marts, naming conventions |
| `mockups` | `generate` `review` | Interactive HTML dashboard mockups with sample data |
| `viz_catalog` | `generate` | Catalogue of charts and visualisations referenced in mockups |

```
/wire:conceptual_model-generate 20240115_acme_full_platform
/wire:conceptual_model-validate 20240115_acme_full_platform
/wire:conceptual_model-review   20240115_acme_full_platform
/wire:pipeline_design-generate  20240115_acme_full_platform
# ...
```

---

## Development — pipeline and dbt

With the design approved, development is where the pipelines and models are built, and since not every release builds every one of them, the tables in this section add a column naming the release types each artifact belongs to.

| Artifact | Commands | Release types | What it produces |
|---|---|---|---|
| `pipeline` | `generate` `validate` `review` | `full_platform`, `pipeline_only` | Fivetran connector configs, Airbyte connection YAMLs or dlt pipeline scripts |
| `dbt` | `generate` `validate` `review` | `full_platform`, `pipeline_only`, `dbt_development` | Staging, integration and mart `.sql` and `.yml` files across all specified domains |
| `data_quality` | `generate` `validate` `review` | `full_platform`, `dbt_development` | Extended dbt schema tests, source freshness tests and a data quality report |
| `data_refactor` | `generate` `validate` `review` | `dashboard_first` | Refactored dbt models replacing seed data with real warehouse sources |
| `seed_data` | `generate` `validate` `review` | `dashboard_first` | CSV seed files matching the mockup data structure |

```
# Generate dbt models for the full platform
/wire:dbt-generate 20240115_acme_full_platform

# Validate runs dbt compile + dbt test
/wire:dbt-validate 20240115_acme_full_platform

# Review presents output for stakeholder sign-off
/wire:dbt-review   20240115_acme_full_platform
```

---

## Development — semantic layer and orchestration

The second half of development sits on top of the dbt models: the semantic layer that makes them queryable, the dashboards that present them and the orchestration that keeps them refreshed.

| Artifact | Commands | Release types | What it produces |
|---|---|---|---|
| `semantic_layer` | `generate` `validate` `review` | `full_platform`, `dbt_development`, `dashboard_extension` | LookML views and explores (Looker), or dbt Semantic Layer MetricFlow models |
| `dashboards` | `generate` `validate` `review` | `full_platform`, `dbt_development`, `dashboard_extension`, `dashboard_first` | LookML dashboard files and Looker dashboard tile definitions |
| `agents_schema` | `generate` `validate` `review` | `full_platform`, `dbt_development`, `dashboard_first`, `agentic_data_stack`, `bi_migration` (optional) | Publication of the release's metadata into the warehouse `AGENTS` schema through dbt Labs' Agents Schema: a deterministic plan detects the providers (dbt manifest, LookML, Omni, OSI, Sigma, skills), writes the pinned GitHub workflow, `agents.yml` and the skills, the consultant completes the warehouse guide, validate compares the warehouse against the plan (see [Agents Schema](../advanced/agents-schema)) |
| `dbtcharts` | `generate` `validate` `review` | `full_platform`, `dbt_development`, `dashboard_first` (optional) | dbt Charts dashboards, one per warehouse subject area, scaffolded from the dbt manifest and catalog, designed to the board brief (`--auto` for every area at once, `--subject-area` for one), validated and rendered by `dct` (see [dbt Charts Boards](../advanced/dbt-charts)) |
| `orchestration` | `generate` `validate` `review` | `full_platform`, `pipeline_only` | Dagster asset graph or dbt Cloud job configuration |

```
/wire:semantic_layer-generate 20240115_acme_full_platform
/wire:semantic_layer-validate 20240115_acme_full_platform
/wire:semantic_layer-review   20240115_acme_full_platform
/wire:orchestration-generate  20240115_acme_full_platform
```

---

## Testing and deployment

Finally, before anything reaches its users, the testing and deployment artifacts check the platform against what was asked for and take it live, together with the documentation and training that let the client run it once you have gone.

| Artifact | Commands | What it produces |
|---|---|---|
| `uat` | `generate` `review` | UAT test plan: test cases per domain with expected results and source system cross-references |
| `deployment` | `generate` `validate` `review` | Step-by-step deployment runbook with rollback procedures for each step |
| `documentation` | `generate` `validate` `review` | Technical documentation: data dictionary, model reference, source system notes |
| `training` | `generate` `validate` `review` | User training materials for data team, analyst and stakeholder personas |

```
/wire:uat-generate        20240115_acme_full_platform
/wire:uat-validate        20240115_acme_full_platform
/wire:uat-review          20240115_acme_full_platform
/wire:deployment-generate 20240115_acme_full_platform
# ...
/wire:training-generate   20240115_acme_full_platform
```

---

## Utility commands

What about the work that surrounds the artifacts, such as keeping Jira in step with the record or pulling in what was said on the last client call? Utility commands, prefixed `utils-`, handle the integrations and supporting operations, and two of them are called internally by the review commands, as the table notes, so you will rarely need to type those yourself.

| Command | Description |
|---|---|
| `/wire:utils-jira-create <release>` | Create the Jira hierarchy (Epic → Tasks → Sub-tasks) for a new engagement |
| `/wire:utils-jira-sync <release>` | Sync current artifact status to Jira |
| `/wire:utils-jira-status-sync <release>` | Full Jira reconciliation: fixes stale statuses and flags divergences |
| `/wire:utils-linear-create <release>` | Create the Linear hierarchy (Project → Issues → Sub-issues) |
| `/wire:utils-linear-sync <release>` | Sync current artifact status to Linear |
| `/wire:utils-linear-status-sync <release>` | Full Linear reconciliation |
| `/wire:utils-atlassian-search <query>` | Search Confluence for context (used internally by review commands) |
| `/wire:utils-docstore-setup <release>` | Configure Confluence or Notion as the document store for a release |
| `/wire:utils-docstore-sync <release>` | Publish generated artifacts to the configured document store |
| `/wire:utils-docstore-fetch <release>` | Retrieve reviewer comments from the document store as review context |
| `/wire:utils-meeting-context <release>` | Search Fathom for recent meetings and surface relevant context (used internally by review commands) |
| `/wire:utils-fathom-sync [--after date] [--before date] [--limit N] [--dry-run] [--no-findings]` | Pull new Fathom call transcripts for the engagement's client into `.wire/engagement/calls/`, with an analytical findings write-up per call. Runs automatically once per session if `fathom_sync.enabled`; see [Fathom Call Sync](../advanced/fathom-sync) |
| `/wire:utils-data-model-registry-setup` | Clone the private `wire-data-model-registry` repo to your machine, for RA staff with access; see [The Process and Data Model Registries](../advanced/registries) |
| `/wire:utils-run-dbt <release>` | Run dbt commands (compile, test, run) in the context of the release |
