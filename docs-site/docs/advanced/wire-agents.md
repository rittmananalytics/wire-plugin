---
sidebar_position: 2
title: Wire Agents
---

# Wire Agents: Specialist Subagents

**Introduced**: v3.8.6 (orchestrate command) → v3.9.0 (12 specialists + `/wire:delegate`)

Wire Agents replaces the single-agent pattern with twelve named specialist agents, each with a focused skill set, dispatched by the `/wire:delegate` command.

The core insight: a single Claude Code agent doing requirements, dbt development, LookML authoring, data quality, and migration audits across a full engagement dilutes context and produces generic output. A specialist with a narrow brief — "your job is dbt models and nothing else" — operates with a much cleaner context and makes better decisions within its domain.

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

The `qa-agent` has no generation responsibility. It validates outputs from other agents and reports pass/fail with specific remediation actions.

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

Step 3 (sequential, starts after step 2):
  dbt-developer → data_model-generate, dbt-generate

Step 4 (parallel, starts after step 3):
  4a  semantic-layer-developer → semantic_layer-generate, dashboards-generate
  4b  data-quality-engineer    → data_quality-generate

Step 5 (sequential, starts after step 4):
  qa-agent → validate all artifacts from steps 1–4

Step 6 (sequential, starts after step 5):
  delivery-lead → deployment-generate, training-generate
```

The plan respects Wire's artifact dependency graph — requirements must be approved before any technical agent starts; dbt and dashboard work can proceed concurrently once design is done.

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
| Phase 1 | v3.9 (current) | 12 specialist agent definitions + local batch orchestration via `/wire:delegate` |
| Phase 2 | v4.0 | Ticket-driven pull model — agents watch Jira/Linear for `ready_for_agent` issues and execute autonomously |
| Phase 3 | v4.1 | Agent-to-agent coordination via child tickets |
| Phase 4 | v4.2 | Named persistent agents with engagement-level expertise; a delivery-coordinator that takes a SoW and generates the full project plan autonomously |
