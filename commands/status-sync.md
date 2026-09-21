---
description: Reconcile recorded release state against evidence (git, execution log, disk, sprint plan) and repair the record with confirmation
argument-hint: [release-folder]
---

# Reconcile recorded release state against evidence (git, execution log, disk, sprint plan) and repair the record with confirmation

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
    'command': 'status-sync',
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
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: false
inputs:
  optional:
    - name: release_folder
      description: "Path to the release folder (inferred from the most recently modified status.md when omitted)"
description: Reconcile a release's recorded state — status.md, execution log, sprint plan — against evidence from git, disk, and the log itself, then repair the record with the consultant's confirmation
argument-hint: [release-folder]
delegates_to:
  - utils/execution_log
---

# Status Sync Utility

## Purpose

Wire's status maintenance is command-coupled: every generate/validate/review spec carries its own `status.md` and `execution_log.md` update steps, so work done **outside a command run** — conversational delivery, agent-assisted edits, direct commits — gets no state capture at all. This bites hardest in `custom` releases (whose lifecycle specs only exist if `/wire:custom-define` generated them) and in any engagement where substantial work is conversational rather than command-driven.

`/wire:status-sync` is the repair path: a single reconciler that diffs the *recorded* state against *reality* and fixes the record with the consultant's confirmation. It is a sibling to `/wire:status` — `status` reports the record as it stands; `status-sync` repairs the record when it has drifted. It is deliberately a single command, not a generate/validate/review triple: there is no artifact here, only reconciliation.

## Usage

```bash
/wire:status-sync [release-folder]
```

If `release-folder` is omitted, infer it from the most recently modified `.wire/releases/*/status.md` (the same inference `specs/utils/pr_create.md` uses). Accept both `releases/02-semantic-layers` and bare `02-semantic-layers` forms.

## Contract

These rules are binding on every step below:

1. **Never silent.** The command proposes repairs; the consultant confirms. No file is modified before an explicit confirmation.
2. **A drift report alone is a valid outcome.** Running the command and declining to apply is side-effect-free: no file writes, no log rows.
3. **The execution log is the primary evidence for what happened**; git history and files on disk are the evidence for what exists. Where the two conflict, present both and ask.
4. **Append-only history.** Never rewrite or delete existing execution-log rows or Session History rows. Backfilled log rows carry the sync's own timestamp, with the evidenced date recorded in the Detail column — never fabricate historical timestamps.
5. **Never auto-downgrade.** When the record claims more than the evidence supports (`record_ahead` below), ask the consultant to adjudicate; do not silently regress a recorded state.

## Evidence Sources and Repair Targets

| Evidence (read-only) | Repair target (written on confirmation) |
|---|---|
| `git log` since the last status touch, over `.wire/` and recorded artifact paths | Artifact lifecycle blocks (`generate`/`validate`/`review` values, `file`, `generated_date`, `generated_files`, `revision_history`) |
| `execution_log.md` rows | `last_updated` frontmatter (and the `**Last Updated**` body line) in every affected `status.md`, including the planning release's when the sprint plan moved |
| Artifact files on disk | Missing execution-log rows (backfilled per Contract rule 4) |
| The governing `sprint_plan.md` | Sprint-plan story Status columns and sprint/epic totals |
| | Session History rows |
| | The Next Action section |

## Workflow

### Step 1: Resolve the Release Folder

1. Resolve the release folder from the argument or the inference above.
2. Verify `.wire/releases/<release_folder>/status.md` exists. If not, stop: suggest `/wire:status` to list releases, or `/wire:new` if no engagement exists in this repo.

### Step 2: Load the Recorded State

1. Read `.wire/releases/<release_folder>/status.md`. Parse `last_updated` from the frontmatter and read the artifact lifecycle states **generically, per `specs/status.md` Step 2's "Reading artifacts generically" rules** — standard `artifacts:` map shape, the `droughty` step-status shape, the `agentic_data_stack` embedded-YAML-block shape, and `custom` releases (whose artifact keys are whatever `/wire:custom-define` decided). Do not hardcode an artifact list.
2. Read `.wire/releases/<release_folder>/execution_log.md` (may be missing — see Edge Cases).
3. Resolve the **governing sprint plan**:
   - If `.wire/releases/<release_folder>/planning/sprint_plan.md` exists, use it.
   - Otherwise scan every other `.wire/releases/*/planning/sprint_plan.md` for one whose Downstream Releases table or epic `Maps to:` lines name this release. If exactly one matches, use it — and note its owning release folder, whose `status.md` must also be touched if the plan is repaired.
   - If none or several match, list what was found and ask the consultant to pick (or to skip sprint-plan reconciliation).

### Step 3: Gather Evidence

Define the **evidence window** as everything dated on or after the recorded `last_updated` (date granularity — same-day work after the last touch is the common case). If `last_updated` is missing, the window is unbounded.

1. **Git**: `git log --since=<last_updated> --name-only -- .wire/releases/<release_folder>/ <recorded artifact paths>` where recorded paths come from each artifact's `file` and `generated_files` fields. Collect commit dates and touched paths.
2. **Disk**: for each artifact, check whether its recorded `file` path (or, when `file` is null, the release-type template's default output path for that artifact) exists on disk.
3. **Log**: collect execution-log rows inside the evidence window, mapped to (artifact, step) using the command-to-artifact derivation in `specs/status.md` Step 2 — including this release's own `custom-commands/` names for custom releases.

### Step 4: Classify Drift

This section is normative — the classification below is deterministic given the gathered evidence, and is what `wire/tests/core/validate_status_sync.py` tests.

**4a. Per artifact lifecycle step.** For each artifact and each of its *present* lifecycle keys (`generate`, `validate`, `review` — whichever exist on the block), determine the evidenced state:

1. If one or more log rows in the evidence window match this (artifact, step), the evidenced state is the **latest** such row's Result, mapped per `specs/utils/execution_log.md`'s vocabulary: `complete`, `pass`, `fail`, `approved`, `changes_requested`. Evidence source: `log`.
2. Otherwise, **for the `generate` step only**: if the artifact's output file exists on disk, the evidenced state is `complete`. Evidence source: `file`. (`validate` and `review` outcomes cannot be evidenced by file existence alone.)
3. Otherwise there is no evidence for this step.

Then classify:

| Condition | Category | Proposal |
|---|---|---|
| Evidenced state exists and equals the recorded value | `in_sync` | — |
| Evidenced state exists and differs from the recorded value, evidence source `log` | `record_behind` | Set the recorded value to the evidenced state (the log is authoritative inside the window — this includes evidenced `fail`/`changes_requested` over a recorded `pass`/`approved`) |
| Evidence source `file` (generate only) and recorded value is not `complete` | `record_behind` | Set `generate: complete`; fill `file`, `generated_date` (latest git commit date touching the path, else today), and `generated_files` from disk/git |
| No evidence, recorded `generate: complete`, and the recorded `file` path is non-null but missing on disk | `record_ahead` | Ask: confirm downgrade, correct the path, or keep as-is (Contract rule 5) |
| No evidence, any other recorded value | `in_sync` | — (absence of log rows alone never downgrades — history may predate the log) |

**4b. Lifecycle fields.** Independently of 4a, an artifact whose step is in a done state (`complete`/`pass`/`approved`) but whose block still holds `file: null`, `generated_date: null`, an empty `generated_files` where the template expects entries, or a literal `TBD` is classified `fields_incomplete` — the same field-level staleness `specs/utils/execution_log.md`'s Stale Status Check warns about. Proposal: fill from disk and git evidence.

**4c. `last_updated`.** The proposed value is the **maximum** of the recorded `last_updated`, the newest qualifying git commit date, and the newest qualifying log-row date. If the proposal is later than the recorded value, classify `last_updated_stale`. File modification times are not evidence — git dates and log rows only.

**4d. Sprint-plan stories and totals.** For each story row in the governing plan, the agent maps the story to its supporting evidence (the repaired artifact states from 4a, log rows, and commits touching paths the story's tasks describe) and summarises it as one signal — `complete` (all of the story's work evidenced), `partial` (some), or `none`. The mapping is judgment; the classification given the signal is not:

| Recorded Status | Evidence signal | Category | Proposal |
|---|---|---|---|
| `Done` | any | `in_sync` | — (never un-tick Done automatically) |
| `Blocked` | `complete` | `record_ahead` | Ask — the blocker may be stale, but that is the consultant's call |
| `Blocked` | `partial` / `none` | `in_sync` | — |
| anything else | `complete` | `record_behind` | Set Status to `Done` |
| `Not started` | `partial` | `record_behind` | Set Status to `In progress` |
| `In progress` | `partial` | `in_sync` | — |
| any | `none` | `in_sync` | — |

Totals: each epic subtotal and sprint total must equal the arithmetic sum of its story rows' points, and any "points done" figure must equal the sum of points on `Done` stories after the proposed repairs. A mismatch is classified `totals_stale` with the recomputed number as the proposal.

**4e. Session History and missing log rows.** Qualifying git commits (or repaired artifact states) with no corresponding execution-log row and no Session History row are classified `history_gap`. Proposal: one backfilled log row per evidenced-but-unlogged event, and one Session History row per evidenced work session (date, inferred objective, what was accomplished), both per Contract rule 4.

**4f. Execution-log row ordering.** Rows in `execution_log.md` are appended in
the order things happened, so each row's timestamp is greater than or equal to
the row above it (`specs/utils/execution_log.md`, rule 6). Walk the rows in
file order and compare each row's timestamp with its predecessor's:

| Condition | Category | Proposal |
|---|---|---|
| Every row's timestamp is greater than or equal to its predecessor's | `in_sync` | — |
| A row's timestamp precedes its predecessor's | `log_out_of_order` | Report both rows, in file order, with their timestamps. Ask; do not repair automatically |
| A row's timestamp is unparseable | `log_out_of_order` | Report the row and its position. It is neither in nor out of order; it cannot be compared |

The proposal is never "re-sort the file". Re-ordering an append-only log
destroys the evidence of what actually happened in what order, and the wrong
row could as easily be the one above. The repair is a decision: correct one
timestamp, or accept the pair as a known artefact of two writers. Observed
failure: out-of-order rows in both logs of a live migration, unnoticed because
nothing looked.

A log with fewer than two rows, or no log at all, is `in_sync` for this check.
Legacy five-column rows are compared on their Timestamp column like any other
row; missing `By`/`Session` columns are not a defect
(`specs/utils/execution_log.md`, "Legacy five-column rows").

### Step 5: Present the Drift Report

Present all findings before asking anything. Suggested shape:

```markdown
## Status Sync — Drift Report: <release_folder>

**Recorded last_updated**: 2026-08-19 · **Evidence through**: 2026-08-21

| # | Target | Drift | Proposed repair |
|---|--------|-------|-----------------|
| 1 | dbt.generate | record_behind (file: 12 models on disk, recorded not_started) | generate: complete, fill file/date/files |
| 2 | last_updated | last_updated_stale | 2026-08-19 → 2026-08-21 |
| 3 | Sprint 1 story "Staging models for X" | record_behind (evidence complete) | Status → Done |
| 4 | Sprint 1 total | totals_stale | points done 0 → 8 |
| 5 | execution_log.md | history_gap (2 commits, no rows) | backfill 2 rows |
| 6 | execution_log.md rows 41–42 | log_out_of_order (14:05 follows 15:40) | your call — correct one timestamp, or accept |

Items needing your call (record_ahead): none

Apply repairs 1–5? (yes / pick numbers / no)
```

If nothing drifted, report "Record and reality are in sync" and stop — write nothing.

### Step 6: Confirm and Apply

On explicit confirmation (all items, or the picked subset):

1. Apply artifact-block repairs. Append a `revision_history` entry on each repaired block noting the date and `status-sync` as the source.
2. Update `last_updated` (frontmatter and the `**Last Updated**` body line) in the release's `status.md` — and, if the sprint plan was repaired and lives in a different release, in that planning release's `status.md` too (with a `revision_history` entry on its `sprint_plan` block).
3. Apply sprint-plan story Status and totals repairs.
4. Append backfilled execution-log rows and Session History rows.
5. Recompute the Next Action section using `specs/status.md` Step 4's data-driven rule against the repaired states.

`record_ahead` items are resolved one at a time with the consultant, never batch-applied.

### Step 7: Log the Sync

After applying (and only then — a declined or empty sync writes nothing), append one execution-log row recording the sync itself, in `specs/utils/execution_log.md`'s format:

```markdown
| 2026-08-21 14:30 | /wire:status-sync | complete | 3 artifact repairs, 2 story updates, last_updated 2026-08-19 → 2026-08-21 |
```

## Edge Cases

- **No `execution_log.md`**: proceed on git and disk evidence alone; note it in the report and offer to create the log with backfilled rows.
- **No governing sprint plan found**: skip 4d, say so in the report. Not an error — not every release is governed by a sprint plan.
- **`last_updated` missing or unparseable**: treat the evidence window as unbounded and propose setting `last_updated` as part of the repair.
- **Shallow clone / no git history**: fall back to log and disk evidence; say so in the report.
- **Droughty releases**: steps are single-action (`status: not_started | complete`), so only rule 4a's file branch and 4c/4e apply — evidenced output on disk proposes `status: complete`.
- **Uncommitted changes on disk**: files on disk count as evidence even when uncommitted; note "uncommitted" in the report so the consultant knows the PR still needs them.

Execute the complete workflow as specified above.
