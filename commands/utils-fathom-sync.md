---
description: Pull new Fathom call transcripts for this engagement's client into .wire/engagement/calls/, then extract findings
argument-hint: [--after YYYY-MM-DD] [--before YYYY-MM-DD] [--limit N] [--dry-run] [--no-findings]
---

# Pull new Fathom call transcripts for this engagement's client into .wire/engagement/calls/, then extract findings

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
    'command': 'utils-fathom-sync',
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
artifact: fathom_sync
domain: utils
release_types: []
action_type: utility
logs_execution: true
description: Pull new Fathom call transcripts and summaries into .wire/engagement/calls/, then extract findings
argument-hint: (engagement-level — no release-folder argument)

---

# Fathom Sync — Pull Call Transcripts and Extract Findings

## Purpose

Fetch meeting recordings from Fathom for the current engagement's client, writing transcripts, summaries, and action items into structured markdown files under `.wire/engagement/calls/`, then extracting an analytical findings document per call. This is the persistence counterpart to `specs/utils/meeting_context.md` (which does a live, ad-hoc Fathom search at review time) — this spec writes durable, committed artifacts once, so the whole team can read them later without re-querying Fathom.

Two callers, two modes:

- **Automatic mode** — invoked silently by `skills/fathom-sync/SKILL.md` once per session. No flags, no interactive output beyond a brief one-line note if something new was found. Never fires if `fathom_sync.enabled` is not `true` in `.wire/engagement/context.md`.
- **Manual mode** — invoked directly via `/wire:utils-fathom-sync [flags]`. Always runs when explicitly invoked, regardless of `fathom_sync.enabled` — running the command is itself the consent. Full flag support and a full report.

## Prerequisites

- Fathom MCP server configured and reachable. If not, **skip silently in automatic mode** (exactly like any other optional MCP integration elsewhere in Wire); in manual mode, tell the user plainly that Fathom isn't configured and stop.
- `.wire/engagement/context.md` must exist with `fathom_sync.client_domain` set to a real, non-RA domain (automatic mode only — see Step 2's safeguard; manual mode still requires a usable domain to search on, see below).

## Configuration (read from `.wire/engagement/context.md`)

```yaml
fathom_sync:
  enabled: false          # resolved at /wire:new Step 2 from the client domain given, or set manually later
  client_domain: null     # required for enabled: true — matches calendar invitees, never rittmananalytics.com
  last_synced: null       # ISO date; drives the default --after window for incremental pulls
```

## Workflow

### Step 1: Parse Arguments (manual mode only)

| Flag | Default | Description |
|------|---------|--------------|
| `--after` | `fathom_sync.last_synced`, or engagement `created_date` if never synced | Only fetch calls after this date (YYYY-MM-DD) |
| `--before` | today | Only fetch calls before this date (YYYY-MM-DD) |
| `--limit` | `50` | Max calls per search page |
| `--dry-run` | false | List calls without writing files |
| `--no-findings` | false | Skip findings extraction |

In automatic mode, use the defaults for all of these — no flags are ever passed.

### Step 2: Resolve the Search Domain — and Refuse Unsafe Ones

**This is the step that stops RA-internal meetings ending up in a client (or any) repo. Do not skip or soften it, in either mode.**

1. Read `.wire/engagement/context.md`'s `fathom_sync.client_domain`.
2. **If it's blank/unset**: automatic mode skips silently (nothing to search on safely). Manual mode: ask the user for a client domain directly (`What's the client's email domain? e.g. acme.com`) — do **not** fall back to searching by `client_name` as free text in either mode. A text search on a company name can't distinguish "this specific client" from any other meeting that happens to mention the same words, and the whole point of this step is a filter narrow enough to trust.
3. **If it resolves to Rittman Analytics' own domain** (`rittmananalytics.com`, case-insensitive, or any subdomain of it) **— or if `client_name` is self-referential** ("Rittman Analytics", "RA", or a close variant) — refuse outright, regardless of mode or what `fathom_sync.enabled` says:
   - Automatic mode: skip silently, exactly as if `fathom_sync.enabled` were `false`. Do not log this as an error — it's a correct refusal, not a failure.
   - Manual mode: tell the user plainly why —
     ```
     This engagement's client domain resolves to Rittman Analytics' own domain (or the
     client name looks self-referential). Fathom Sync matches by calendar-invitee domain
     — your own domain is on every meeting your team has, internal or client-facing, so
     it can't safely narrow anything here. Refusing to run rather than pulling in
     unrelated internal meetings. If this genuinely is an external client whose name or
     domain happens to look like this, double-check .wire/engagement/context.md's
     client_domain and client_name before re-running.
     ```
   - Stop. Do not proceed to Step 3 under any circumstances once this check has triggered — this overrides everything else in this spec, including an explicit manual invocation with flags.
4. Otherwise, a real external domain is confirmed — proceed to Step 3 using it as the search filter.

### Step 3: Search Fathom

Use the Fathom MCP server's meeting-listing/search tools (`search_meetings`, `list_meetings`, or whichever the connected server actually exposes — inspect what's available rather than assuming a fixed signature) to find candidate meetings within the `--after`/`--before` window whose calendar invitees include the confirmed `client_domain` from Step 2:

- If the tool accepts a domain/company filter directly, use it.
- If it only accepts a free-text term, search on `client_domain` (not `client_name` — the domain is the thing Step 2 confirmed is safe) and, from the results, keep only meetings with at least one calendar invitee whose email matches that domain, discarding the rest client-side.
- Filter results to the date window client-side if the tool doesn't support date filtering natively.
- Paginate through all matching pages if the tool returns a cursor/next-page token; keep going until exhausted.

Collect all candidate meetings (title, date, recording ID, attendees, URL) — full transcript/summary content is fetched per-meeting in Step 5, not here. A candidate with zero invitees actually matching `client_domain` (a false positive from a text search) does not count as a match — discard it rather than writing it.

### Step 4: Filter to New Meetings Only

**Filename convention**: `YYYY-MM-DD_<sanitized-title>.md` under `.wire/engagement/calls/` — sanitize the title (lowercase, spaces to hyphens, strip non-alphanumeric except hyphens, truncate to 60 chars).

For each candidate meeting, check whether a file with that name already exists. If so, skip it — never overwrite an existing call file. Only meetings with no existing file are "new" and proceed to Step 5.

If `--dry-run`, list what would be fetched (title, date, new vs. already-present) and stop here without writing anything.

### Step 5: Fetch and Write Each New Meeting

For each new meeting, fetch the full transcript, summary, and action items (via `get_meeting_transcript`, `get_meeting_summary`, or whatever the connected MCP server's equivalent tools are named), then write:

```markdown
---
title: "{meeting.title}"
date: "{meeting.created_at}"
recording_id: {meeting.recording_id}
url: "{meeting.url}"
share_url: "{meeting.share_url}"
recorded_by: "{meeting.recorded_by.name}"
attendees:
{for each calendar_invitee}
  - name: "{invitee.name}"
    email: "{invitee.email}"
    external: {invitee.is_external}
{end for}
---

# {meeting.title}

**Date:** {formatted date}
**Recorded by:** {meeting.recorded_by.name}
**Attendees:** {comma-separated list of invitee names}
**Recording:** {meeting.url}

## Summary

{meeting summary, markdown-formatted — or "No summary available."}

## Action Items

{for each action_item}
- [ ] {action_item.description} — *{action_item.assignee.name}* ({action_item.recording_timestamp})
{end for}
{if no action items: "No action items recorded."}

## Transcript

{for each transcript_item}
**{speaker.display_name}** ({timestamp}):
{text}

{end for}
{if no transcript: "No transcript available."}
```

Ensure `.wire/engagement/calls/` exists before writing. If a meeting has no transcript or summary available, still write the file with the placeholder text shown above rather than skipping it — a partial record is better than none.

### Step 6: Extract Findings (skip if `--no-findings` or `--dry-run`)

For each **newly written** call file only (never for calls that were already on disk before this run):

**Filename**: same base name as the call file, with `_findings` appended before `.md`. Skip if it already exists (shouldn't happen for a genuinely new call file, but check anyway — never overwrite).

**How**: Read the full call file (summary, action items, transcript). Before writing, read 2–3 of the most recent existing `*_findings.md` files in `.wire/engagement/calls/` as style and structure references — match their voice, depth, and section conventions rather than inventing a new format each time. If this is the very first call synced for this engagement, use the structure below as-is.

**Structure**:

```markdown
# Findings: {meeting.title} — {short subtitle describing the call's focus}

**Date:** {date}
**Recording:** [Fathom]({meeting.url}) | [Share Link]({meeting.share_url})
**Attendees:** {name (role)} for each attendee, noting silent/absent/partial attendance
**Duration:** ~{duration}
**Purpose:** {1–2 sentence summary of the call's goal and context relative to prior sessions}

---

## 1. {First topic heading}

{Narrative analysis — not a transcript rehash. Explain what was discussed, what was decided, and why it matters. Include direct quotes where they capture a decision, insight, or strong opinion. Attribute quotes.}

---

[... one numbered section per major topic, sub-headings (###) for sub-topics ...]

## N-2. Decisions Captured

| # | Decision | Owner |
|---|----------|-------|
| 1 | **{Decision}** — {brief context} | {Owner} |

## N-1. Open Questions / Follow-ups

{Table or list of unresolved questions, with context and owner.}

## N. Action Items

- [ ] **{Owner}:** {Action description}
```

**Guidelines**:
- Synthesise, don't summarise — the call file already has the raw summary; findings add analytical value (what changed, what was decided, what it means downstream).
- Connect to prior sessions where the conversation builds on or reverts earlier decisions.
- Attribute decisions and quotes: `> *"quote"* — Name`.
- Skip small talk and off-topic segments.
- Be opinionated about implications — state what a decision means for downstream artifacts, releases, or architecture, don't just record that it happened.

### Step 7: Update Sync State

Update `.wire/engagement/context.md`'s `fathom_sync.last_synced` to today's date (or the latest meeting's date if it's later than today for any reason — shouldn't happen, but don't regress the marker).

### Step 8: Report

**Automatic mode**: if zero new meetings were found, say nothing at all — this is the expected, common outcome for most sessions. If one or more were found, one brief line: `Synced N new Fathom call(s) into .wire/engagement/calls/.`

**Manual mode**: always report in full, regardless of whether anything new was found:

```
## Fathom Sync Complete

- **Calls found:** {total candidates in window}
- **Files written:** {written} (skipped {skipped} — already on disk)
- **Findings written:** {findings_written} (skipped {findings_skipped})
- **Date range:** {after} to {before}
- **Output:** .wire/engagement/calls/

### Calls
| Date | Title | Recording ID | Call File | Findings |
|------|-------|---------------|------------|----------|
| ... | ... | ... | written/skipped | written/skipped |
```

## Error Handling

- Fathom MCP not reachable: skip silently (automatic) or tell the user plainly and stop (manual) — never treat this as a bug.
- No `client_domain` in context.md: same treatment as above (Step 2).
- `client_domain` resolves to Rittman Analytics' own domain, or `client_name` looks self-referential: refused, per Step 2 — not an error, a correct outcome.
- A meeting with no transcript or summary: write the file anyway with placeholder text (Step 5) — never skip a meeting just because part of it is missing.
- Never fail silently in manual mode — every error gets a clear, direct message. In automatic mode, never surface an error to the user at all; log nothing, just don't sync this session and try again next session.

## Notes

- This spec never manages a Fathom API key directly — it goes through the Fathom MCP server, configured once per user via `/mcp` (Claude Code) or `gemini mcp` (Gemini CLI), same as every other MCP-backed Wire feature.
- To change which client's calls sync for this engagement, edit `fathom_sync.client_domain` directly in `.wire/engagement/context.md`. Step 2's safeguard re-runs on every invocation, so an edit that resolves to RA's own domain is refused the same way it would be at `/wire:new`.
- The findings-extraction step (Step 6) is the most valuable and most expensive part of this workflow — it's a genuine analytical pass over each transcript, not a mechanical extraction. This is deliberately not skipped by default; use `--no-findings` (manual mode) if you want the raw call files without it.

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
