---
description: Optional planning ritual — propose a focused 3–5 step plan before starting work
argument-hint: (optional: release-folder)
---

# Optional planning ritual — propose a focused 3–5 step plan before starting work

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
    'command': 'session-plan',
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
artifact: session
domain: session
release_types: []
action_type: lifecycle
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Optional session planning ritual — propose a focused 3–5 step plan before starting work

---

# Wire Plan Command

## Purpose

An optional planning ritual. Enters Plan Mode, reads current release and engagement state, then proposes a focused 3–5 step session plan for explicit approval before any work begins. Useful for complex sessions or when multiple paths are possible.

Unlike the deprecated `session:start`, this command is not part of the mandatory session lifecycle — it is an on-demand tool for consultants who want a structured plan before proceeding.

## Inputs

**Optional**: `$ARGUMENTS` — release folder name (e.g. `releases/01-discovery`). If not provided, uses the most recently modified release.

## Workflow

### Step 1: Enter Plan Mode

Immediately enter Plan Mode. Do not perform any file edits, run any commands, or generate any artifacts until the session plan has been explicitly approved.

### Step 2: Load Release and Engagement Context

1. Locate the active release (by argument, or most recently modified `status.md`)
2. Read `status.md` — current phase, artifact states, session history (last 3 rows), blockers
3. Read `engagement/context.md` if present — engagement overview and objectives
4. Scan `.wire/research/sessions/*/summary.md` — surface any recent research relevant to the current phase

### Step 3: Scope Alignment Check (discovery releases only)

If `release_type` is `discovery` and `primary_analytical_focus` is set in `status.md`, display it prominently and evaluate any stated objective against it. If the objective is adjacent to the primary focus, surface a challenge before proposing the plan.

If `release_type` is `sop_discovery`, display the current Maturity Curve pin (under `sponsor_validation.maturity_pin` once recorded) and the count of completed stakeholder interviews vs the stakeholder map total. Surface any interviews that are missing the mandatory four-tag set before proposing the plan — those gaps block the consolidation step.

### Step 4: Ask What the Consultant Wants to Accomplish

Output a brief context summary, then ask:

```
What do you want to accomplish in this session?
(Or press Enter to follow the suggested next focus from the last session)
```

### Step 5: Propose Session Plan

Based on release state, research, and the stated objective, propose a focused plan. **Every executable step names the Wire command that performs it**, or the skill when no command covers the step. A step that names neither is not a plan step; it is a description of an outcome, and it is how work ends up done by hand instead of through the command (wire#265).

```
## Proposed Session Plan

**Objective**: [stated objective or derived from suggested next focus]

| # | Step | Type | Command or skill | Scope | Produces |
|---|------|------|------------------|-------|----------|
| 1 | [what, in method terms] | command | /wire:<command> <release-folder> [flags] — the command in full, as it would be typed | [objects this step may touch] | [file, report, PR, decision] |
| 2 | [what] | skill | <skill-identifier> — no command covers this because [reason] | [scope] | [output] |
| 3 | [validation or review step] | command | /wire:<artifact>-validate <release-folder> | [scope] | PASS/FAIL report |
| 4 | [approval or hand-off] | human | external | decision | [who] | [what they decide] |

**Left out, and why**: [steps of the method this plan does not include, with the reason]

**Blocked by** (if applicable): [What needs resolving first]

Approve / Changes / Explain <step> / Cancel?
```

Step types: `command` (a `/wire:` command), `skill` (a Wire skill, only where no command covers the work; say why), `human` (something the consultant does), `external` (a client action, e.g. PR review), `decision` (a ruling by a named owner), `investigation` (read-only; nothing written).

On **Explain**, give the consequence of skipping that step in this release's own terms, not a general principle.

### Step 6: Wait for Approval

- **Approve**: exit Plan Mode and execute step 1 of the plan. **The approved commands are what runs.** Do not do by hand what a named command does. If a step's result changes what should happen next, stop, propose the amendment and wait; never add a step, widen a scope or substitute a command silently. A step that ran differently from the plan is recorded in the execution log's Detail as `deviation: <what differed>` (see `specs/utils/execution_log.md`), so `/wire:status-sync` can report it.
- **Changes**: incorporate feedback and re-present
- **Cancel** or a different objective: regenerate the plan, or stop

## Output

No files are created or modified during planning. After approval, executes the approved steps by running the commands the plan names. When invoked from `/wire:work`, the approved plan is also written to the iteration file (see `specs/work.md`).

Execute the complete workflow as specified above.
