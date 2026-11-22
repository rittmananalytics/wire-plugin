---
wire_schema: "1.0"
command: lifecycle
artifact: delegate
domain: delegate
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Decompose a release's pending work into typed tasks and dispatch to specialist local subagents
argument-hint: <release-folder>

delegates_to:
  - utils/runnable_set
  - utils/director_operating_model
---

# Wire Delegate Command

## Purpose

Read a release's `status.md`, identify all pending artifact work, group it into typed task units per specialist agent, present a parallel/sequential execution plan, and dispatch to Claude Code local subagents.

Run it directly when you want to review and confirm the delegation plan before agents start executing, for any release with multiple pending artifacts across different specialist agents.

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
3. Read `.wire/engagement/context.md` — extract `client_name`, `engagement_name`, warehouse type (`bigquery` or `snowflake`), and `orchestration.mode` (`orchestrated` or `manual`; absent means `orchestrated` on Claude Code, `manual` on Gemini CLI)
4. Read `status.md`'s `budget:` block. Absent means the defaults: `lanes_max: 4`, `warehouse_spend` unrestricted, `stop_at: decisions`.
5. Read `status.md`'s `agents.coordinator_session` — the release claim.

---

### Step 1b: Resolve the Release Claim

Before anything is dispatched, resolve the claim per
`specs/utils/director_operating_model.md` ("The release claim"):

| Claim state | What this command does |
|---|---|
| No claim, or `null` | Claim it: write `agents.coordinator_session` with this user, this session id, the current branch, `claimed_at` and `last_write`. Proceed. |
| Held by this user, this session | Proceed. Refresh `last_write`. |
| Held by this user, a different session | Rewrite `session_id` to this session and proceed. One person cannot contend with themselves. |
| Held by another user, `last_write` within 30 minutes | **Do not dispatch.** Offer: join as reviewer (read state and rule, no dispatch), or move to another release. |
| Held by another user, `last_write` older than 30 minutes | **Do not dispatch yet.** Offer: take over (the 30-minute stall rule — rewrites the claim and says whose it was), join as reviewer, or move. |

Output when the claim is held by someone else:

```
This release is claimed.

  Held by:     [user]
  Session:     [session_id]
  Branch:      [branch]
  Last write:  [last_write]  ([N] minutes ago)

  [If under 30 minutes:]
  Another session is driving this release. Options:
    join   — read state and make rulings; no dispatch
    move   — pick a different release
  [If over 30 minutes:]
  That session has not written for [N] minutes. Options:
    take   — take the release over; the claim is rewritten in your name
    join   — read state and make rulings; no dispatch
    move   — pick a different release
```

Never dispatch while another live claim exists. A person typing a single
command by hand is a different case: they get a warning naming the holder, and
proceed (the collision guard in the operating model).

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
| `conceptual_model`, `data_model`, `pipeline_design`, `mockups` (standard mode), `viz_catalog` (standard mode) | `data-designer` |
| `mockups`, `viz_catalog` (`dashboard_first` projects only) | `dashboard-mock-developer` |
| `seed_data`, `data_refactor` | `mock-data-developer` |
| `pipeline`, `pipeline/fivetran/*`, `pipeline/airbyte/*`, `pipeline/dlt/*` | `pipeline-engineer` |
| `dbt`, `droughty/dbt-tests`, `droughty/stage` | `dbt-developer` |
| `semantic_layer`, `dashboards`, `ads/lookml_views`, `ads/semantic_layer`, `droughty/lookml` | `semantic-layer-developer` |
| `orchestration`, `migration/orchestration_audit`, `migration/orchestration_migration` | `orchestration-engineer` |
| `data_quality`, `uat`, `droughty/setup`, `droughty/introspect`, `droughty/docs`, `droughty/qa`, `droughty/dbml` | `data-quality-engineer` |
| `migration/omni_model`, `migration/omni_content` (`bi_migration` releases) | `semantic-layer-developer` |
| `migration/looker_audit`, `migration/bi_migration_plan`, `migration/omni_target_setup`, `migration/bi_equivalency` (`bi_migration` releases) | `migration-specialist` |
| `migration/*` (all except orchestration_audit/orchestration_migration) | `migration-specialist` |
| `deployment`, `kickoff`, `enablement/training_*`, `playbook` | `delivery-lead` |
| `agentic_data_stack/*` | `agentic-data-stack-developer` |
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
   - **Integration** (`int_<group>__*`): depends on staging; models within integration are independent of each other.
   - **Warehouse** (`*_dim`, `*_fact`, `*_xa`): depends on integration; models within warehouse are independent of each other.
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

**Start from the runnable set.** Run `specs/utils/runnable_set.md` for this
release. It reads the release-type YAML and the active profile and returns each
artifact's state and the topological order. That is the authority on what can
run and what can run alongside what; the rules below are the agent-level view
of the same graph and must not contradict it. Where they disagree, the runnable
set is right.

Three of its outputs change the plan directly:

- `parked: needs ruling` — not scheduled. Surface it as a decision the director
  must make. Every review edge is parked.
- `blocked: <unmet precondition>` — not scheduled. Surface it with the unmet
  precondition named.
- `not applicable` — not scheduled, and not reported as pending. The profile
  has ruled it out.

**Apply the budget** (`specs/utils/director_operating_model.md`, "Budget"):

| Setting | Effect on the plan |
|---|---|
| `lanes_max: N` | No step dispatches more than N agents at once. Where the graph offers more, take them in the runnable set's order and queue the rest. Fan-out batches (Step 2.5) count individually: 5 `dbt-developer` batches under `lanes_max: 2` run 2 at a time. |
| `model_tier: economy` | Dispatch eligible lanes on the routing file's `lane_economy` model, by the order in Step 6 ("Lane model"). A lane whose command has a tier model, or produces a client-facing deliverable, is not eligible. The consolidation pass runs regardless. |
| `warehouse_spend: none` | **Refuse** to dispatch any lane whose command queries a warehouse (`dbt-*` builds, `equivalency-validate`, `data_quality-validate`, `droughty-*`, any `-validate` with `auto_validate: false` that runs against a live system). Report them as budget-blocked, naming the setting. Do not silently drop them. |
| `warehouse_spend: estimate_required` | Dispatch them, with the cost-governance rules in each lane brief. |
| `warehouse_spend: cap:<amount>` | As above, plus: a lane whose estimate would take the release past the cap becomes a parked decision, not a dispatch. |

On Claude Code the Wire mod (wire#270) applies the same budget at the moment
of the call, after dispatch: a brief past `lanes_max` is refused at
`agent.spawn` and named as queued; a lane's warehouse tool call or dbt run
under `warehouse_spend: none` is refused; every warehouse call from a lane is
recorded in `lanes/_spend.jsonl`, and under `cap:<amount>` the call that passes
the cap raises a parked decision (kind `budget`) and the next is refused. This
command's check at planning time is still the first line: it keeps a refused
lane out of the plan rather than letting it start and be stopped.
| `stop_at: decisions` | Stop the plan at the first parked decision and report. |
| `stop_at: phase_end` | Continue past a parked decision on one artifact to other runnable work in the phase. |
| `stop_at: never` | Run until nothing is runnable. |

Output when a lane is refused on budget:

```
Not dispatched — budget:
  [artifact]-[action]   warehouse_spend: none (queries the warehouse)
  [artifact]-[action]   lanes_max: 2 reached — queued behind [artifact], [artifact]

Change the budget in status.md, or say so, and I will re-plan.
```

Then determine which agent tasks can run in parallel and which must be sequential, based on these dependency rules:

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

This plan is the run plan of `specs/utils/director_operating_model.md` rule 8, grouped by agent. Every command in it is written in full, as it would be typed (`/wire:` prefix, release folder, flags), never as a bare name.

Format the plan as a numbered sequence with parallel steps as lettered sub-steps. When fan-out applies to a step, use a multi-wave block inside that step — waves are sequential, agents within each wave are parallel:

```
Delegation plan — [engagement_name] / [release_folder]
──────────────────────────────────────────────────────

Step 1 (sequential):
  discovery-analyst → /wire:requirements-generate [release_folder], /wire:workshops-generate [release_folder]
  Subagent: discovery-analyst

Step 2 (parallel, starts after step 1):
  2a  data-designer    → /wire:conceptual_model-generate [release_folder], /wire:pipeline_design-generate [release_folder], /wire:mockups-generate [release_folder]
  2b  pipeline-engineer → /wire:pipeline-generate [release_folder] (connectors)
  Subagents: 2 parallel

Step 3 (multi-wave fan-out, starts after step 2):

  Wave 3a — Staging layer  (2 parallel agents):
    dbt-developer [staging 1/2]  → stg_source_a__entity_x, stg_source_a__entity_y, ...
    dbt-developer [staging 2/2]  → stg_source_b__entity_a, stg_source_b__entity_b, ...
  
  Wave 3b — Integration layer  (1 agent, starts after Wave 3a):
    dbt-developer [integration 1/1]  → int_core__unified_entity
  
  Wave 3c — Warehouse layer  (2 parallel agents, starts after Wave 3b):
    dbt-developer [warehouse 1/2]  → wh_core__entity_dim, wh_core__summary_fact, ...
    dbt-developer [warehouse 2/2]  → wh_core__detail_fact, wh_core__history_fact, ...
  
  Total dbt-developer agents: 5  (2 + 1 + 2)

Step 4 (parallel, starts after step 3):
  4a  semantic-layer-developer → /wire:semantic_layer-generate [release_folder], /wire:dashboards-generate [release_folder]
  4b  data-quality-engineer    → /wire:data_quality-generate [release_folder]
  Subagents: 2 parallel

Step 5 (sequential, starts after step 4):
  qa-agent → /wire:<artifact>-validate [release_folder] for every artifact from steps 1–4

Step 6 (sequential, starts after step 5):
  delivery-lead → /wire:deployment-generate [release_folder], /wire:documentation-generate [release_folder], /wire:training-generate [release_folder]

Total: [N] steps, [N] with parallelism. Blocked items: [list any blocked artifacts]
```

If there are no pending items, output:
```
No pending work found for [release_folder].
All artifacts are complete or approved. Nothing to delegate.
```

---

### Step 4: Confirm with User

Present the plan and ask. This is the go / adjust / cancel step of operating model rule 8: nothing is dispatched until the director answers, and silence is not a yes.

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
   - `model`: the lane's model from "Lane model" below, or no `model` parameter when that order resolves to the session default
   - Prompt: task instruction including release folder, specific artifact actions, and paths to input artifacts
   - The agent definition at `agents/[agent-name]/AGENT.md` is loaded as the subagent's system context

   **Every dispatch carries the lane brief** from
   `specs/utils/director_operating_model.md` ("Lane brief template"): the lane
   label, the release, the task, the directories the lane owns, its state file
   path, the resume contract, its budget line, the flat-lane rule, the
   status-writing rule, and report-once. The brief is not optional decoration:
   rules 1, 3, 4 and 6 are conventions, and the brief is where they are stated.

   Example task instruction (single agent, orchestrated mode):
   ```
   Lane:        conceptual_model
   Release:     [release_folder]
   Tasks:       conceptual_model-generate
   Owns:        .wire/releases/[release]/design/
   State file:  .wire/releases/[release]/lanes/conceptual_model.md
   Resume:      Read the state file first; skip completed items. Rewrite it
                after each completed item, not at the end.
   Budget:      warehouse_spend: none — do not query a warehouse.
   Flat:        Do not spawn sub-agents. If this is bigger than one lane, say
                so and stop.
   Status:      Do not write status.md or execution_log.md. I write them from
                your state file. (WIRE_INVOKED_BY=lane is set for you.)
   Report:      Report once — complete, stalled, or needs a ruling.
   Inputs:
     - Requirements: .wire/releases/[release]/artifacts/requirements/requirements.md
     - Conceptual model: .wire/releases/[release]/artifacts/conceptual_model/conceptual_model.md
   Context file: .wire/engagement/context.md
   Append non-obvious choices to decisions.md.
   ```

   **In manual mode** (`orchestration.mode: manual`, or a single command
   auto-delegating outside the director model) the `Status:` line is omitted
   and the lane updates `status.md` itself, exactly as it does today. This is
   the only behavioural difference between the two modes at dispatch.

   Set `WIRE_INVOKED_BY=lane` in each lane's environment before dispatch, and
   `WIRE_INVOKED_BY=orchestrator` for commands this session runs itself. The
   telemetry hook and the execution log both read it
   (`specs/utils/telemetry.md`, `specs/utils/execution_log.md`), so the record
   says what invoked each run without anyone being asked.

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

2. Update `status.md` to reflect work in progress. In orchestrated mode this
   session is the only writer of `status.md` and `execution_log.md`:
   ```yaml
   agents:
     mode: orchestrated
     coordinator_session:
       user: "[git user.name]"
       session_id: "[session id]"
       branch: "[current branch]"
       claimed_at: "[when this session claimed the release]"
       last_write: "[now]"
     last_orchestrated: [timestamp]
   ```
   In manual mode, write `mode: local` and `last_orchestrated` as before.

3. Show subagent progress in the console as it executes. Surface artifact completion events without pasting full content.

4. On subagent completion, run the consolidation check from
   `specs/utils/director_operating_model.md` ("The consolidation and backstop
   pass") before treating the lane's work as done:
   - the artifact files the lane claimed exist on disk;
   - validate ran, and its recorded result matches what the lane reported;
   - **the lane did not write `status.md`** (orchestrated mode only). A lane
     that did is a rule-6 violation: report it, and reconcile `status.md` from
     the lane's state file rather than trusting the lane's edit;
   - for warehouse-touching work, re-check build results against the warehouse
     rather than the lane's claim.

   Then write `status.md` from the lane's state file. In manual mode, check
   instead that the lane updated `status.md` itself, as today.

5. After each step completes, launch the next step (or the next parallel batch).

#### Lane model

`wire/model-routing.yaml` is the only place a lane's model is set. It ships at
the plugin root as `model-routing.yaml`; read the tier models under `tiers:`
and the economy model `lane_economy` from there. Agent definitions carry no
`model:` field. Resolve one model for each lane, taking the first rule that
applies:

| Order | Rule | Model |
|---|---|---|
| 1 | **Command tier.** The lane's command has a `workload:` tag whose tier maps to a model (a non-empty value under `tiers:`). | That tier's model |
| 2 | **Economy.** `budget.model_tier: economy` is set in `status.md`, and the command does not produce a client-facing deliverable. | `lane_economy` |
| 3 | **Session default.** Neither rule applies. | No `model` parameter: the lane inherits the session model (or `CLAUDE_CODE_SUBAGENT_MODEL`, if the person has set it) |

Pass the result of rule 1 or 2 as the Agent tool's `model` parameter. Do not
rely on the agent definition or on the model stamped into the command (see the
note below).

**Floor.** Rule 2 never applies to a command that produces a client-facing
deliverable, so economy mode cannot run one below the session default. Rule 1
is not subject to this check at dispatch: a tier's model is chosen in the
routing file, where the same floor applies and a demotion needs an eval
comparison.

**Client-facing deliverable.** Decided from the command spec's front matter.
A command produces one when any of these holds:

- `command: generate` with `action_type: artifact` (the artifact is the deliverable);
- `command: review` (it is presented to, and approved by, the client's stakeholders);
- a `produces` entry of type `document`, `deck` or `pr`.

It does not when none holds and the command is a `validate` with no `produces`
entry, or a `utility`, `lifecycle` or `meta` command. One case is not settled
by the front matter: a `validate` whose `produces` entries are all of type
`report`. Some of these reports are evidence the client sees (the
`bi_equivalency` parity report gates cutover); others are internal checks.
Until the spec says which, treat it as client-facing, so the floor holds.

**One model per lane.** If the commands in one lane resolve to different
models, split them into consecutive lanes, one per model, in the plan's order.
A fan-out batch resolves on its command like any other lane.

**Unknown economy model.** If `model_tier: economy` is set and the routing
file has no `lane_economy` value, do not guess one. Dispatch on rules 1 and 3
only and say so in the plan. (Tier 0 lint fails the build in that state, so it
should not reach a release.)

> **Which model a lane runs on, checked against Claude Code 2.1.302 (October
> 2026), sub-agents and skills documentation.** A subagent's model is chosen,
> highest first, by: the Agent tool call's `model` parameter; the agent
> definition's `model:`; the `CLAUDE_CODE_SUBAGENT_MODEL` environment
> variable; the main session's model. When `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`
> is set (from 2.1.257) the environment variable wins over all of these. A
> command's or skill's `model:` is not in that order. It is documented as an
> override for the rest of the current turn; whether it changes the model of
> a subagent that runs the command through the Skill tool is not documented.
>
> Until wire#316 every agent definition set `model: claude-opus-4-8`, so every
> lane ran on that model whatever the session default and whatever the routing
> file said. That was a live fault for lane work, not only a maintenance risk:
> a model change in the routing file never reached a lane. Whether a stamped
> command (for example a `planning` one) ran on its tier's model inside a lane
> is unverified. This is why the orchestrator passes the model on the Agent
> call, the top of the order, and does not depend on the stamp.

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

Record the park in `status.md` as a parked decision, not as a single
`paused_at` value — a release can be waiting on more than one thing at once
(`specs/utils/director_operating_model.md`, "Parked decisions"):

```yaml
agents:
  mode: orchestrated
  last_orchestrated: [timestamp]

parked_decisions:
  - id: PD-[n]
    artifact: [artifact]
    kind: review
    question: "Approve now, request changes, or park for client sign-off?"
    parked_at: "[timestamp]"
    awaiting: "[who is expected to answer, if not the director]"
```

In orchestrated mode, present the three-way ruling (approve now / changes /
park for client sign-off) rather than only printing the review command. The
review command still runs, unchanged, when the director approves.

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
