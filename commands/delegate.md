---
description: Decompose a release's pending work into typed tasks and dispatch to specialist local subagents
argument-hint: <release-folder>
---

# Wire Delegate Command

## Purpose

Read a release's `status.md`, identify all pending artifact work, group it into typed task units per specialist agent, present a parallel/sequential execution plan, and dispatch to Claude Code local subagents.

`/wire:autopilot` calls this command internally. Run it directly when you want to review and confirm the delegation plan before agents start executing.

Individual generate/validate commands also auto-delegate to the appropriate specialist subagent when their agent definition is available — `/wire:delegate` is the batch entry point for multiple pending tasks across agents.

## Usage

```bash
/wire:delegate 20260210_acme_analytics
/wire:delegate releases/01-discovery
```

## Prerequisites

- `.wire/releases/<release-folder>/status.md` exists
- Agent definitions exist at `wire/agents/<agent-name>/AGENT.md` (bundled with the Wire plugin under `agents/`)
- No API key or managed agent registration needed — subagents run on the same Claude Code session and API key

---

## Workflow

### Step 1: Read Release State

1. Resolve the release folder path (try `.wire/releases/<arg>`, then `.wire/<arg>`)
2. Read `status.md` frontmatter — extract:
   - `release_type`
   - `current_phase`
   - All `artifacts.*` entries with their generate/validate/review status values
3. Read `.wire/engagement/context.md` — extract `client_name`, `engagement_name`, warehouse type (`bigquery` or `snowflake`)

---

### Step 2: Identify Pending Work

From the artifacts status, extract all actions not yet at `complete` or `approved`:

- `not_started` → schedule for this delegation run
- `in_progress` → treat as pending (no active session tracking needed for local subagents)
- `blocked` → surface to user, do not schedule
- `failed` → surface to user with the last failure reason; ask whether to retry or skip

Group pending work by agent type using this mapping:

| Artifacts | Agent |
|---|---|
| `requirements`, `workshops`, `problem_definition`, `stakeholder_map`, `sop_discovery/*` | `discovery-analyst` |
| `conceptual_model`, `data_model`, `pipeline_design`, `mockups`, `viz_catalog` | `data-designer` |
| `pipeline`, `pipeline/fivetran/*`, `pipeline/airbyte/*`, `pipeline/dlt/*` | `pipeline-engineer` |
| `dbt`, `data_refactor`, `droughty/dbt-tests`, `droughty/stage` | `dbt-developer` |
| `semantic_layer`, `dashboards`, `ads/lookml_views`, `ads/semantic_layer`, `droughty/lookml` | `semantic-layer-developer` |
| `orchestration`, `migration/orchestration_audit`, `migration/orchestration_migration` | `orchestration-engineer` |
| `data_quality`, `uat`, `droughty/setup`, `droughty/introspect`, `droughty/docs`, `droughty/qa`, `droughty/dbml` | `data-quality-engineer` |
| `migration/*` (all except orchestration_audit/orchestration_migration) | `migration-specialist` |
| `deployment`, `kickoff`, `enablement/training_*`, `playbook` | `delivery-lead` |
| `agentic_data_stack/*` | `agentic-data-stack-developer` |
| `agentic_commerce/*` | `agentic-commerce-developer` |
| Any `*-validate` action once generate is complete | `qa-agent` |

Note: `qa-agent` is layered on top of primary assignments. When a generate action is complete, add the corresponding validate action to the `qa-agent` task list regardless of which agent generated it.

---

### Step 2.5: Decompose Large Task Sets into Parallel Batches (Fan-out)

For agent types that handle large sets of independent items within a natural execution layer, split the item list into per-layer waves where every batch within a wave runs in parallel. Layer sequencing is preserved: all agents in a wave must complete before the next wave starts.

#### Fan-out rules by agent type

**`dbt-developer`** — apply when any single layer has more than 5 models:

1. Enumerate all models from the data model artifact or `dbt_project.yml`.
2. Group by execution layer in order:
   - **Staging** (`stg_*`): all models in this layer are independent of each other.
   - **Integration** (`int__*`): depends on staging; models within integration are independent of each other.
   - **Warehouse** (`*_dim`, `*_fct`): depends on integration; models within warehouse are independent of each other.
   - **Seeds**: independent; co-batch with the first staging wave unless the seed count alone exceeds the threshold.
3. Within each layer, calculate: `batch_count = min(ceil(model_count / 5), 8)`. Only fan-out when `batch_count > 1` (i.e. the layer has more than 5 models).
4. Split the model list as evenly as possible across `batch_count` batches.
5. Name each agent instance: `dbt-developer [<layer> <i>/<n>]` — e.g. `dbt-developer [staging 1/2]`, `dbt-developer [staging 2/2]`.
6. Each batch agent receives a `task_scope` list: the specific model file names it should generate (see Step 6).

**`semantic-layer-developer`** — apply when LookML view or explore count exceeds 5:

- Group by explore (each explore with its dependent views is a natural batch).
- `batch_count = min(ceil(explore_count / 3), 6)`.
- Name: `semantic-layer-developer [explores <i>/<n>]`.

**`migration-specialist`** — apply when source table or object count exceeds 10:

- Group by source system or schema.
- `batch_count = min(ceil(table_count / 10), 8)`.
- Name: `migration-specialist [<source-system> <i>/<n>]`.

For all other agent types, do not fan-out — their work is contextually coupled and batching offers no benefit.

#### Updating the execution plan

When fan-out applies to a step, replace the single agent line with a multi-wave block. Waves within the step are sequential; agents within a wave are parallel.

---

### Step 3: Compute Execution Plan

Determine which agent tasks can run in parallel and which must be sequential, based on these dependency rules:

**Hard dependencies (downstream cannot start until upstream is complete):**

1. `discovery-analyst` → requirements must be approved before any technical agent starts
2. `data-designer` → pipeline_design and data_model must be complete before `dbt-developer` starts
3. `pipeline-engineer` → pipeline connectors must be complete before `dbt-developer` starts on staging models
4. `dbt-developer` → dbt generate must be complete before `semantic-layer-developer` and `data-quality-engineer` start
5. `semantic-layer-developer` → semantic_layer generate must be complete before `qa-agent` validates it
6. All generate actions must be complete before `delivery-lead` starts deployment/documentation

**Can run in parallel (no dependency between them):**

- `data-designer` (conceptual_model, mockups, viz_catalog) and `pipeline-engineer` can start concurrently once requirements are approved
- `data-quality-engineer` and `semantic-layer-developer` can run concurrently once `dbt-developer` is complete
- `qa-agent` validate tasks can run as soon as their corresponding generate is complete — do not wait for all generates to finish

Format the plan as a numbered sequence with parallel steps as lettered sub-steps. When fan-out applies to a step, use a multi-wave block inside that step — waves are sequential, agents within each wave are parallel:

```
Delegation plan — [engagement_name] / [release_folder]
──────────────────────────────────────────────────────

Step 1 (sequential):
  discovery-analyst → requirements-generate, workshops-generate
  Subagent: discovery-analyst

Step 2 (parallel, starts after step 1):
  2a  data-designer    → conceptual_model-generate, pipeline_design-generate, mockups-generate
  2b  pipeline-engineer → pipeline-generate (connectors)
  Subagents: 2 parallel

Step 3 (multi-wave fan-out, starts after step 2):

  Wave 3a — Staging layer  (2 parallel agents):
    dbt-developer [staging 1/2]  → stg_source_a__entity_x, stg_source_a__entity_y, ...
    dbt-developer [staging 2/2]  → stg_source_b__entity_a, stg_source_b__entity_b, ...
  
  Wave 3b — Integration layer  (1 agent, starts after Wave 3a):
    dbt-developer [integration 1/1]  → int__unified_entity
  
  Wave 3c — Warehouse layer  (2 parallel agents, starts after Wave 3b):
    dbt-developer [warehouse 1/2]  → entity_dim, summary_fct, ...
    dbt-developer [warehouse 2/2]  → detail_fct, history_fct, ...
  
  Total dbt-developer agents: 5  (2 + 1 + 2)

Step 4 (parallel, starts after step 3):
  4a  semantic-layer-developer → semantic_layer-generate, dashboards-generate
  4b  data-quality-engineer    → data_quality-generate
  Subagents: 2 parallel

Step 5 (sequential, starts after step 4):
  qa-agent → validate all artifacts from steps 1–4

Step 6 (sequential, starts after step 5):
  delivery-lead → deployment-generate, documentation-generate, training-generate

Total: [N] steps, [N] with parallelism. Blocked items: [list any blocked artifacts]
```

If there are no pending items, output:
```
No pending work found for [release_folder].
All artifacts are complete or approved. Nothing to delegate.
```

---

### Step 4: Confirm with User

Present the plan and ask:

```
Ready to dispatch the above plan to specialist subagents?
This will spawn [N] local subagent sessions (no API key required beyond your existing Claude Code key).

Note: Review gates (artifact *-review steps) remain human-in-the-loop.
Subagents will stop at each review gate and you will be prompted.

Proceed? (yes / adjust / cancel)
```

On `adjust`: ask what to change (skip a step, change agent assignment, run a subset). Apply the adjustment and re-present the plan.

On `cancel`: exit without dispatching.

---

### Step 5: Check for Agent Definitions

Before dispatching, verify `agents/<agent-name>/AGENT.md` exists for each agent type in the plan (bundled with the plugin; located at the plugin's `agents/` directory).

If an agent definition is missing for a required type:

```
Agent definition not found: [agent-name]
Expected at: agents/[agent-name]/AGENT.md

This agent type will be skipped. Affected tasks: [list]
Continue with the remaining plan? (yes / cancel)
```

---

### Step 6: Dispatch Subagents

For each step in the plan, in sequence (launching parallel steps concurrently using Claude Code's Agent tool):

1. Spawn a local subagent using the Agent tool with:
   - `subagent_type`: `[agent-id]` (matching the `agent_id` in the agent's `AGENT.md`)
   - Prompt: task instruction including release folder, specific artifact actions, and paths to input artifacts
   - The agent definition at `agents/[agent-name]/AGENT.md` is loaded as the subagent's system context

   Example task instruction (single agent):
   ```
   Release: [release_folder]
   Tasks: pipeline-generate, data_model-generate, dbt-generate
   Inputs:
     - Requirements: .wire/releases/[release]/artifacts/requirements/requirements.md
     - Conceptual model: .wire/releases/[release]/artifacts/conceptual_model/conceptual_model.md
   Context file: .wire/engagement/context.md
   Update status.md and decisions.md as you complete each artifact.
   ```

   For fan-out agents, include the scoped model list in the task instruction:
   ```
   Release: [release_folder]
   Tasks: dbt-generate
   Fan-out: dbt-developer [staging 1/2] — generate only the models listed in task_scope
   task_scope:
     - stg_source_a__entity_x
     - stg_source_a__entity_y
     - stg_source_a__entity_z
     [+ seeds if co-batched with this agent]
   Inputs:
     - Requirements: .wire/releases/[release]/artifacts/requirements/requirements.md
     - Conceptual model: .wire/releases/[release]/artifacts/conceptual_model/conceptual_model.md
   Context file: .wire/engagement/context.md
   Do not generate models outside task_scope. Update decisions.md for non-obvious choices.
   Note: parallel agents are generating other batches simultaneously — do not wait for them.
   ```

2. Update `status.md` to reflect work in progress:
   ```yaml
   agents:
     mode: local
     last_orchestrated: [timestamp]
   ```

3. Show subagent progress in the console as it executes. Surface artifact completion events without pasting full content.

4. On subagent completion, check that expected artifact files exist and `status.md` has been updated.

5. After each step completes, launch the next step (or the next parallel batch).

---

### Step 7: Handle Review Gates

When the plan reaches a review action (`*-review`), pause and notify:

```
[Release] Delegation paused at review gate.

Artifact: [artifact_name]
Status:   [validate result — PASS / PASS WITH WARNINGS / FAIL]
Location: .wire/releases/[release]/artifacts/[artifact]/

Run /wire:[artifact]-review [release_folder] to conduct the stakeholder review.
Once approved, re-run /wire:delegate [release_folder] to continue.
```

Update `status.md`:
```yaml
agents:
  mode: local
  last_orchestrated: [timestamp]
  paused_at: [artifact]-review
```

---

### Step 8: Handle Failures

If a subagent returns without completing its expected artifacts:

```
[Subagent incomplete] [agent-name] — [task list]

Artifacts expected but not written: [list]
Artifacts written: [list]

Options:
  retry   — re-dispatch the same subagent with the same task
  skip    — mark this artifact as blocked and continue with independent work
  stop    — halt delegation and return control
```

Wait for user input. Do not automatically retry.

---

### Step 9: Completion Summary

When all steps are complete (or delegation is halted):

```
## Delegation complete — [engagement_name] / [release_folder]

Subagents run:   [N]
Artifacts:       [N complete / N incomplete / N skipped]

Next steps:
  /wire:[artifact]-review [release_folder]    — conduct outstanding review gates
  /wire:status [release_folder]               — check full release status
```

Commit `status.md`, `decisions.md`, and `execution_log.md` to git:
```bash
git add .wire/releases/[release_folder]/status.md .wire/releases/[release_folder]/decisions.md .wire/execution_log.md
git commit -m "delegate: [release_folder] — [N] subagents complete"
```

---

## Edge Cases

### Agent definition not found

Skip tasks for that agent type and note them as `unscheduled — agent definition not found`. Continue with the remaining plan.

### Parallel subagents writing overlapping paths

Design task assignments to avoid overlapping output paths — the dependency rules in Step 3 prevent most conflicts. If a conflict is detected post-run, surface it in the completion summary and ask the user which version to keep.

### decisions.md merge conflicts

If two parallel subagents both append to `decisions.md`, do a line-level merge after the parallel step completes. Both agents' entries are valid — preserve all entries, ordered by timestamp. With fan-out, multiple agents of the same type write concurrently within each layer wave; the line-level merge after each wave completes handles all conflicts.
