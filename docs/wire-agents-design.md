# Wire Agents — Design Document and Implementation Plan

**Status:** Proposal — for review  
**Prepared:** 2026-06-11  
**Author:** Mark Rittman, Rittman Analytics  
**Target release:** v3.9 (Phase 1) → v4.0 (Phase 2) → v4.1 (Phase 3) → v4.2 (Phase 4)

---

## 1. Problem Statement

Wire currently operates with a single Claude Code agent doing everything. One agent generates requirements, writes dbt models, authors LookML, validates data quality, and documents the engagement — context switching across six different specialist disciplines in a single session. The inevitable result: generic output, missed conventions, and agents that carry so much context they lose focus on the task at hand.

The Power Digital engagement demonstrated what's possible when you separate concerns. A BI agent, a schema agent, a catalog agent — each focused, each with deep domain context, each producing better output than a single generalist. That engagement ran concurrently with Wire's development and directly fed its thinking. The specialist agent pattern has now been validated under real multi-team, multi-tenant Snowflake/Looker conditions.

The goal is to bring that pattern into Wire as a first-class capability: named specialist agents with focused skills, orchestrated by a coordinator, evolving from local developer-laptop execution to autonomous cloud-hosted delivery.

---

## 2. Platform Foundation: Claude Managed Agents

This design is built on **Claude Managed Agents** (Anthropic, public beta since April 2026) rather than self-managed infrastructure (GKE, Docker Compose, etc.).

Key capabilities confirmed available as of June 2026:

| Capability | Status | Relevance |
|---|---|---|
| Multiagent orchestration | Public beta (May 2026) | Coordinator + parallel specialist agents |
| Scheduled agents (cron) | Public beta (June 9 2026) | Ticket-driven polling without managing a scheduler |
| Per-agent MCP connections | Available | Each agent gets its own Jira/Snowflake/BigQuery credentials |
| Shared filesystem across agents | Available | Agents read each other's Wire artifact outputs |
| Credential vaults | Public beta | Per-engagement auth without secrets in agent definitions |
| Self-hosted sandboxes | Public beta | Air-gapped / compliance scenarios |

**Hard constraint**: delegation is depth-1 only. A coordinator can spawn specialist agents; specialist agents cannot in turn spawn further agents via the API. Agent-to-agent coordination in Phase 3 routes through the coordinator or through Jira ticket creation — not through direct agent-to-agent API calls.

**Compliance note**: Claude Managed Agent sessions persist on Anthropic's servers (required for resumability and shared filesystem). Sessions are **not eligible for ZDR or HIPAA BAA**. Engagements with data residency requirements must use self-hosted sandboxes (public beta, requires request access) or restrict managed agents to non-client-data tasks only. This constraint should be surfaced in `/wire:new` when agent mode is selected.

**Pricing** (beta): standard Claude API token rates + $0.08/session-hour (idle waiting is free). Web search: $10/1,000 calls.

---

## 3. Agent Taxonomy

Eight specialist agents cover the full Wire delivery lifecycle. Each has a focused role, a bounded spec scope, and a specific set of skills it loads.

| Agent | Role | Wire specs in scope | Skills loaded |
|---|---|---|---|
| `dbt-developer` | Transform raw data into warehouse-ready models per Wire dbt conventions | `pipeline-*`, `data_model-*`, `dbt-*`, `droughty-dbt-tests`, `droughty-stage` | `dbt-development`, `droughty` |
| `lookml-developer` | Author and validate LookML views, explores, and measures | `semantic_layer-*`, `dashboards-*`, `droughty-lookml` | `lookml-authoring`, `droughty` |
| `dashboard-prototyper` | Design and validate visualisation catalogs and UI mockups | `mockups-*`, `viz_catalog-*`, `wireframe-*` | `lookml-authoring` |
| `migration-auditor` | Inventory and audit platform migration scope and risk | `migration/*-audit-*`, `ingestion_audit-*`, `db_object_audit-*`, `security_audit-*`, `orchestration_audit-*`, `dbt_migration-lint` | (none — warehouse MCP tools) |
| `qa-agent` | Validate all artifact types against Wire acceptance criteria | `*-validate` commands across all release types | `dbt-development`, `lookml-authoring` |
| `data-quality-agent` | Data quality validation, schema testing, field documentation | `data_quality-*`, `droughty-qa`, `droughty-docs`, `droughty-introspect` | `droughty` |
| `stakeholder-interviewer` | Gather, structure, and validate requirements from discovery sources | `requirements-*`, `workshops-*`, `problem-definition-*`, `pitch-*` | (none — synthesis from Fathom/docs) |
| `playbook-generator` | Generate delivery plans, kickoff materials, and engagement playbooks | `playbook-*`, `kickoff-*`, `delivery-plan-*`, `release-brief-*` | (none) |

The `qa-agent` is intentionally a pure critic — it has no generation responsibility. It validates outputs from other agents and reports pass/fail with specific remediation actions.

---

## 4. Architecture

### 4.1 Agent Definition Files

Each agent is defined in `wire/agents/<agent-name>/AGENT.md`. This mirrors the `wire/skills/<skill-name>/SKILL.md` pattern already established in Wire.

```
wire/agents/
  dbt-developer/
    AGENT.md
  lookml-developer/
    AGENT.md
  dashboard-prototyper/
    AGENT.md
  migration-auditor/
    AGENT.md
  qa-agent/
    AGENT.md
  data-quality-agent/
    AGENT.md
  stakeholder-interviewer/
    AGENT.md
  playbook-generator/
    AGENT.md
```

Each `AGENT.md` contains:

```markdown
---
agent_id: dbt-developer
model: claude-opus-4-8
description: <one-line role description>
specs:
  - pipeline-generate
  - data_model-generate
  - dbt-generate
  - droughty-dbt-tests
  - droughty-stage
skills:
  - dbt-development
  - droughty
mcp_requirements:
  - bigquery        # or snowflake — resolved at session time from engagement context
  - github
output_contract:
  writes_to_status:
    - artifacts.pipeline.generate
    - artifacts.data_model.generate
    - artifacts.dbt.generate
  writes_artifacts:
    - .wire/releases/{release}/artifacts/pipeline/
    - .wire/releases/{release}/artifacts/data_model/
---

# dbt Developer Agent

## Role

<System prompt: role description, constraints, conventions the agent always follows>

## Acceptance criteria for all outputs

<What "done" means for this agent's outputs — specific, testable>

## What this agent does not do

<Explicit out-of-scope — prevents scope creep>
```

The build script bundles `wire/agents/` into the plugin alongside skills and specs.

### 4.2 The Coordinator: `/wire:orchestrate`

A new top-level command that decomposes a release's pending work into typed task units and dispatches to specialist agents.

`/wire:autopilot` is updated to call `/wire:orchestrate` internally when agent mode is configured, preserving its "run everything with minimal input" UX.

### 4.3 Status Tracking

`status.md` gains an `agents` block (added by `/wire:upgrade` for existing releases):

```yaml
agents:
  mode: null          # null | local | managed
  coordinator_session: null
  last_orchestrated: null
  active_sessions: []
  completed_sessions: []
```

Each completed session records: `agent_id`, `session_id`, `task`, `started_at`, `completed_at`, `outcome` (pass/fail/partial), `artifacts_written`.

---

## 5. Implementation Phases

### Phase 1 — Specialist Agent Definitions and Local Orchestration (v3.9)

**Goal**: Each agent is better-focused than the current do-it-all approach. Coordinator dispatches work to specialist managed agents, runs parallelisable work in parallel. No new infrastructure beyond the managed agents API.

**Deliverables:**

1. `wire/agents/` directory with eight `AGENT.md` definitions
2. `/wire:orchestrate <release-folder>` command (spec at `wire/specs/orchestrate.md`)
3. Build script updated to bundle `wire/agents/` into the plugin
4. `/wire:upgrade` updated to add `agents` block to existing `status.md` files
5. `wire/docs/AGENTS.md` user guide section

**`/wire:orchestrate` workflow:**

```
Step 1: Read status.md — identify all pending artifact tasks
Step 2: Group into typed work units per agent type
Step 3: Check for parallelism — which agents can run concurrently
         (e.g. dbt-developer and dashboard-prototyper after requirements are done)
Step 4: Present work plan to user for approval:

  Orchestration plan — 20260210_acme_analytics

  Sequential:
    [1] stakeholder-interviewer  →  requirements-generate, workshops-generate

  Parallel (after step 1):
    [2a] dbt-developer           →  pipeline-generate, data_model-generate
    [2b] dashboard-prototyper    →  mockups-generate, viz_catalog-generate

  Sequential (after step 2):
    [3]  lookml-developer        →  semantic_layer-generate, dashboards-generate
    [4]  qa-agent                →  validate all artifacts from steps 1-3

  Estimated sessions: 4 sequential steps, 2 parallel. Proceed? (yes/no)

Step 5: Create managed agent sessions via Anthropic API
         — each session references the agent's AGENT.md as system prompt
         — each session mounts the shared engagement filesystem
         — coordinator streams events and updates status.md as sessions complete
Step 6: On completion, summarise outcomes and flag any failures for manual review
```

**Managed agents API usage in Phase 1:**

```python
# Coordinator creates sessions for each specialist agent
session = client.beta.sessions.create(
    agent=agent_registry["dbt-developer"],  # pre-registered agent ID
    environment_id=engagement_environment,   # shared filesystem per engagement
    title=f"{release_folder}:pipeline-generate",
)
```

Agent registration (`/wire:agents-setup <engagement-folder>`) is a one-time step per engagement that registers the eight agents with the API and stores their IDs in `.wire/engagement/agents.json`.

**What this gets immediately**: a dbt agent that only knows dbt conventions, with the full `dbt-development` SKILL.md loaded and no LookML or migration context polluting its context window.

---

### Phase 2 — Ticket-Driven Pull Model (v4.0)

**Goal**: Agents don't wait to be pushed work — they watch Jira for issues assigned to their type on a cron schedule and pull tasks autonomously. The consultant's role is setting up the project plan; agents execute.

**The critical dependency**: Jira issues must be agent-consumable. Wire's current Jira integration writes minimal tickets. Agent-consumable tickets require a richer schema.

**Agent-consumable Jira issue schema:**

```yaml
summary: "[dbt-developer] Generate pipeline artifact — 20260210_acme_analytics"
labels:
  - wire-agent
  - wire-agent-type:dbt-developer
  - wire-release:20260210_acme_analytics
description:
  agent_type: dbt-developer
  release_folder: 20260210_acme_analytics
  task: pipeline-generate
  context_pointer: .wire/engagement/context.md
  input_artifacts:
    - .wire/releases/20260210_acme_analytics/artifacts/requirements/requirements.md
    - .wire/releases/20260210_acme_analytics/artifacts/data_model/conceptual_model.md
  output_artifacts:
    - .wire/releases/20260210_acme_analytics/artifacts/pipeline/
  acceptance_criteria:
    - Pipeline spec covers all sources listed in requirements.md §3
    - All source tables have extraction frequency defined
    - Fivetran connectors specified where available
  status_field: wire_agent_status
```

Status flow: `backlog → ready_for_agent → claimed → in_progress → review_required → done | failed`

**Deliverables:**

1. `/wire:jira-agent-setup <release-folder>` — enriches a release's existing Jira issues with the agent-consumable schema above
2. Scheduled agent configuration — each agent type runs on a cron (e.g. every 15 minutes during working hours) via the Anthropic scheduled agents API
3. Agent claiming logic — when an agent's scheduled session fires, it queries Jira for `wire-agent-type:<this-agent>` + `status: ready_for_agent`, transitions the first unclaimed issue to `claimed`, executes, updates the issue with outcome
4. `/wire:agent-status` — queries the managed agents API and Jira to show all active agent sessions, their current tasks, elapsed time, and queue depth per agent type
5. Wire Studio: agent status panel in the sidebar (polls `/api/agents/status`)

**Atomic claiming**: two scheduled instances of the same agent type must not claim the same ticket. The Jira transition from `ready_for_agent → claimed` acts as an optimistic lock — if two agents attempt the transition simultaneously, only one succeeds (Jira enforces workflow transitions atomically). The losing agent backs off and queries for the next unclaimed issue.

---

### Phase 3 — Agent-to-Agent Coordination (v4.1)

**Goal**: An agent executing a task can identify that it needs output from a different specialist, creates a child Jira ticket addressed to that agent type, and continues with other available work while it waits.

**Design within the depth-1 constraint**: specialist agents cannot spawn sub-agents via the managed agents API (depth-1 only). The coordination mechanism is Jira tickets — a specialist agent creates a `ready_for_agent` ticket for another agent type, which the coordinator (on its next scheduled poll) picks up and dispatches. The coordinator remains the single point of orchestration.

**Handoff contract** (`wire/specs/utils/agent_handoff.md`):

Any agent spec can invoke the handoff utility to create a child ticket. The child ticket must include:
- `parent_issue_key` — the requesting agent's current issue
- `blocking: true` — signals the parent issue is waiting on this child
- Full agent-consumable schema (agent type, task, context pointer, acceptance criteria)

The coordinator's scheduled poll checks for newly completed child tickets and transitions their parent issues from `waiting_on_agent` back to `in_progress`.

**Guard rails:**
- Maximum child ticket depth: 2 levels. A child issue cannot itself create child issues — the coordinator enforces this by checking `parent_issue_key` depth before transitioning a child to `ready_for_agent`.
- Coordinator veto: child tickets created by specialist agents enter `pending_coordinator_review` status before `ready_for_agent`. The coordinator's scheduled session reviews and approves (or rejects with a comment) before the specialist picks it up.

**Deliverables:**

1. `wire/specs/utils/agent_handoff.md` — shared utility spec for creating typed child tickets
2. Coordinator spec updated with child-ticket monitoring loop
3. `status.md` agent block updated to track dependency graph: which sessions are waiting on which child sessions
4. `/wire:agent-status` updated to surface the dependency tree

---

### Phase 4 — Agent Identity and Expertise (v4.2)

**Goal**: Agents have persistent names and identities across projects. Expertise levels are assigned based on demonstrated performance. A project manager agent can take a scope document, generate a full Jira project plan, and the specialist agents execute it end-to-end.

**Agent identity:**

Each registered agent gets a persistent identity stored in `.wire/engagement/agents.json` and in a global agent registry at `.wire/agents/registry.json`:

```json
{
  "agent_id": "dbt-developer-042",
  "name": "Rosalind",
  "type": "dbt-developer",
  "expertise_level": "intermediate",
  "managed_agent_id": "agt_abc123",
  "registered_date": "2026-03-15",
  "engagements": ["20260210_acme_analytics", "20260310_barton_peveril"],
  "performance": {
    "tasks_completed": 47,
    "first_pass_approval_rate": 0.83,
    "mean_iterations_to_approval": 1.4
  }
}
```

**Expertise levels**: `junior → intermediate → senior → specialist`. Advancing requires sustained first-pass approval rate above threshold for a given skill set. Senior and specialist agents are loaded with more complex skills (e.g. a specialist dbt agent gets the multi-source, cross-database equivalency skills that a junior one doesn't receive).

**Project manager agent** (`pm-agent`): a new ninth agent type. Takes a scope document (SoW PDF, brief, or existing Wire `context.md`) and:
1. Generates a complete Jira project hierarchy (Epic → Tasks per artifact → Sub-tasks per agent step)
2. Labels all issues with the correct `wire-agent-type` labels
3. Sets `ready_for_agent` status on Phase 1 tasks
4. Monitors overall delivery progress and unblocks stalled agents

This is the long-term evolution of `/wire:orchestrate` — instead of running interactively on a developer's laptop, the PM agent runs as a persistent managed agent that owns full delivery orchestration.

**Deliverables:**

1. `wire/agents/registry.json` — global agent registry (committed to Wire repo, updated per engagement)
2. `/wire:agents-onboard <engagement-folder>` — assign named agents to a new engagement, set expertise levels, configure their managed agent API registrations
3. `/wire:agents-review <engagement-folder>` — generate a performance summary per agent for the completed engagement; propose expertise level changes
4. `pm-agent/AGENT.md` — project manager agent definition
5. `/wire:pm-generate <sow-file>` — PM agent takes a scope document, generates and populates the full Jira project plan

---

## 6. Wire Changes Summary

| Component | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|
| `wire/agents/` directory | New — 8 AGENT.md definitions | — | — | +pm-agent |
| `wire/specs/orchestrate.md` | New | Updated (cron mode) | Updated (child ticket monitoring) | Updated (PM agent calls) |
| `wire/specs/utils/agent_handoff.md` | — | — | New | — |
| `wire/TEMPLATES/status-template.md` | +agents block | +agent_sessions | +dependency_graph | +agent_identity |
| `wire/scripts/build-packages.sh` | Bundle wire/agents/ | — | — | +registry |
| `/wire:upgrade` | Adds agents block | Adds agent_sessions | Adds dependency_graph | Adds agent_identity |
| `/wire:jira-agent-setup` | — | New | Updated | Updated |
| `/wire:agent-status` | Basic (session list) | Queue depth + Jira | Dependency tree | Performance metrics |
| Wire Studio | Agent status panel (read-only) | Agent queue panel | Dependency graph view | Agent roster + performance |

---

## 7. Open Questions

1. **Engagement filesystem sharing**: the managed agents shared filesystem operates within a single session. For Phase 2 (agents operating across multiple scheduled sessions), how is the engagement filesystem persisted between sessions? Options: commit/push to the engagement git repo after each session (agents have git access); or use the managed agents memory store. Git is the cleaner audit trail.

2. **Credential vault scope**: are credential vaults per-agent, per-engagement, or per-consultant? Per-engagement is the right granularity (each client has its own Snowflake account, Jira workspace, etc.) but requires vault management as part of `/wire:new` and `/wire:agents-setup`.

3. **Agent definition versioning**: when Wire releases a new version with an updated `dbt-developer/AGENT.md`, do existing registered agents auto-update or pin to the version at registration time? Recommend: registered agents pin to the version at registration; `/wire:upgrade` prompts to re-register against the new definition.

4. **Coordinator availability**: in Phase 2, is the coordinator itself a managed agent running on a cron schedule, or is it still invoked manually by the consultant? Recommendation: manual invocation in Phase 2 (consultant runs `/wire:orchestrate` to kick off a batch), move to scheduled coordinator in Phase 3.

5. **Review gate placement**: Wire's current lifecycle has a human review step (`*-review` commands) after each generate+validate cycle. In an agent-driven workflow, where do these gates live? Recommendation: review gates remain human-in-the-loop by default in Phases 1-2. Phase 3 introduces an optional `auto_approve_on_pass: true` flag per artifact type in `context.md`, allowing agents to proceed without waiting when validation passes on first attempt.

---

## 8. Out of Scope (this proposal)

- Wire Studio infrastructure changes beyond the agent status panel (agent pods, persistent workspaces for agents — these run on Anthropic's infrastructure, not GKE)
- HIPAA/ZDR compliance scenarios — self-hosted sandboxes are the path but require Anthropic request access and a separate design
- Agent billing and chargeback per engagement — tracked as a future feature once managed agents pricing stabilises post-beta
- LLM provider agnosticism — this design is Claude-only; Gemini CLI support for the agent layer is a separate proposal

---

## 9. References

- [Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview)
- [Multiagent sessions](https://platform.claude.com/docs/en/managed-agents/multi-agent)
- [Scheduled agents](https://claude.com/blog/whats-new-in-claude-managed-agents) (June 9 2026)
- `wire/docs/engagement-planning-feature-brief.md` — prior feature brief format reference
- `powerdigital-delivery/agents/bi-agent/` — production implementation this design generalises
- GitHub issue #40 — Power Digital findings and Wire framework contributions
