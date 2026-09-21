---
description: Present migration batch acceptance pack for stakeholder sign-off
argument-hint: <release-folder> [--batch N 
---

# Present migration batch acceptance pack for stakeholder sign-off

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
    'command': 'migration-acceptance-pack-review',
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
command: review
artifact: migration_acceptance_pack
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Present migration batch acceptance pack for stakeholder sign-off
argument-hint: <release-folder> [--batch N | --wave id]

---

## Auto-Delegation

This is a **review command**. Do NOT delegate to a subagent. The workflow below must execute in the main session — it requires real-time human interaction to capture the reviewer's decision.

---

## Data Safety — Read Before Proceeding

Before proceeding, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT run INSERT, UPDATE, DELETE, CREATE TABLE, DROP, or TRUNCATE
  against the source platform. Query it only.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not write to these):
  [list each production project ID]
```

If the current working context would write to a source platform or a blocked production project, stop immediately and report the conflict.

---

# Migration Acceptance Pack — Review

## Purpose

Formal stakeholder sign-off on a completed migration batch. Once all models in a batch have reached a terminal state (PASSED or FAILED) in the iterative translation + equivalency loop, this command presents the acceptance pack to the reviewer and records their decision. It is the human gate before proceeding to the next batch — or, if all batches are complete, before beginning cutover preparation.

## Prerequisites

- `dbt_migration.batch_N_generate: complete` in status.md
- `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md` exists

## Flags

- `--batch N` — review the acceptance pack for topological batch N specifically (the `dbt_audit.batch_number` scheme — `acceptance_pack_batch_N.md`).
- `--wave <id>` — review the acceptance pack for execution wave `<id>` specifically (the `migration_batching.csv` scheme — `acceptance_pack_batch_{wave_id}.md`, since `dbt-migration-generate` Step 1w substitutes the wave id directly into the same `batch_{N}` filename template). Accepts zero-padded (`B01`) or bare (`1`) forms, normalised identically to `dbt-migration-generate`'s `--wave`. Wave-id form and normalisation are the shared contract in `specs/utils/wave_resolution.md` (normative; accepts `2`, `B02`, `b2`, or the `W02` display form). `--batch` and `--wave` read different numbering schemes and cannot be combined — abort if both are supplied: `[wire] --batch and --wave read different numbering schemes and cannot be combined. Pick one.`

## Workflow

### Step 1: Determine Which Batch to Review

1. If `--batch N` is supplied, use that batch number. If `--wave <id>` is supplied, normalise it (per the **Flags** section) and use the normalised wave id in place of `N` everywhere below (`acceptance_pack_batch_{wave_id}.md`, `migration_acceptance_pack.batch_{wave_id}_review`).
2. Otherwise, scan `.wire/releases/$ARGUMENTS/migration/dbt/` for all `acceptance_pack_batch_*.md` files — this glob already matches both topological-batch and wave-labelled filenames. For each, check status.md for `migration_acceptance_pack.batch_{N}_review`. Select the highest N where the review status is `pending` or absent (comparing wave ids and topological batch numbers as separate pools — don't interleave `B01` with `3`).
3. If no batch has a pending acceptance pack, list all batches and their current review status, then ask:
   ```
   All acceptance packs have been reviewed. Which batch would you like to re-review?
   Enter a batch number, or press Enter to cancel:
   ```
4. Load `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md`.

### Step 2: Retrieve Meeting Context

Follow `specs/utils/meeting_context.md`. Search for transcripts mentioning: "migration", "batch N", "acceptance", "sign-off", "equivalency".

If relevant meetings are found, output a brief bullet list — no more than five items — before presenting the acceptance pack. Label it clearly:

```
## Context from recent meetings
- [decision or action item — source: meeting title, date]
```

If no relevant meetings are found, proceed silently.

If a document store is configured, follow `specs/utils/docstore_fetch.md`:
- Pass `artifact_id: migration_acceptance_pack`, `artifact_name: acceptance_pack_batch_{N}`, `file_path: migration/dbt/acceptance_pack_batch_{N}.md`, and `project_id: $ARGUMENTS`
- Surface any reviewer comments added to the document store page since generation alongside the Fathom context

### Step 3: Present the Acceptance Pack

Output the full content of `acceptance_pack_batch_{N}.md`, then present the reviewer prompt:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[wire] Migration — Batch N Acceptance Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Acceptance pack content above]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reviewer — please confirm before responding:

  [ ] You have reviewed the model-by-model results table
  [ ] FAILED models have been noted and escalated, accepted
      as known gaps, or scheduled for a follow-up batch
  [ ] You are satisfied that PASSED models meet the
      equivalency thresholds agreed in the migration strategy

Your decision:

  A  Approve        — batch accepted, proceed to next batch
                      or cutover preparation
  R  Reject         — batch must be re-run or specific models
                      fixed before proceeding
  H  Hold           — accepted with reservations (list them);
                      proceed to next batch while tracking gaps

Enter A, R, or H:
```

Use `AskUserQuestion` for the decision:

```json
{
  "questions": [{
    "question": "What is your decision on Batch N?",
    "header": "Batch N Acceptance Decision",
    "options": [
      {"label": "Approve", "description": "Batch accepted — proceed to next batch or cutover preparation"},
      {"label": "Reject", "description": "Batch must be re-run or specific models fixed before proceeding"},
      {"label": "Hold", "description": "Accepted with reservations — list them; proceed to next batch while tracking gaps"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect Sign-Off Details

Ask:
```
Reviewer name (leave blank to use the engagement stakeholder name from status.md):
```

Read `engagement.stakeholder_map` from status.md if blank.

If the decision is **Reject** or **Hold**, ask:
```
Please describe the issues or reservations to record:
```

Capture:
- `decision` — Approve / Reject / Hold
- `reviewer` — name
- `date` — today's date (`YYYY-MM-DD`)
- `notes` — free-text feedback (Reject or Hold only; empty string for Approve)

### Step 5: Append Sign-Off Block to the Acceptance Pack

Append the following section to `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md`:

```markdown
## Sign-off

| Field | Value |
|-------|-------|
| Decision | APPROVED / REJECTED / HOLD |
| Reviewer | <reviewer name> |
| Date | <YYYY-MM-DD> |
| Notes | <feedback or reservations, or — if none> |
```

Substitute the actual values. Do not modify any earlier content in the file.

### Step 6: Update status.md

Write the following fields under `artifacts.migration_acceptance_pack`:

```yaml
artifacts:
  migration_acceptance_pack:
    batch_{N}_review: approved | rejected | hold
    batch_{N}_reviewer: "<reviewer name>"
    batch_{N}_review_date: "<YYYY-MM-DD>"
    batch_{N}_notes: "<feedback or empty>"
```

Use `approved`, `rejected`, or `hold` as the status value — lowercase, no spaces.

### Step 7: Output Review Summary and Next Steps

**If Approved**:

```
## Batch N — Accepted

Reviewed by: [reviewer], [date]

[If more batches remain:]
Next batch:
  /wire:dbt-migration-generate $ARGUMENTS --batch [N+1]

[If all batches are complete:]
All batches accepted. Proceed to cutover preparation:
  /wire:cutover-generate $ARGUMENTS
```

**If Rejected**:

```
## Batch N — Rejected

Reviewed by: [reviewer], [date]

Issues raised:
  [notes]

Re-run the batch after addressing the issues above:
  /wire:dbt-migration-generate $ARGUMENTS --batch N
```

**If Hold**:

```
## Batch N — Accepted with Reservations

Reviewed by: [reviewer], [date]

Reservations recorded:
  [notes]

Reservations are logged in status.md. Proceed to the next batch:
  /wire:dbt-migration-generate $ARGUMENTS --batch [N+1]

Track the reservations to resolution before cutover.
```

### Step 8: Post-Execution Hooks

Run the following in order:

1. **Execution log** — follow `specs/utils/execution_log.md`. Record the outcome as `approved`, `rejected`, or `hold`. Detail should include reviewer name.

2. **Jira sync** — follow `specs/utils/jira_sync.md`:
   - `release_folder`: `$ARGUMENTS`
   - `artifact`: `migration_acceptance_pack`
   - `action`: `review`
   - Status: the review outcome just written to status.md
   - Include reviewer name in the Jira comment; include feedback text if rejected or hold

3. **Doc store sync** — follow `specs/utils/docstore_sync.md` to push the updated acceptance pack (with sign-off block appended) to Confluence or Notion. Push regardless of decision — the sign-off record should be visible to all stakeholders in the document store.

4. **Auto-commit** — follow `specs/utils/commit.md`:
   - `release_folder`: `$ARGUMENTS`
   - `artifact`: `migration_acceptance_pack`
   - `action`: `review`

## Review Gate

Stakeholder sign-off on each batch's acceptance pack is required before proceeding to the next batch or to cutover preparation. The `/wire:cutover-generate` command will not proceed unless all batches show `batch_{N}_review: approved` or `batch_{N}_review: hold` in status.md. A `rejected` batch must be re-run and re-reviewed.

Execute the complete workflow as specified above.
