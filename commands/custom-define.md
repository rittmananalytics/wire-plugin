---
description: Define a custom release type from SoW or project documents — map deliverables to Wire commands or generate bespoke specs
argument-hint: <release-folder>
---

# Define a custom release type from SoW or project documents — map deliverables to Wire commands or generate bespoke specs

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
    'command': 'custom-define',
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
command: utility
artifact: custom
domain: custom
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Define a custom release type by analysing SoW or project documents — map deliverables to Wire commands or generate bespoke specs
argument-hint: <release-folder>

---

# Wire Custom Release Define

## Purpose

When an engagement has bespoke deliverables that don't map to any standard Wire release type, this command analyses the provided source documents (SoW, kick-off notes, agreed delivery plan) and proposes a tailored release structure. Deliverables that match existing Wire commands use those commands directly. Deliverables with no standard equivalent get fully-generated project-scoped custom specs with their own generate/validate/review cycle.

This command is invoked automatically by `/wire:new` when the user selects "Custom" as the release type.

## Usage

```bash
/wire:custom-define <release-folder>
```

The `release-folder` argument is the `.wire/releases/` subfolder that `/wire:new` has already created (e.g. `01-poc-productionisation`). If invoked standalone (not via `/wire:new`), the release folder must already exist.

---

## Workflow

### Phase 1: Document Ingestion

Ask in chat:

```
To define a custom release structure, I need to read the engagement documents.

Provide one or more of the following (file paths, Google Drive URLs, or Confluence URLs):
- Statement of Work (SoW)
- Kick-off meeting notes
- Agreed delivery plan
- Project proposal or scope document

Paste paths or URLs, or type "paste" to paste the content directly.
```

For each provided source, call `utils/doc_analyze` to extract the `DeliverableList` object. If multiple documents are provided, merge their deliverable lists (deduplicate by name similarity — a deliverable mentioned in both the SoW and the kick-off notes is one deliverable, not two; use the SoW description as authoritative and kick-off notes for additional acceptance criteria).

Store: `deliverable_list` (merged `DeliverableList`), `source_documents` (list of all sources).

---

### Phase 2: Mapping and Proposal

For each extracted deliverable, determine the proposed handling based on the `wire_artifact_match` score:

**Score ≥ 0.70 (Strong match)**: Use the standard Wire command.
- Map to the matched `artifact` (e.g. `dbt` → `/wire:dbt-generate`, `/wire:dbt-validate`, `/wire:dbt-review`)
- Record as `type: standard`

**Score 0.40–0.69 (Approximate match, no workflow mismatch)**: Propose the standard command as approximate.
- Present a workflow comparison note (see format below)
- Ask user to confirm or choose custom instead
- Record as `type: approximate` pending user confirmation

**Score 0.40–0.69 with `workflow_mismatch: true`**: Default to custom despite the mid-band score.
- Show the mismatch note from `doc_analyze`
- Recommend custom; user can override to standard if they prefer
- Record as `type: custom` (unless user overrides)

**Score < 0.40 (No match)**: Generate a custom spec.
- Record as `type: custom`

Assemble the proposed release table:

```markdown
## Proposed Release Structure — [release_folder]

| # | Deliverable | Handling | Command / Spec Name | Notes |
|---|-------------|----------|---------------------|-------|
| 1 | [name] | Standard ✅ | `/wire:[artifact]-generate` | Matched: [artifact] (score [N]) |
| 2 | [name] | Approximate ⚠️ | `/wire:[artifact]-generate` | Workflow note: [mismatch_note] |
| 3 | [name] | Custom 🔧 | `/wire:[kebab-name]-generate` | No standard match (score [N]) |
```

**Workflow comparison note format** (for approximate matches):
```
⚠️ Approximate match: "[deliverable name]" → /wire:[artifact]-generate (score 0.NN)
   Standard command workflow: [one-line description of what Wire's standard command does]
   This deliverable requires: [one-line description from SoW]
   Recommend: [Custom (workflow differs) | Standard (workflow acceptable)]
```

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Review the proposed release structure. Would you like to proceed with this, or make changes?",
    "header": "Proposal",
    "options": [
      {"label": "Accept this structure", "description": "Proceed with the proposed mapping and generate custom specs as listed"},
      {"label": "Make changes", "description": "Swap or rename individual items before generating — I'll walk through each one"}
    ],
    "multiSelect": false
  }]
}
```

**If "Make changes"**: for each deliverable marked `approximate` or `custom`, ask in sequence:
```
Deliverable: "[name]"
Proposed: [Custom spec | /wire:[artifact]-generate (approximate)]

Options:
  a) Use proposed
  b) Use standard /wire:[artifact]-generate
  c) Use a different existing command — type the command name
  d) Custom spec with a different name — type the name

Your choice (a/b/c/d):
```

Require explicit confirmation before writing anything. Do not proceed to Phase 3 until the user has approved the final structure.

---

### Phase 3: Custom Spec Generation

For each deliverable with `type: custom`, generate three fully-detailed specs:

**`[artifact-kebab-name]-generate.md`**

Structure each custom generate spec as:

```markdown
---
description: [one-line description derived from SoW]
argument-hint: <release-folder>
---

# [Deliverable Name] — Generate

## Purpose

[One paragraph from deliverable description in the DeliverableList, written as a Wire spec purpose.]

## Prerequisites

- `.wire/releases/[release_folder]/status.md` exists with this artifact registered
- Source documents: [list the source_doc values from DeliverableList]
- [Any dependencies from deliverable.dependencies]

## Inputs

[List the input files/sources the consultant will need. Derived from the SoW description and acceptance criteria.]

## Workflow

### Step 1: Review Source Materials

Read the following to understand the current state and constraints:
[Generated from the deliverable's context in the SoW — e.g. existing codebase, prior decisions, stakeholder preferences extracted from kick-off notes]

### Step 2–N: [Steps derived from acceptance criteria]

[Each acceptance criterion from the DeliverableList becomes one or more workflow steps.
For example: acceptance criterion "covers storage tier, transformation tier, semantic layer, AI/presentation layer"
→ Step 2: Document storage tier decision and rationale
→ Step 3: Document transformation approach
→ Step 4: Document semantic layer recommendation
→ Step 5: Document AI/MCP integration pattern]

### Final Step: Update Status and Log Session

Update `.wire/releases/[release_folder]/status.md`:
```yaml
[artifact-key]:
  generate: complete
  file: "[output file path]"
  generated_date: "[today]"
```

Log this session in the Session History table.
```

**`[artifact-kebab-name]-validate.md`**

```markdown
---
description: Validate [deliverable name] against SoW acceptance criteria
argument-hint: <release-folder>
---

# [Deliverable Name] — Validate

## Purpose

Run automated checks to confirm the generated [deliverable] meets all acceptance criteria defined in the SoW before it proceeds to stakeholder review.

## Workflow

### Step 1: Read the Artifact

Read the file path recorded in `status.md` under `[artifact-key].file`.

### Step 2: Check Each Acceptance Criterion

[One check per acceptance criterion from DeliverableList. Format as PASS/FAIL.]

| Criterion | Check | Result |
|-----------|-------|--------|
| [criterion 1] | [how to check it] | PASS / FAIL |
| [criterion 2] | [how to check it] | PASS / FAIL |

### Step 3: Report

If all criteria pass: update `status.md` `[artifact-key].validate: complete`.
If any fail: update `status.md` `[artifact-key].validate: fail`, list failures.

Output validation report to terminal.
```

**`[artifact-kebab-name]-review.md`**

```markdown
---
description: Present [deliverable name] for stakeholder review and approval
argument-hint: <release-folder>
---

# [Deliverable Name] — Review

## Purpose

Present the [deliverable] to stakeholders for approval. Gather structured feedback and record the verdict in status.md.

## Workflow

### Step 1: Retrieve Meeting Context

Call `utils/meeting_context` to search Fathom for any prior discussions about this deliverable.

### Step 2: Present for Review

[Stakeholders from DeliverableList — present the artifact summary and key decisions.]

### Step 3: Gather Feedback

Ask the reviewer:
1. Do you approve this deliverable as meeting the SoW requirements?
2. Are there specific sections that need changes?
3. Any blocking concerns before sign-off?

### Step 4: Record Verdict

- **Approved**: update `status.md` `[artifact-key].review: approved`
- **Changes requested**: update `status.md` `[artifact-key].review: changes_requested`, record feedback
- **Blocked**: update `status.md` `[artifact-key].review: blocked`, note blocker

Log in Session History.
```

**Spec naming**: convert the deliverable name to kebab-case for the spec filename and command name. Examples:
- "Target State Architecture Document" → `target-state-architecture-doc`
- "Decision Log" → `decision-log`
- "MCP / AI Integration Roadmap" → `mcp-ai-integration-roadmap`

---

### Phase 4: Scaffolding

Write all files in this order:

**4a. Custom command specs** (for `type: custom` deliverables):
- `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-generate.md`
- `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-validate.md`
- `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-review.md`

Create the directory first:
```bash
mkdir -p .wire/releases/[release_folder]/custom-commands
```

**4b. `.claude/commands/wire/` wrappers** (for each custom spec):

Write a thin wrapper to `.claude/commands/wire/[artifact-kebab-name]-generate.md`:
```markdown
---
description: [same description as the custom spec]
argument-hint: <release-folder>
---

Read the spec at `.wire/releases/[release_folder]/custom-commands/[artifact-kebab-name]-generate.md` and execute it for the provided release folder.
```

Write equivalent wrappers for `-validate.md` and `-review.md`.

The subdirectory `wire/` gives these commands the `wire:` namespace prefix, so they are invoked as `/wire:[artifact-kebab-name]-generate` — consistent with standard Wire commands.

Create the directory first:
```bash
mkdir -p .claude/commands/wire
```

**4c. Update `status.md`**:

Open the existing `.wire/releases/[release_folder]/status.md` and append custom artifact entries to the `artifacts:` YAML section for each deliverable:

For `type: custom` deliverables:
```yaml
[artifact-key]:
  custom: true
  source_document: "[source_doc from DeliverableList]"
  generate: not_started
  validate: not_started
  review: not_started
  file: null
  generated_date: null
  generated_files: []
  revision_history: []
```

For `type: standard` or `type: approximate` deliverables (confirmed), add the matching artifact entry from `status-template.md`.

**4d. Seed Session History from timeline milestones**:

If `deliverable_list.timeline.milestones` contains entries, append a pre-populated session history skeleton to the Session History table in `status.md`:

```markdown
## Session History — Planned Milestones

| Week / Phase | Target Date | Focus | Accomplished | Next |
|---|---|---|---|---|
| [milestone.name] | [milestone.date or TBC] | [milestone.focus] | | |
```

This gives the consultant a ready-made progress tracking structure from day one.

**4e. Patch `engagement/context.md`**:

Add or update the `custom_commands_path` field in the engagement context:
```yaml
custom_commands_path: ".wire/releases/[release_folder]/custom-commands"
```

---

### Phase 5: Activation Notice

Print to terminal:

```
## Custom Release Ready ✅

Folder: .wire/releases/[release_folder]/

### Deliverables and Commands

| Deliverable | Type | Generate | Validate | Review |
|-------------|------|----------|----------|--------|
[one row per deliverable]

### Invocation

All commands use the `/wire:` prefix — custom and standard are consistent:
[list each /wire:[artifact-kebab-name]-generate, -validate, -review]

Standard commands work as usual:
[list each /wire:[artifact]-generate etc. for standard deliverables]

### Suggested First Step

/wire:[first-custom-artifact]-generate [release_folder]

### Keeping Status Current

Custom releases often do substantial work conversationally, outside the
generated commands — and only command runs update status.md and the
execution log automatically. Any work done outside a command run must
reconcile the record before raising a PR:

   /wire:status-sync [release_folder]
```

---

## Edge Cases

**No documents provided**: ask once more, then offer to define deliverables manually (user types them as a numbered list).

**Deliverable with no acceptance criteria and very vague description**: flag in the proposal table as "⚠️ Vague — acceptance criteria will need to be confirmed before spec is generated." Ask the user to clarify before generating that deliverable's specs.

**Duplicate deliverable names**: append a numeric suffix (`-2`, `-3`) to disambiguate.

**Custom commands directory already exists**: check for existing specs before writing. If a spec with the same name already exists, ask whether to overwrite or keep the existing one.

**Standalone invocation (not via `/wire:new`)**: check that `.wire/releases/[release_folder]/` exists. If not, ask the user to run `/wire:new` first or create the folder manually.

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
