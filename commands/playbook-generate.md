---
description: Generate a step-by-step BPMN delivery playbook for any Wire release
argument-hint: <release-folder>
---

# Generate a step-by-step BPMN delivery playbook for any Wire release

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
    'command': 'playbook-generate',
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
command: generate
artifact: playbook
domain: playbook
release_types: []
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Generate a step-by-step BPMN delivery playbook for any Wire release
argument-hint: <release-folder>

---

# Playbook Generate

Follow `specs/utils/delivery_lead_delegate.md` before executing the workflow below.

## Purpose

Generate a step-by-step delivery playbook for any Wire release. The playbook has two parts: a BPMN-style Mermaid control-flow diagram, followed by a narrative step-by-step guide. It is a planning utility — it does not create a tracked artifact in `status.md` but it does sync to the release's Confluence page if one is configured.

Ideal run point: after the first scope-setting artifact is complete (`engagement_brief` for `sop_discovery`, `problem_definition` for `discovery`, `requirements` for all delivery release types). Can also run immediately after `/wire:new` for a template-level playbook — the diagram and narrative will lack open questions, dates, and team names.

## Prerequisites

- `.wire/releases/<release-folder>/status.md` must exist
- `.wire/engagement/context.md` should exist (optional but recommended for client name, team, and dates)

## Workflow

### Step 1 — Locate the release

Resolve `.wire/releases/<release-folder>/status.md`. Read:
- `release_type`
- `release_name`
- `release_id`
- `confluence_page_id` (if present)
- The full artifact block (all artifacts and their generate/validate/review gate states)

Read `.wire/engagement/context.md` for: client name, engagement lead, team members, and target dates.

If no artifact has `generate: complete`, continue but prepend the following notice to the output:

> **Playbook generated at template level — re-run after [first artifact] to incorporate open questions, dates, and team context.**

If a playbook file already exists at `.wire/releases/<release-folder>/planning/<release_name>_playbook.md`, ask the user: **"A playbook already exists. Overwrite or update?"** Wait for their response before proceeding.

---

### Step 2 — Extract context from completed artifacts

Read every artifact file listed in `status.md` where `generate: complete`. The artifact files live under `.wire/releases/<release-folder>/` in subdirectories matching the artifact name (e.g. `requirements/requirements_specification.md`, `planning/engagement_brief.md`).

From these files extract:

- All open questions (rows labelled `OQ-N` or `DQ-N`) and flag which are marked as blockers or must-close
- Named owners for each OQ/DQ
- Target dates (kick-off, playback, go-live, sprint end, etc.)
- Named team members and their roles
- Known risks and constraints
- Any repeat-cycle steps (e.g. per-session workshop loops, per-stakeholder interview cycles)

---

### Step 3 — Determine the artifact sequence and parallel structure

Use this canonical mapping to determine phases and whether the release type has parallel work streams:

| Release type | Phases | Parallel streams in Week 1? |
|---|---|---|
| `sop_discovery` | Pre-sprint → Week 1 (parallel) → Week 2 consolidation | Yes: Gold Layer Audit, Hightouch Classification, dbt Audit, Domain Workshops (×N sessions) |
| `discovery` | Pre-sprint → Shaping → Review | No |
| `full_platform` | Requirements → Design → Development → Testing → Deployment → Enablement | No |
| `pipeline_only` | Requirements → Design → Development → Testing → Deployment | No |
| `dbt_development` | Requirements → Design → Development → Testing → Deployment | No |
| `dashboard_extension` | Requirements → Mockups → Development → Review | No |
| `dashboard_first` | Mockups → Data Model → Development → Review | No |
| `enablement` | Content → Delivery | No |
| `platform_migration` | Phase 1: Audit (parallel) → Phase 2: Inventory & Strategy → Phase 3: Target Setup → Phase 4: Migration (parallel batches; dbt models and snapshots, each snapshot ordered ahead of its dependents) → Phase 5: Equivalency → Phase 6: Cutover | Yes: Phase 1 audits run in parallel; Phase 4 dbt batches run in parallel per batch group |

For `platform_migration` the canonical Phase 2 step sequence is:

1. `/wire:migration-audit-all` (or individual audit commands in parallel)
2. `/wire:lineage-generate` — generates an interactive HTML dependency explorer showing the full migration scope from ingestion sources through to warehouse objects. Run immediately after the inventory is complete; the lineage map is the primary tool for scoping batches and communicating migration complexity to the client.
3. `/wire:migration-inventory-generate`
4. `/wire:migration-strategy-generate`

Include `/wire:lineage-generate` explicitly in the Phase 2 section of every `platform_migration` playbook, between the audit phase and the inventory step.

For `platform_migration` playbooks, also include a **Session Start** section at the top of the narrative as the recommended sequence to run at the beginning of every working session:

```
Session start sequence (run at the start of every session):
  1. /wire:start [release-folder]       — reorient, see current state and next action
  2. /wire:mcp check [release-folder]   — verify all required MCP servers are reachable
  3. [continue with the next audit or migration command]
```

#### Tenant carve-out variant (`migration.scope == tenant_carveout`)

Read `migration.scope` from `status.md`. When it is absent or `full_migration`, **omit this block entirely** — the standard six-phase `platform_migration` sequence above is unchanged. Only when `migration.scope == tenant_carveout` insert the following carve-out steps into the sequence (both the narrative and the BPMN diagram), at the positions noted, using `migration.tenant_predicate` to scope the extracted tenant. Mark each inserted node clearly as a carve-out-only step.

- **After Phase 1 audits** — region-tagging: tag every in-scope item with the region / tenant boundary it belongs to, scoped by `migration.tenant_predicate`. Run `/wire:region-tagging-generate <release> [--region <code>]` → `/wire:region-tagging-validate` → `/wire:region-tagging-review` (the human adjudication gate).
- **Alongside Phase 2 strategy** — data-residency-assessment: the GDPR and data-residency assessment, including the legal review of the historical data window being migrated. Run `/wire:data-residency-assessment-generate <release>` → `-validate` → `-review` (the client DPO/legal sign-off gate). RA prepares this as data processor; the lawful-basis and retention determinations are the client's. This is a Stage 1 contractual deliverable with its own gate.
- **Phase 4 migration** — bulk-copy-migration **in place of the re-ingest assumption**: a tenant-scoped Snowflake→BigQuery bulk copy filtered by `migration.tenant_predicate`, instead of re-running ingestion connectors. This copy also moves each `copy_and_continue` snapshot's built SCD-2 history (payload + `dbt_scd_id`/`dbt_updated_at`/`dbt_valid_from`/`dbt_valid_to`, frozen at the baseline `T`, tenant-filtered) so the target `dbt snapshot` run adopts and continues it rather than restarting history from empty. Run `/wire:bulk-copy-migration-generate <release>` → `-validate` → `-review` (safety gate before the first copy).
- **Reporting layer** — reinstate the tenant's reporting layer against the target, tool-dependent on `migration.reporting_tool`: for `metabase`, run `/wire:metabase-migration-generate <release>` → `-validate` → `-review` (preceded by `/wire:metabase-audit-*` if not yet catalogued); for `omni`, run `/wire:omni-migration-generate <release>` → `-validate` → `-review` (preceded by `/wire:omni-audit-*` if not yet catalogued); for `oac`, run `/wire:oac-migration-generate <release>` → `-validate` → `-review` (preceded by `/wire:oac-audit-*` if not yet catalogued). Reporting-layer commands are gated on `migration.reporting_tool` being set to the matching tool, not on scope.
- **Before Phase 6 cutover** — logical-access-uat: verify tenant-scoped logical access (roles, row-level security, masking) on the target before cutover. Run `/wire:logical-access-uat-generate <release> [--region <code>]` → `-validate` → `-review` (the isolation-proof sign-off gate).

For `sop_discovery` and any release type with parallel streams: the diagram will include parallel fork and join gateways. For all others: linear sequence.

---

### Step 4 — Generate the BPMN-style Mermaid diagram

The diagram **MUST** be a `flowchart TD` BPMN-style diagram. Apply the following rules without exception.

#### Node shapes — map directly to BPMN element types

| Mermaid syntax | BPMN element | Use for |
|---|---|---|
| `([Label])` | Circle event | Start and end events only |
| `[Label]` | Rectangle task | Offline work tasks and Wire generate/validate/review steps |
| `{Label}` | Diamond gateway | Exclusive gateways — decisions, yes/no branches |
| `{{Label}}` | Hexagon gateway | Parallel gateways — fork and join points |

#### Subgraphs

Use one `subgraph` per phase. Label each subgraph with the phase name and date range where known from the context extracted in Step 2.

#### Parallel structure

For `sop_discovery` (and any release type with parallel streams):
1. Emit a `{{PARALLEL FORK}}` hexagon node after the pre-sprint subgraph.
2. Connect it to each parallel stream subgraph.
3. After all parallel streams end, emit a `{{PARALLEL JOIN}}` hexagon node. All stream terminal nodes must point into it.
4. Label both gateway nodes with the expected calendar date if it can be inferred from extracted context.

#### Decision gates for blockers

For every OQ or DQ extracted in Step 2 that is flagged as a blocker or must-close:
1. Insert a `{OQ-N resolved?}` diamond node at the point in the flow where it must be resolved.
2. The **No / not yet resolved** branch must go to an offline chase node: `[Chase [owner] — [OQ label]]`, which loops back to the decision diamond.
3. The **Yes / resolved** branch continues the main flow.

#### Rework loops

Wherever a generate → validate → review cycle can result in changes being requested, the "changes requested" branch of the review decision node must loop back to the generate node for that artifact.

#### Class definitions

Define and apply all five of the following `classDef` classes. Every node must have exactly one class:

```
classDef wireCmd fill:#1a3a5c,stroke:#4a90d9,color:#fff
classDef offline fill:#2d4a1e,stroke:#6abf4b,color:#fff
classDef decision fill:#5c3a00,stroke:#d98c1a,color:#fff
classDef gate fill:#4a1a5c,stroke:#a04ad9,color:#fff
classDef event fill:#1a1a1a,stroke:#888,color:#fff
```

Apply as follows:
- Wire generate/validate/review command nodes → `wireCmd`
- Offline work task nodes → `offline`
- Decision diamond nodes → `decision`
- Parallel gateway hexagon nodes → `gate`
- Start and end event nodes → `event`

#### Wire command node labels

Label Wire command nodes with the exact command including the leading slash: e.g. `/wire:engagement-brief-generate`. Where validate and review are shown together to save space, combine them on one node with a line break using `<br/>`.

#### Pre-write validation

Before writing the diagram, mentally trace every path from start to end and verify:
- No dangling nodes
- Every fork has a matching join
- Every loop has an exit condition

---

### Step 5 — Generate the narrative playbook

After the diagram, produce a narrative section for each step in the release sequence. Each step section must contain:

1. **Step heading** — numbered, with the Wire artifact name and a plain-English label (e.g. `Step 4 — Gold Layer Audit → discovery_analyses`)
2. **Offline prerequisites** — what files need to exist in the artifact directory before running generate, who produces them, and any naming conventions
3. **Wire commands** — the exact generate, validate, and review commands with the actual `<release-folder>` argument filled in from the release name
4. **OQ/DQ checkpoint** — any open questions that must be resolved at or before this step, with the named owner from extracted context and the escalation path if unresolved
5. **Done when** — one sentence defining what "complete" looks like for this step before moving on

Also include the following sections at the end:

**Daily rhythm** — covering `/wire:session-plan` and how to scope each session (applicable to any release type with workshop or interview steps).

**What Wire does and does not do** — write this as two short paragraphs, not a single bullet.

*Wire writes the artifacts.* List the specific output types relevant to this release type — for example: requirements specs, conceptual + physical data models, pipeline code, dbt staging/integration/warehouse models, LookML views and explores, dashboards, audit reports, migration translations, kickoff decks, training materials, documentation. Wire also runs the mechanical validations (naming conventions, structural checks, test coverage, FK referential integrity, etc.).

*Wire does not take decisions on the team's or sponsor's behalf.* Workshops and interviews are run by humans; open-question resolution happens in conversation, not in Wire commands; sponsor sign-off, UAT approval, and external communications (email, Slack, client meetings) remain human-owned. Every `-generate` command is followed by a `-validate` and a `-review` — the review is the human gate. Do NOT claim Wire "doesn't write code" or "doesn't run audits" — both are wrong for every release type that includes those artifacts.

**Wire command reference table** — every command used in the playbook with a one-line description.

---

### Step 6 — Write output

Create the directory if it does not exist:

```bash
mkdir -p .wire/releases/<release-folder>/planning
```

Write the file to `.wire/releases/<release-folder>/planning/<release_name>_playbook.md`.

File structure:

```
# [Client] [Release name] — Wire Framework Playbook
[metadata: sprint dates, end deliverable, engagement lead]
---
## Sprint Control Flow
[Mermaid diagram block]
---
## How the Framework Works for This [Release type]
[artifact → work stream mapping table]
---
## Step-by-step Playbook
[numbered steps]
---
## Daily Rhythm
## What Wire Does Not Do
## Wire Command Reference
```

---

### Step 7 — Update execution log and sync to Confluence

Append one row to `.wire/releases/<release-folder>/execution_log.md` in the standard table format:

```
| [timestamp] | /wire:playbook-generate | complete | <release_name>_playbook.md generated — [N]-step playbook with BPMN diagram |
```

If `confluence_page_id` is present in `status.md` for this release, sync the playbook file to Confluence as a child page of the release page, titled `[Release name] — Delivery Playbook`. Follow `specs/utils/docstore_sync.md`.

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
