---
description: Raise a GitHub issue on the Wire repo proposing a bespoke command as a framework addition
argument-hint: <custom-spec-name>
---

# Raise a GitHub issue on the Wire repo proposing a bespoke command as a framework addition

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
    'command': 'custom-feature-request',
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
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Raise a GitHub issue on the Wire repo proposing a bespoke command as a framework addition
argument-hint: <custom-spec-name> [--description "use case description"]

---

# Wire Custom Feature Request

## Purpose

When a custom command spec created by `/wire:custom-define` represents a general pattern that other RA engagements would benefit from, this utility generalises it and raises a GitHub issue on the Wire repo proposing it as a new standard command.

**This command is never automatically offered or suggested by any other Wire command.** It exists as an explicit user action only. See the User Guide for instructions.

## Usage

```bash
/wire:custom-feature-request <custom-spec-name> [--description "broader use case"]
```

`custom-spec-name` is the kebab-case name of the custom command (e.g. `target-state-architecture-doc`). The spec must exist at `.wire/releases/[any-folder]/custom-commands/[name]-generate.md`.

## Prerequisites

- The custom command spec must exist in `.wire/releases/*/custom-commands/`
- `gh` CLI must be available and authenticated (`gh auth status`)
- The user must have explicitly requested this action

---

## Workflow

### Step 1: Locate the Custom Spec

Search `.wire/releases/` for `custom-commands/[custom-spec-name]-generate.md`. Read the spec file.

If not found: `Custom spec "[name]-generate.md" not found in any release's custom-commands folder.`

### Step 2: Generalise the Problem

Analyse the spec and produce a generalised problem statement:

1. Identify the deliverable type (architecture doc, decision log, advisory report, knowledge transfer plan, etc.)
2. Remove all client-specific details (client name, technology names specific to this client, budget, dates)
3. Extract the generalised workflow pattern: what does the consultant do, step by step?
4. Identify reuse potential: what other RA engagement types would need this? What makes it general enough to be a standard command rather than a one-off?

### Step 3: Draft GitHub Issue

Assemble the issue body:

```markdown
## Feature Request: /wire:[proposed-command-name]

**Proposed by**: [engagement lead from context.md, anonymised if preferred]
**Engagement context**: [generalised — e.g. "PoC productionisation advisory engagement, 4-week fixed-scope"]

---

### Problem Statement

[2-3 sentences describing the gap: what type of engagement has this deliverable, why existing Wire commands don't cover it, what a consultant would otherwise have to do manually]

### Proposed Command

`/wire:[proposed-command-name]-generate`
`/wire:[proposed-command-name]-validate`
`/wire:[proposed-command-name]-review`

### Deliverable Description

[Generalised description of what the command produces, stripped of client specifics]

### Proposed Workflow (from the custom spec)

[Step-by-step workflow extracted from the custom spec, generalised]

### Validation Criteria

[Acceptance criteria from the custom spec, generalised]

### Applicable Release Types

[Which Wire release types would use this command — e.g. "any advisory/architecture engagement, PoC productionisation, discovery with significant existing codebase"]

### Example Usage

```
/wire:new
> Release type: Custom → [this command would become a standard option]
/wire:[command-name]-generate 01-[release-name]
```

---

*Raised from a project-scoped custom command. Original spec: `[spec-filename]`*
*This issue was generated by `/wire:custom-feature-request` and has not been reviewed for framework fit.*
```

**Proposed command name**: derive from the deliverable type. Remove client-specific qualifiers. Examples:
- "Target State Architecture Document" → `architecture-blueprint`
- "Decision Log" → `technology-decision-log`
- "MCP / AI Integration Roadmap" → `mcp-integration-roadmap`

### Step 4: Show Draft and Confirm

Display the full draft issue to the user:

```
## Proposed GitHub Issue

Title: Feature Request: /wire:[proposed-command-name]

[full issue body]

---

Post this issue to github.com/rittmananalytics/wire? (yes/no)
If yes, I'll use gh to create it. If no, I'll save the draft as a markdown file for you.
```

Ask explicitly in chat. Do **not** use AskUserQuestion (this is a deliberate, conversational confirmation step).

Wait for explicit "yes" or "no". If the user asks to edit the draft first, show the editable sections and let them revise.

### Step 5: Post or Save

**If confirmed "yes"**:

```bash
gh issue create \
  --repo rittmananalytics/wire \
  --title "Feature Request: /wire:[proposed-command-name]" \
  --label "enhancement,community-proposed" \
  --body "[issue body]"
```

Return the issue URL.

**If "no"** (save draft):

Write the draft to `.wire/releases/[release_folder]/custom-commands/[spec-name]-feature-request-draft.md`.

```
Draft saved to .wire/releases/[release_folder]/custom-commands/[spec-name]-feature-request-draft.md
Post manually when ready.
```

---

## Output

```
✅ Feature request posted: https://github.com/rittmananalytics/wire/issues/[N]

The issue has been labelled "enhancement, community-proposed".
It will be reviewed by the Wire maintainers for potential inclusion as a standard command.
```

Execute the complete workflow as specified above.
