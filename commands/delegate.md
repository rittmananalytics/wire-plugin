---
description: Decompose a release's pending work into typed tasks and dispatch to specialist local subagents
argument-hint: <release-folder>
---

# Decompose a release's pending work into typed tasks and dispatch to specialist local subagents

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'delegate',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

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
| `model_tier: economy` | Pass the lower-tier model override to each lane. The consolidation pass runs regardless. |
| `warehouse_spend: none` | **Refuse** to dispatch any lane whose command queries a warehouse (`dbt-*` builds, `equivalency-validate`, `data_quality-validate`, `droughty-*`, any `-validate` with `auto_validate: false` that runs against a live system). Report them as budget-blocked, naming the setting. Do not silently drop them. |
| `warehouse_spend: estimate_required` | Dispatch them, with the cost-governance rules in each lane brief. |
| `warehouse_spend: cap:<amount>` | As above, plus: a lane whose estimate would take the release past the cap becomes a parked decision, not a dispatch. |
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

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
