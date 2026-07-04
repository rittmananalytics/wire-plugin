---
sidebar_position: 1
title: Commands Reference
---

# Commands Reference

All Wire commands follow the pattern `/wire:<artifact>-<action> <release-folder>`. Every artifact has three lifecycle commands — `generate`, `validate`, and `review` — except where noted below.

```
/wire:dbt-generate    20240115_barton_peveril_full_platform
/wire:dbt-validate    20240115_barton_peveril_full_platform
/wire:dbt-review      20240115_barton_peveril_full_platform
```

---

## Session and management commands

These commands operate on the session or engagement as a whole, not on individual artifacts.

| Command | Description |
|---|---|
| `/wire:new` | Create a new release. Prompts for release type, client name, optional Jira/Linear/document store setup. Always the first command for a new engagement. |
| `/wire:start` | Load session context, show current engagement state, and suggest the next action. Run at the start of any session or whenever you're unsure what to do next. |
| `/wire:status [release]` | Show completion status across all active releases (or a specific release). Reconciles Jira/Linear state when integrations are configured. |
| `/wire:autopilot <release>` | Run all pending generate → validate cycles autonomously, pausing at review gates and validation failures. |
| `/wire:delegate <release>` | Build a parallel/sequential delegation plan across specialist subagents and dispatch it. Called internally by Autopilot; run directly to review the plan before agents start. |
| `/wire:playbook-generate <release>` | Generate a visual BPMN-style delivery plan with dependency order, team assignments, and target dates for the release. |
| `/wire:delivery-roadmap-generate <release>` | Generate a multi-release delivery roadmap across an entire engagement. |
| `/wire:archive <release>` | Mark a release as complete or cancelled, write a final status snapshot, and optionally export a client-facing artifact package. |
| `/wire:release-spawn <release>` | Spawn one or more new delivery releases from an approved discovery release. Reads the discovery outputs to pre-populate the new release context. |
| `/wire:session-plan <release>` | Enter Plan Mode and propose a 3–5 step session plan. Optional — never required. |
| `/wire:mcp [list/view/update/auth]` | Manage MCP server connections: list configured servers, view details, update URLs, or guide re-authentication. |
| `/wire:help` | Display available commands for the current release type and phase. |
| `/wire:migrate <release>` | Migrate a release from an older Wire spec format to the current version. |
| `/wire:remove <release>` | Remove a release folder after confirming with the user. Irreversible — prompts for confirmation. |

---

## Discovery — Shape Up

Shape Up discovery produces a problem definition, a pitch, a release brief, and a sprint plan. These feed directly into `/wire:release-spawn` to create delivery releases.

| Artifact | Commands | What it produces |
|---|---|---|
| `problem-definition` | `generate` `validate` `review` | Structured problem statement: context, pain points, proposed data domains, named metrics |
| `pitch` | `generate` `validate` `review` | Shape Up pitch: problem, appetite, solution sketch, rabbit holes, no-gos |
| `release-brief` | `generate` `validate` `review` | Scoped release brief with success criteria, out-of-scope items, and dependencies |
| `sprint-plan` | `generate` `validate` `review` | Sprint plan with task breakdown, effort estimates, and delivery order |

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

SOP discovery follows Rittman Analytics' canonical discovery methodology: structured interviews, a stakeholder map, discovery analyses, a findings playback deck, and a sponsor validation checklist.

| Artifact | Commands | What it produces |
|---|---|---|
| `requirements` | `generate` `validate` `review` | Requirements document with business questions, data domains, and success metrics |
| `requirements-matrix` | `generate` `validate` `review` | Traceability matrix mapping requirements to proposed artifacts |
| `stakeholder-interview` | `generate` `validate` `review` | Interview guide and structured notes for each stakeholder session |
| `stakeholder-map` | `generate` `validate` `review` | Stakeholder map with influence, interest, and engagement approach |
| `workshops` | `generate` `review` | Workshop facilitation guide and output notes |
| `discovery-analyses` | `generate` `validate` `review` | Data analysis outputs surfaced during discovery |
| `findings-playback` | `generate` `validate` `review` | Findings playback deck for stakeholder presentation |
| `engagement-brief` | `generate` `validate` `review` | Engagement brief summarising scope, team, timeline, and success criteria |

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

Design artifacts are shared across `full_platform`, `pipeline_only`, `dbt_development`, and `dashboard_first` release types.

| Artifact | Commands | What it produces |
|---|---|---|
| `conceptual_model` | `generate` `validate` `review` | Entity-relationship diagram, domain definitions, and grain decisions |
| `pipeline_design` | `generate` `validate` `review` | Source-system selection, ingestion tool choice (Fivetran/Airbyte/dlt/custom), connector config |
| `data_model` | `generate` `validate` `review` | Full dbt project structure design: staging schemas, integration layer, marts, naming conventions |
| `mockups` | `generate` `validate` `review` | Interactive HTML dashboard mockups with sample data |
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

| Artifact | Commands | Release types | What it produces |
|---|---|---|---|
| `pipeline` | `generate` `validate` `review` | `full_platform`, `pipeline_only` | Fivetran connector configs, Airbyte connection YAMLs, or dlt pipeline scripts |
| `dbt` | `generate` `validate` `review` | `full_platform`, `pipeline_only`, `dbt_development` | Staging, integration, and mart `.sql` and `.yml` files across all specified domains |
| `data_quality` | `generate` `validate` `review` | `full_platform`, `dbt_development` | Extended dbt schema tests, source freshness tests, and a data quality report |
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

| Artifact | Commands | Release types | What it produces |
|---|---|---|---|
| `semantic_layer` | `generate` `validate` `review` | `full_platform`, `dbt_development`, `dashboard_extension` | LookML views and explores (Looker), or dbt Semantic Layer MetricFlow models |
| `dashboards` | `generate` `validate` `review` | `full_platform`, `dbt_development`, `dashboard_extension`, `dashboard_first` | LookML dashboard files and Looker dashboard tile definitions |
| `orchestration` | `generate` `validate` `review` | `full_platform`, `pipeline_only` | Dagster asset graph or dbt Cloud job configuration |

```
/wire:semantic_layer-generate 20240115_acme_full_platform
/wire:semantic_layer-validate 20240115_acme_full_platform
/wire:semantic_layer-review   20240115_acme_full_platform
/wire:orchestration-generate  20240115_acme_full_platform
```

---

## Testing and deployment

| Artifact | Commands | What it produces |
|---|---|---|
| `uat` | `generate` `validate` `review` | UAT test plan: test cases per domain with expected results and source system cross-references |
| `deployment` | `generate` `validate` `review` | Step-by-step deployment runbook with rollback procedures for each step |
| `documentation` | `generate` `validate` `review` | Technical documentation: data dictionary, model reference, source system notes |
| `training` | `generate` `validate` `review` | User training materials for data team, analyst, and stakeholder personas |

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

Utility commands are prefixed `utils-` and handle integrations and supporting operations.

| Command | Description |
|---|---|
| `/wire:utils-jira-create <release>` | Create the Jira hierarchy (Epic → Tasks → Sub-tasks) for a new engagement |
| `/wire:utils-jira-sync <release>` | Sync current artifact status to Jira |
| `/wire:utils-jira-status-sync <release>` | Full Jira reconciliation — fixes stale statuses and flags divergences |
| `/wire:utils-linear-create <release>` | Create the Linear hierarchy (Project → Issues → Sub-issues) |
| `/wire:utils-linear-sync <release>` | Sync current artifact status to Linear |
| `/wire:utils-linear-status-sync <release>` | Full Linear reconciliation |
| `/wire:utils-atlassian-search <query>` | Search Confluence for context — used internally by review commands |
| `/wire:utils-docstore-setup <release>` | Configure Confluence or Notion as the document store for a release |
| `/wire:utils-docstore-sync <release>` | Publish generated artifacts to the configured document store |
| `/wire:utils-docstore-fetch <release>` | Retrieve reviewer comments from the document store as review context |
| `/wire:utils-meeting-context <release>` | Search Fathom for recent meetings and surface relevant context — used internally by review commands |
| `/wire:utils-run-dbt <release>` | Run dbt commands (compile, test, run) in the context of the release |
