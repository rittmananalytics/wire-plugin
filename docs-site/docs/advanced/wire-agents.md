---
sidebar_position: 2
title: Wire Agents
---

# Wire Agents: Specialist Subagents

**Introduced**: v3.8.6 (orchestrate command) → v3.9.2 (12 specialists + `/wire:delegate`) → v3.9.2 (14 specialists, adds `dashboard-mock-developer` and `mock-data-developer`) → v3.9.3 (migration generate commands auto-delegate to `migration-specialist`) → v3.9.5 (all 44 non-migration generate commands auto-delegate) → v3.9.6 (intra-batch parallelism for dbt migration — groups of ~5 models per agent) → v3.9.7 (post-execution hooks, stale artifact detection, Data Safety blocks on all migration specs)

Wire Agents replaces the single-agent pattern with thirteen named specialist agents, each with a focused skill set, dispatched by the `/wire:delegate` command.

The core insight: a single Claude Code agent doing requirements, dbt development, LookML authoring, data quality, and migration audits across a full engagement dilutes context and produces generic output. A specialist with a narrow brief — "your job is dbt models and nothing else" — operates with a much cleaner context and makes better decisions within its domain.

## The thirteen agents

| Agent | Domain |
|---|---|
| `discovery-analyst` | Requirements, workshops, all SOP discovery artifacts |
| `data-designer` | Conceptual model, pipeline design, standard-mode mockups and viz catalog |
| `dashboard-mock-developer` | Interactive HTML mockups for `dashboard_first` — iterates with user until approved, derives viz catalog and data model requirements |
| `mock-data-developer` | CSV seed data from approved viz catalog; manages data refactor from seeds to real client data |
| `pipeline-engineer` | Fivetran, Airbyte, dlt connector configuration |
| `dbt-developer` | Staging → integration → warehouse model generation |
| `semantic-layer-developer` | LookML views, explores, dashboards, ads/semantic_layer |
| `orchestration-engineer` | DAG authoring, scheduling, orchestration migration |
| `data-quality-engineer` | Schema tests, Droughty QA, field docs, UAT |
| `migration-specialist` | Full migration lifecycle — audits, inventory, strategy, cutover |
| `delivery-lead` | Deployment guides, training, kickoff, enablement |
| `agentic-data-stack-developer` | Canonical models, knowledge skills, agent configs, eval suites |
| `qa-agent` | Pure validator across all release types — no generation |

The `qa-agent` has no generation responsibility. It validates outputs from other agents and reports pass/fail with specific remediation actions.

### dashboard-mock-developer and mock-data-developer

These two agents activate exclusively for `dashboard_first` releases.

`dashboard-mock-developer` runs an explicit iteration loop — it generates the first HTML mock immediately from requirements, then invites changes (tiles, chart types, layout, new pages, filter dimensions) until you confirm approval. It then derives three artifacts the rest of the chain depends on: the viz catalog CSV, a data-content dashboard spec, and `data_model_requirements.md` (the distinct measures and dimensions with grain and calculation definitions).

`mock-data-developer` has two time-separated phases: seed data (CSV files with referential integrity and domain-realistic values, enabling `dbt seed && dbt run` without any client data) and data refactor (repoints staging models from seeds to real client sources once access is available, producing a written plan before touching any code).

## Auto-delegation on individual commands

Nothing changes for individual commands. When you run `/wire:dbt-generate` (or any generate/validate command), the main session automatically delegates to the appropriate specialist subagent. You see a brief "→ delegating to dbt-developer agent" message. The subagent executes and the result appears in the usual artifact location.

Review commands (`*-review`) always stay in the main session — they require your direct input.

## Batch delegation with `/wire:delegate`

```
/wire:delegate <release-folder>
```

Wire reads `status.md`, identifies all pending artifact work, groups it by agent type, computes a parallel/sequential execution plan, and presents it for your approval before spawning any subagents. A typical full-platform plan:

```
Step 1 (sequential):
  discovery-analyst → requirements-generate, workshops-generate

Step 2 (parallel, starts after step 1):
  2a  data-designer    → conceptual_model-generate, pipeline_design-generate
  2b  pipeline-engineer → pipeline-generate

Step 3 (multi-wave fan-out, starts after step 2):
  dbt-developer → data_model-generate, dbt-generate  [fan-out — see below]

Step 4 (parallel, starts after step 3):
  4a  semantic-layer-developer → semantic_layer-generate, dashboards-generate
  4b  data-quality-engineer    → data_quality-generate

Step 5 (sequential, starts after step 4):
  qa-agent → validate all artifacts from steps 1–4

Step 6 (sequential, starts after step 5):
  delivery-lead → deployment-generate, training-generate
```

The plan respects Wire's artifact dependency graph — requirements must be approved before any technical agent starts; dbt and dashboard work can proceed concurrently once design is done.

## Fan-out parallelism for large model sets

When any dbt layer has more than 5 models, `/wire:delegate` splits that layer's models into batches of 5 and runs one `dbt-developer` agent per batch in parallel. Layers are still sequential: all staging agents complete before integration starts, which completes before warehouse starts. Within each layer, every agent runs in parallel.

A release with 11 staging models and 9 warehouse models produces this fan-out for Step 3:

```
Wave 3a — Staging layer  (3 parallel agents):
  dbt-developer [staging 1/3]  →  stg_shopify__orders, stg_shopify__customers, ...
  dbt-developer [staging 2/3]  →  stg_netsuite__transactions, stg_netsuite__items, ...
  dbt-developer [staging 3/3]  →  stg_klaviyo__events, stg_klaviyo__campaigns, ...

Wave 3b — Integration layer  (1 agent, starts after Wave 3a):
  dbt-developer [integration 1/1]  →  int__customer_unified, int__order_financial, ...

Wave 3c — Warehouse layer  (2 parallel agents, starts after Wave 3b):
  dbt-developer [warehouse 1/2]  →  customer_dim, product_dim, orders_fct, ...
  dbt-developer [warehouse 2/2]  →  daily_revenue_fct, marketing_spend_fct, ...

Total dbt-developer agents: 6  (3 + 1 + 2)
```

Each agent receives a `task_scope` list — the specific models it should generate. It reads the same upstream artifacts as every other dbt agent but writes only the files in its scope. The orchestrating session merges `decisions.md` entries from all agents after each wave completes.

## Review gates remain human-in-the-loop

Delegation pauses before every `*-review` step:

```
[Release] Delegation paused at review gate.

Artifact: data_model
Status:   PASS WITH WARNINGS
Location: .wire/releases/[release]/artifacts/data_model/

Run /wire:data_model-review [release_folder] to conduct the stakeholder review.
Once approved, re-run /wire:delegate [release_folder] to continue.
```

Run the review manually, then re-run `/wire:delegate` to resume.

## The decisions.md convention

Each subagent appends non-obvious choices and rationale to `.wire/releases/{release}/decisions.md` as it works — grain choices, tool selections, modelling trade-offs. Downstream agents read it; so do human reviewers at the review gates. This creates a lightweight audit trail of architectural decisions that wouldn't otherwise be captured in the artifacts themselves.

## Local execution — no additional infrastructure

Wire Agents runs entirely on your workstation. Subagents are spawned using Claude Code's built-in Agent tool. They use your existing Claude Code API key — no additional keys, accounts, or managed agent services required.

## Autopilot and agents

`/wire:autopilot` calls `/wire:delegate` internally. When you run Autopilot, you are already using Wire Agents — the batch delegation and specialist routing happen automatically. Run `/wire:delegate` directly when you want to review and confirm the delegation plan before agents start.

## Roadmap

| Phase | Version | What ships |
|---|---|---|
| Phase 1 | v3.9–v3.9.7 (current) | 14 specialist agent definitions + local batch orchestration via `/wire:delegate`; all generate commands auto-delegate as of v3.9.5; intra-batch parallel agents for dbt migration in v3.9.6; migration reliability hooks and safety blocks in v3.9.7 |
| Phase 2 | v4.0 | Ticket-driven pull model — agents watch Jira/Linear for `ready_for_agent` issues and execute autonomously |
| Phase 3 | v4.1 | Agent-to-agent coordination via child tickets |
| Phase 4 | v4.2 | Named persistent agents with engagement-level expertise; a delivery-coordinator that takes a SoW and generates the full project plan autonomously |
