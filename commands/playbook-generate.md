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

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.7.0\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"playbook-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.7.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate a step-by-step BPMN delivery playbook for any Wire release
argument-hint: <release-folder>
---

# Playbook Generate

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

**Daily rhythm** — covering `/wire:plan` and how to scope each session (applicable to any release type with workshop or interview steps).

**What Wire does not do** — a short list: does not run audits, does not attend workshops, does not resolve OQs, does not write Looker/dbt code, does not send emails.

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

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
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
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
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

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
