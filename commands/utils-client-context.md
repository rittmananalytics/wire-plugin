---
description: Gather external client context from Slack, HubSpot, Harvest, Jira, Confluence and Fathom
argument-hint: <client-name>
---

# Gather external client context from Slack, HubSpot, Harvest, Jira, Confluence and Fathom

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
    'command': 'utils-client-context',
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
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Gather external context about a client from Slack, HubSpot, Harvest, Jira, Confluence, and Fathom
argument-hint: <client-name>

---

# Client Context Utility

## Purpose

Fetch a structured summary of everything known about a client from all external systems: Slack discussion, HubSpot deal state, Harvest project hours, Jira issues, Confluence documentation, and Fathom call recordings.

This utility is called automatically by `/wire:adopt` (Phase 2) and can also be invoked by review commands, `/wire:status`, or any other Wire command that needs a current external-sources picture of the client. All sources are optional — the utility degrades gracefully if a source is unavailable or returns no results.

## Usage

```bash
/wire:utils-client-context <client-name>
```

Can also be invoked automatically by commands that need external client context. In that case, `client_name` is passed from the calling command's engagement context.

## Prerequisites

- `client_name` must be provided (or derivable from `.wire/engagement/context.md`)
- At least one external MCP source should be configured; all are optional

---

## Workflow

### Step 1: Resolve Client Name and Known Metadata

If called standalone without an argument, check `.wire/engagement/context.md` for `client_name`. If not found, ask:
```
What is the client name? (used to search all external sources)
```

Derive a normalised search slug: lowercase, hyphens for spaces, strip common suffixes ("Corporation", "Ltd", "Inc", "Limited", "Group").

Examples:
- "Acme Corporation" → `acme`
- "Client M Marketing" → `power-digital`
- "a prior client" → `hunke`

Store both `client_name` (display) and `client_slug` (search).

**Client directory fast-path**: Before doing any fuzzy channel searching, check whether a client directory is available at `wire/skills/engagement-status-report/references/client_directory.md`. If the client name matches a known entry, use the pre-confirmed values directly:
- `email_domain` — used for Fathom domain-filtered listing
- `slack_channel` and `slack_channel_internal` — exact channel names or IDs, skip fuzzy search
- `jira_project_key` — skip Jira text search, query by key directly
- `delivery_lead` — used to interpret Harvest and Fathom results

If no directory match, proceed with fuzzy derivation. Store `email_domain` if found (needed for Fathom).

---

### Step 2: Parallel Source Queries

Dispatch all source queries simultaneously. Each source is independent; none blocks another except Harvest which requires the HubSpot deal ID.

#### Source A: Slack

1. Use `slack_search_channels` to find candidate channels matching:
   - `clients-[client_slug]`
   - `clients-[first_word_of_slug]`

   Try both hyphen (`-`) and underscore (`_`) separators. Collect all channels whose names start with `clients-` and contain the client slug or first word.

2. Identify:
   - **Client-facing channel**: closest match to `#clients-[slug]`
   - **Internal channel**: closest match to `#clients-[slug]-internal` or `#clients-[slug]_internal`

   If multiple candidates exist for either, prefer the channel with more recent activity.

3. For each identified channel, use `slack_read_channel` to fetch messages from the last 60 days.

4. **Also read these internal company-wide channels** — they contain high-signal delivery status that doesn't appear in client channels:
   - **`#shopfloor`**: end-of-day updates from delivery leads. These follow a Move / Stuck / Watch structure and are the most direct indicator of real daily progress. Search for the client name within this channel.
   - **`#delivery-and-invoicing`**: milestone ETAs and invoicing readiness checks, typically posted by Mark or Lewis. Search for the client name. Confirmed dates here are authoritative.

   Use `slack_search_public_and_private` with `[client_name]` scoped to each of these channels for the last 60 days. Do not read the full channel history — search within it.

5. Extract:
   - `last_message_date`: most recent message timestamp (client channels)
   - `active_participants`: unique senders in last 60 days
   - `blocker_signals`: messages containing "blocked", "waiting on", "issue", "problem", "stuck", "delayed", "at risk", "paused" (return up to 5 with dates)
   - `decision_signals`: messages containing "decided", "agreed", "confirmed", "signed off", "approved", "go ahead" (return up to 5 with dates)
   - `recent_summary`: last 10 messages from each channel, each as a one-line summary with date
   - `shopfloor_signals`: EOD updates mentioning this client from `#shopfloor` (Move / Stuck / Watch items)
   - `delivery_invoicing_signals`: milestone or ETA mentions from `#delivery-and-invoicing`

6. **Fail gracefully**: if Slack MCP is unavailable, return `slack: {status: "not_available"}`. If no matching channels found, return `slack: {status: "no_channels_found", searched: [list of names tried]}`.

#### Source B: HubSpot

1. Use `search_crm_objects` on the Deals object, searching by client name:
   - Filter: `dealname` contains `client_slug` or `client_name`
   - Return all matches with `dealstage`, `amount`, `closedate`, `hs_lastmodifieddate`

2. If zero results, try searching by first word of client name only.

3. If multiple deals found, select the most recently modified active deal. If all appear closed or if selection is ambiguous, return all candidates and let the calling command decide (do not block).

4. For the selected deal, retrieve:
   - `deal_id`: HubSpot internal deal ID
   - `deal_name`: deal name
   - `deal_stage`: pipeline stage
   - `deal_value`: contract amount
   - `close_date`
   - `deal_description`: notes/description field
   - `associated_contacts`: list of contact names and roles
   - `recent_activity`: last 5 CRM activity notes (type, date, summary)

5. **Fail gracefully**: return `hubspot: {status: "not_available"}` or `hubspot: {status: "no_deal_found"}`.

#### Source C: Atlassian (Jira + Confluence)

**Jira:**
1. Use `searchJiraIssuesUsingJql`:
   ```
   text ~ "[client_name]" ORDER BY updated DESC
   ```
   Also try `project ~ "[client_slug]"` if no results.

2. For each matched project/epic, retrieve:
   - Project name and key
   - Issue count by status category (To Do / In Progress / Done)
   - Most recently updated 10 issues (summary, status, assignee, updated date)
   - Any issues with labels or summaries matching Wire artifact names

3. Return: `jira_projects`, `issue_counts_by_status`, `recent_issues`, `wire_artifact_issues`.

**Confluence:**
1. Use `searchConfluenceUsingCql`:
   ```
   text ~ "[client_name]" ORDER BY lastModified DESC
   ```

2. For each result, record: page title, space key, last modified date, URL, and a short excerpt.

3. Map page titles to Wire artifact categories using the keyword table:

   | Keywords in title | Wire artifact |
   |-------------------|---------------|
   | requirements, scope, brief, SOW, specification | `requirements` |
   | pipeline, architecture, data flow, ingestion, ETL | `pipeline_design` |
   | data model, ERD, entity, dimensional | `data_model` / `conceptual_model` |
   | dashboard, mockup, wireframe, report spec | `mockups` / `dashboards` |
   | deployment, go-live, runbook, cutover | `deployment` |
   | training, enablement, handover, onboarding | `training` / `documentation` |
   | test plan, UAT, acceptance | `uat` |
   | discovery, findings, playback, stakeholder | `findings_playback` / `requirements_matrix` |

4. Return: `confluence_pages` with `wire_artifact_hint` field per page.

5. **Fail gracefully**: return `atlassian: {status: "not_available"}`.

#### Source D: Fathom

**Important — two-connector model**: Fathom is split across two MCP servers with different capabilities. Use both:
- **`Fathom_2`** (n8n-hosted custom server) — use for `list_meetings`. Supports `calendar_invitees_domains` filtering, which is the most reliable way to find client-specific meetings.
- **`Fathom`** (official api.fathom.ai server) — use for `get_meeting_transcript`, `get_meeting_summary`, `get_recording_by_url`. Do not call `list_meetings` on this connector unless `Fathom_2` is unavailable.

If a listing call errors with a schema mismatch, the wrong connector is being addressed.

1. **List client meetings** using `Fathom_2:list_meetings`:
   - If `email_domain` is known: `calendar_invitees_domains=[email_domain]`, `created_after=90 days ago`, `limit=25`
   - If no domain known: fall back to `Fathom_2:search_meetings` with `client_name` as search term, then `Fathom:search_meetings` as backup. Deduplicate by recording ID.

2. **Prioritise which meetings to read** — fetch at most 3 transcripts to stay within tool-call budgets. Default priority:
   - **Sprint review / Sprint Changeover** — richest source for delivery status in steady-state engagements
   - **Sprint planning** — shows what was committed and what was deferred
   - **Workshop, definition session, executive 1:1** — outranks sprint ceremonies when the engagement is in flux; watch for these signals in Slack before deciding which meetings to pull
   - **Daily scrums** — lowest priority; skip unless no other meetings available

   Override the default when Slack signals (from Source A) suggest something significant happened: suspension, scope change, executive escalation, definition workshop. In those cases, pull the meetings where the decision was made, not the routine sprint ceremonies.

3. **Retrieve summaries and transcripts** using `Fathom:get_meeting_summary` for the top 3 prioritised meetings. If action items or decisions need more detail, use `Fathom:get_meeting_transcript`.

4. Extract:
   - `last_call_date`: most recent client meeting date
   - `call_participants`: unique names across retrieved meetings
   - `key_decisions`: extracted from summaries
   - `open_action_items`: extracted from summaries (action items not marked complete)
   - `recent_calls`: list of up to 5 calls with title, date, and one-line summary
   - `engagement_state_signal`: infer from meeting patterns — `steady_state_sprint`, `discovery`, `closeout_suspension`, or `mobilisation`

5. **Fail gracefully**: return `fathom: {status: "not_available"}` or `fathom: {status: "no_meetings_found"}`. Never block the calling command.

#### Source E: Harvest (Sequential — requires Source B deal_id)

Wait for Source B to return before dispatching this query.

1. Use `Get_data_of_all_projects` and filter by client name. Also check if `deal_name` from HubSpot matches any project name.

2. If no project found by client name, try matching on `deal_id` if Harvest stores deal references (some implementations do).

3. For the matched project, retrieve:
   - `harvest_project_id`
   - `budget_hours`: total budgeted hours
   - `logged_hours`: total hours logged to date
   - `budget_pct`: percentage of budget consumed
   - `last_entry_date`: date of most recent time entry (use `Get_data_of_all_time_entries` sorted by date descending, limit 1)
   - `active_members`: team members with time entries in last 30 days

4. Use `Get_data_of_all_time_entries` for this project grouped by task to produce:
   - `hours_by_task`: list of `{task_name, hours_logged}` sorted by hours descending
   - `wire_task_map`: attempt to map each task name to a Wire artifact (fuzzy match on task name vs. Wire artifact keyword table)

5. **Fail gracefully**: return `harvest: {status: "not_available"}` or `harvest: {status: "no_project_found"}`.

---

### Step 3: Assemble and Return Context Object

Return a single structured context object:

```
ClientContext {
  client_name: string
  client_slug: string
  email_domain: string | null              # e.g. "acme.com" — used for Fathom domain filter
  retrieved_at: ISO-8601 timestamp
  sources: {
    slack: {
      status: "ok" | "not_available" | "no_channels_found"
      client_channel: string | null        # e.g. "#clients-acme"
      internal_channel: string | null      # e.g. "#clients-acme-internal"
      last_message_date: date | null
      active_participants: string[]
      blocker_signals: [{date, summary}]
      decision_signals: [{date, summary}]
      recent_summary: [{date, text}]
      shopfloor_signals: [{date, summary}]         # Move/Stuck/Watch items from #shopfloor
      delivery_invoicing_signals: [{date, summary}] # ETAs and milestone confirms from #delivery-and-invoicing
    }
    hubspot: {
      status: "ok" | "not_available" | "no_deal_found" | "multiple_candidates"
      deal_id: string | null
      deal_name: string | null
      deal_stage: string | null
      deal_value: number | null
      close_date: date | null
      deal_description: string | null
      associated_contacts: [{name, role}]
      recent_activity: [{type, date, summary}]
      candidates: [...] | null             # populated if multiple_candidates
    }
    jira: {
      status: "ok" | "not_available" | "no_issues_found"
      projects: [{key, name}]
      issue_counts: {todo: N, in_progress: N, done: N}
      recent_issues: [{summary, status, assignee, updated}]
      wire_artifact_issues: [{summary, artifact_hint, status}]
    }
    confluence: {
      status: "ok" | "not_available" | "no_pages_found"
      pages: [{title, space, url, last_modified, wire_artifact_hint}]
    }
    fathom: {
      status: "ok" | "not_available" | "no_meetings_found"
      last_call_date: date | null
      call_participants: string[]
      key_decisions: string[]
      open_action_items: string[]
      recent_calls: [{title, date, summary}]
      engagement_state_signal: "steady_state_sprint" | "discovery" | "closeout_suspension" | "mobilisation" | null
    }
    harvest: {
      status: "ok" | "not_available" | "no_project_found"
      harvest_project_id: string | null
      budget_hours: number | null
      logged_hours: number | null
      budget_pct: number | null
      last_entry_date: date | null
      active_members: string[]
      hours_by_task: [{task_name, hours_logged}]
      wire_task_map: [{task_name, wire_artifact, confidence}]
    }
  }
  summary: {
    last_real_activity_date: date         # best available from Harvest > git > Jira > Slack
    last_real_activity_source: string
    sources_available: string[]           # list of sources that returned "ok"
    sources_unavailable: string[]
  }
}
```

---

### Step 4: Output (when called standalone)

When invoked directly via `/wire:utils-client-context`, render the context object as a readable markdown report:

```markdown
## Client Context — [client_name]
Retrieved: [timestamp]

### Sources
| Source | Status | Key Signal |
|--------|--------|------------|
| Slack #clients-[slug] | ✅ / ⚠️ | Last message: [date] |
| Slack #clients-[slug]-internal | ✅ / ⚠️ | [signal or "not found"] |
| HubSpot | ✅ / ⚠️ | [deal name], stage: [stage] |
| Harvest | ✅ / ⚠️ | [N]h logged ([X]%), last entry: [date] |
| Jira | ✅ / ⚠️ | [N] issues ([N] done) |
| Confluence | ✅ / ⚠️ | [N] pages |
| Fathom | ✅ / ⚠️ | [N] calls, last: [date] |

### Last Real Activity
[date] (source: [source])

### Recent Signals
**Slack**: [summary of recent discussion]
**Harvest**: [hours summary, last entry date]
**Fathom**: [last call summary, open action items]

### Open Action Items (from Fathom)
- [ ] [action item] ([meeting], [date])

### HubSpot Deal
[deal name] — [stage] — [value] — [close date]

### Harvest Budget
[N]h of [total]h logged ([X]%)
Hours by phase: [table]
```

When called from another command (not standalone), return the structured `ClientContext` object directly without rendering — the calling command is responsible for formatting and using the data.

---

## Fail-Safe Behaviour

This utility must never block a calling command. If all external sources fail simultaneously:

```
⚠️ Client context: all external sources unavailable.
Sources tried: Slack, HubSpot, Jira, Confluence, Fathom, Harvest
Proceeding without external context.
```

Return a `ClientContext` object with all sources set to `not_available` and `sources_available: []`.

Execute the complete workflow as specified above.
