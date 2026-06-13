# Wire Agents

**Introduced**: v3.9  
**Status**: Phase 1 — Specialist agent definitions and local orchestration

Wire Agents replaces the single-agent pattern with twelve named specialist agents, each with a focused skill set, dispatched by the `/wire:delegate` command. A dbt agent that only knows dbt conventions. A QA agent that is a pure critic with no generation responsibility. A discovery analyst that works from Fathom transcripts without contamination from deployment concerns.

---

## The problem this solves

A single Claude Code agent doing requirements, dbt development, LookML authoring, data quality, and migration audits across a full engagement dilutes context and produces generic output. A specialist with a narrow brief — "your job is dbt models and nothing else" — operates with a much cleaner context and makes better decisions within its domain.

---

## The twelve agents

| Agent | Domain |
|---|---|
| `discovery-analyst` | Requirements, workshops, all SOP discovery artifacts |
| `data-designer` | Conceptual model, pipeline design, mockups, viz catalog |
| `pipeline-engineer` | Fivetran, Airbyte, dlt connector configuration |
| `dbt-developer` | Staging → integration → warehouse model generation |
| `semantic-layer-developer` | LookML views, explores, dashboards, ads/semantic_layer |
| `orchestration-engineer` | DAG authoring, scheduling, orchestration migration |
| `data-quality-engineer` | Schema tests, Droughty QA, field docs, UAT |
| `migration-specialist` | Full migration lifecycle — audits, inventory, strategy, cutover |
| `delivery-lead` | Deployment guides, training, kickoff, enablement |
| `agentic-data-stack-developer` | Canonical models, knowledge skills, agent configs, eval suites |
| `agentic-commerce-developer` | Lovable storefront, Shopify integration, all AC AI features |
| `qa-agent` | Pure validator across all release types — no generation |

Each agent is defined in `wire/agents/<agent-name>/AGENT.md`. The definition sets the agent's role, the Wire specs it runs, the skills it loads, its MCP requirements, and explicit out-of-scope declarations.

---

## Quick start

### 1. Run individual commands as normal

Nothing changes for individual commands. When you run `/wire:dbt-generate` (or any generate/validate command), the main session auto-delegates to the appropriate specialist subagent. You see a brief "→ delegating to dbt-developer agent" message. The subagent executes and the result appears in the usual artifact location.

Review commands (`*-review`) always stay in the main session — they require your direct input.

### 2. Batch delegate pending work

```bash
/wire:delegate [release-folder]
```

Wire reads `status.md`, identifies all pending artifact work, groups it by agent type, computes the parallel/sequential execution plan, presents it for your approval, and spawns local subagents.

### 3. Review gates remain human-in-the-loop

Delegation pauses before every `*-review` step. You receive a notification with the artifact location and the validate result. Run the review command manually, then re-run `/wire:delegate` to continue.

---

## How delegation plans work

The plan respects the Wire artifact dependency graph. Some work is sequential (requirements must be approved before any technical agent starts); some runs in parallel (dbt development and dashboard design can proceed concurrently once requirements are done).

A typical full-platform engagement plan:

```
Step 1:  discovery-analyst         →  requirements, workshops
Step 2a: data-designer             →  conceptual_model, pipeline_design, mockups  (parallel)
Step 2b: pipeline-engineer         →  pipeline (connectors)                        (parallel)
Step 3:  dbt-developer             →  data_model, dbt  (fan-out — see below)
Step 4a: semantic-layer-developer  →  semantic_layer, dashboards                  (parallel)
Step 4b: data-quality-engineer     →  data_quality                                (parallel)
Step 5:  qa-agent                  →  validate all artifacts from 1–4
Step 6:  delivery-lead             →  deployment, documentation, training
```

---

## Fan-out parallelism for large model sets

When a release has more than 5 dbt models in any single layer, `/wire:delegate` splits that layer across multiple agents running in parallel. Each agent receives a scoped list of models — its batch. Layers are still sequential: all staging agents complete before integration agents start, which complete before warehouse agents start. Within each layer, agents run in parallel.

The batch size is 5 models per agent, capped at 8 agents per layer. A project with 30 staging models and 15 warehouse models runs:

```
Step 3 (multi-wave fan-out):

  Wave 3a — Staging layer  (6 parallel agents):
    dbt-developer [staging 1/6]  →  stg_source_a__accounts, stg_source_a__contacts, ...
    dbt-developer [staging 2/6]  →  stg_source_b__orders, stg_source_b__order_items, ...
    ... (6 total, 5 models each)

  Wave 3b — Integration layer  (1 agent, starts after Wave 3a):
    dbt-developer [integration 1/1]  →  int__customer_unified, int__order_lifecycle

  Wave 3c — Warehouse layer  (3 parallel agents, starts after Wave 3b):
    dbt-developer [warehouse 1/3]  →  customer_dim, product_dim, ...
    dbt-developer [warehouse 2/3]  →  orders_fct, order_items_fct, ...
    dbt-developer [warehouse 3/3]  →  revenue_fct, churn_fct, ...

  Total dbt-developer agents: 10  (6 + 1 + 3)
```

The same fan-out logic applies to `semantic-layer-developer` (grouped by explore, batch size 3) and `migration-specialist` (grouped by source system, batch size 10).

---

## Agent definitions

Agent definitions live in `wire/agents/<name>/AGENT.md` and mirror the pattern of `wire/skills/<name>/SKILL.md`. Each definition contains:

- **Frontmatter**: `agent_id`, `model`, `description`, `specs` (Wire commands the agent runs), `skills` (skill files loaded into context), `mcp_requirements`, `output_contract` (status fields and file paths the agent writes)
- **Role**: system-prompt-level description of the agent's focus and constraints
- **What you always do**: non-negotiable behaviours
- **Acceptance criteria**: what "done" means for this agent's outputs
- **What this agent does not do**: explicit out-of-scope declarations

The build script bundles `wire/agents/` into the distributed plugin alongside skills and specs.

---

## Platform: local execution via Claude Code Agent tool

Wire Agents runs locally. Subagents are spawned using Claude Code's built-in Agent tool with `subagent_type` set to the agent's `agent_id`. They use your existing Claude Code API key — no additional keys, accounts, or managed agent services required.

Each subagent runs in its own context window. Shared state is the engagement filesystem: the git repo containing `.wire/`. Subagents read upstream artifacts from there and write their outputs back to the same tree.

**No data residency concerns** — all computation happens on your workstation, against your existing API endpoint configuration.

---

## decisions.md convention

Each subagent appends non-obvious choices and rationale to `.wire/releases/{release}/decisions.md`. This creates a lightweight audit trail of architectural decisions that wouldn't otherwise be captured in the artifacts themselves — grain choices, tool selections, modelling trade-offs. Downstream agents read it; so do human reviewers at the review gates.

---

## Roadmap

Phase 1 (v3.9, current): twelve specialist agent definitions and local batch orchestration via `/wire:delegate`.

Phase 2 (v4.0): ticket-driven pull model — agents watch Jira/Linear for `ready_for_agent` issues on a schedule and execute autonomously.

Phase 3 (v4.1): agent-to-agent coordination via child tickets; coordinator monitors dependency resolution.

Phase 4 (v4.2): named persistent agents with engagement-level expertise; `delivery-coordinator` takes a SoW and generates the full project plan autonomously.
