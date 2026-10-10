---
description: Read a release's tickets from Linear or Jira and propose the ticket map (kind, slices, Wire steps per ticket), using the Modality model where linked; turns on ticket delivery for the release
argument-hint: <release-folder> [--tracker linear
model: claude-fable-5
---

# Read a release's tickets from Linear or Jira and propose the ticket map (kind, slices, Wire steps per ticket), using the Modality model where linked; turns on ticket delivery for the release

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
    'command': 'tickets-import',
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
artifact: tickets
domain: tickets
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder the tracker project belongs to"
  optional:
    - name: tracker
      description: "--tracker linear|jira. Omitted: the tracker configured in status.md (linear: or jira: block); asked when both or neither are configured"
    - name: project
      description: "--project <name or key>. The Linear project or Jira project key and filter. Omitted: the one recorded in tickets.yaml, else the linear:/jira: block, else asked"
    - name: refresh
      description: "--refresh. Compare the tracker with the existing ticket map and propose new, changed and removed tickets"
description: "Read a release's tickets from Linear or Jira and propose the ticket map (each ticket's kind, slices and Wire steps), using the release's Modality model where one is linked; on confirmation write the map, the ticket records and delivery: tickets in status.md"
argument-hint: <release-folder> [--tracker linear|jira] [--project <name-or-key>] [--refresh]
delegates_to:
  - utils/ticket_delivery
  - utils/mml_import
  - utils/execution_log
  - utils/director_operating_model
workload: planning
---

# Wire Tickets Import Command

## Purpose

Turns on ticket delivery for a release (`specs/utils/ticket_delivery.md`). It
reads the tracker project for the release, proposes for each ticket the kind of
work, the slices it covers and the Wire steps it covers, and writes the ticket
map once the consultant confirms. Run again with `--refresh`, it lists what
changed in the tracker and asks before changing anything.

Wire could create tickets before 4.2.0 (`/wire:utils-linear-create`,
`/wire:utils-jira-create`) but not read them, so every link between a ticket
and the release was kept by hand and went out of date. This command is the
read path.

The lead consultant runs it, once the platform design is agreed and the release
is cut into tickets. It needs nothing from Modality: Modality is used only when
the release has `model_source: modality`.

## Usage

```bash
/wire:tickets-import <release-folder> [--tracker linear|jira] [--project <name-or-key>] [--refresh]

/wire:tickets-import 02-customer-core --tracker linear
/wire:tickets-import 03-acquisition --tracker jira --project GRO
/wire:tickets-import 02-customer-core --refresh
```

Accept both `releases/02-customer-core` and bare `02-customer-core`.

## Workflow

### Step 1: Resolve the release and the tracker

1. Locate `.wire/releases/<release-folder>/status.md`. If absent, stop: "No
   release at `<path>`. Run `/wire:new` first."
2. Resolve the tracker from `--tracker`, else from the `linear:` or `jira:`
   block in `status.md`. If both or neither are configured, ask.
3. Check the tracker's MCP server is reachable (Linear: `list_projects`;
   Jira: `getVisibleJiraProjects`). If it is not, stop and say which server
   failed and how to connect it. Do not fall back to typed-in tickets: a map
   built from memory is the hand-kept list this command replaces.
4. Resolve the tracker project from `--project`, else `tickets.yaml`'s
   `tracker_project`, else the `linear:`/`jira:` block, else list the
   tracker's projects and ask which belong to this release.
5. If `tickets.yaml` exists and `--refresh` was not given, say so and ask
   whether to refresh. Never overwrite a ticket map.

### Step 2: Read the tickets

- **Linear**: `list_issues` for the project, all states. For each issue read
  key, title, description, state, labels, milestone, estimate, URL and its
  "blocked by" relations.
- **Jira**: `searchJiraIssuesUsingJql` with `project = <KEY>` plus the release
  filter (fix version, epic or label recorded on the release). Same fields;
  "blocked by" from issue links of type Blocks.

Also list the tracker's other projects (or epics) that look like part of this
engagement but match no Wire release, for the "Not in any release" question in
Step 5.

### Step 3: Read the design model, if there is one

If `status.md` has `model_source: modality`, follow `specs/utils/mml_import.md`
to read the model at `modality_path`:

1. The conceptual objects (entities, derivations, metrics), the data products
   and the sources, with their types.
2. The model's own ticket links: a `task` block, a `ticket` or `tracker_key`
   key on an object, or a link file named in `modality_project.yaml`. Use them
   where they exist; do not ask about them.
3. Whether `modality/models/physical/` holds tables, and which.

Without `model_source: modality`, skip this step. Nothing needs Modality.

### Step 4: Propose kind, slices and steps

For each ticket, from its title and text:

1. Propose the **kind** (`specs/utils/ticket_delivery.md`, "Ticket kinds").
2. Propose the **slice** and its kind. With a Modality link, the slice is the
   linked object. Without one, propose a match to a model object, or a
   plain-text slice from the ticket's wording ("marketing spend in CPA: dbt").
3. For `review` tickets, name the reviewed steps from the text
   (`requirements.review`). For `layer`, `deliverable` and `batch` slices,
   name the steps from the text. Never guess either: ask.
4. Propose each slice's `depends_on` from the design (the physical or logical
   model with Modality; `design/data_model.md` and the ticket text without).

Write these proposals to a JSON file in the release's scratch area and run:

```bash
python3 <wire>/scripts/ticket_delivery.py propose <proposals.json>
```

The script applies the recipes, uses Modality links over proposals, drops
`data_model` from build tickets whose slice a design ticket covers, marks
every proposal that needs checking, lists plain work and lists tickets in
tracker projects that are not this release's. Use its output as the proposal;
do not re-derive it.

Every step named must exist in the release type's graph (or, for a `custom`
release, in `status.md`'s artifact keys). A step that does not is reported as
an import error and asked about.

### Step 5: Present the proposal

Present, before writing anything:

1. The tracker project, the ticket count and the points total.
2. Where the slices came from: the Modality model, or Wire's proposals from
   ticket text (then: "Please check the Slice column").
3. One table: Ticket | Title | Kind | Slice | Wire steps.
4. The questions from the script, numbered: proposed slices to check, plain
   work to confirm.
5. Order: each slice dependency the tracker has no "blocked by" link for, with
   the reason from the design, and an offer to add the link.
6. Not in any release: tracker projects with no matching Wire release, each
   with the choice: start a new release (`/wire:new`), add to an existing
   release, or ignore.
7. **confirm / adjust / cancel**.

On **adjust**, take the changes, re-run the script and present again. On
**cancel**, write nothing.

### Step 6: Write on confirmation

1. `tickets.yaml` in the release folder, in the shape of
   `specs/utils/ticket_delivery.md`, with `imported` and `imported_by`.
2. One ticket record per ticket in `iterations/<key>.md`, from `/wire:work`'s
   iteration file template, with the front matter block and `state: planned`.
   An existing record (a ticket already worked with `/wire:work`) is kept;
   its front matter is added if missing and its state is not changed.
3. `status.md`: `delivery: tickets`; the `## Slices` table from
   `ticket_delivery.py status <release> --markdown`; one `## Iterations` row
   per ticket.
4. `decisions.md`: one entry per answer that sets scope (a tracker project left
   out of every release, plain work agreed), with the consultant's name and
   reason, in the ruling format of `specs/utils/director_operating_model.md`.
5. Tracker links the consultant agreed to add: Linear `save_issue` with the
   relation, Jira `createIssueLink`. Only those agreed.
6. One execution-log row:
   `/wire:tickets-import | complete | <n> tickets, <k> slices, <p> plain, from <tracker> <project>`.

These are written on the release branch. The import is a release-record
change, not a ticket.

### Step 7: Refresh (`--refresh`)

1. Read the tracker as in Step 2 and propose as in Steps 3 and 4.
2. Run `ticket_delivery.py refresh <release> <new-proposal.json>`. It lists
   **new** tickets (with their proposal), **changed** tickets (title, kind,
   slices or steps, was and now) and **removed** tickets (cancelled or gone
   from the tracker, proposal: close the record as cancelled).
3. Present the table and ask **apply all / choose / cancel**.
4. On confirmation, update `tickets.yaml`, create records for new tickets,
   set `state: cancelled` on removed ones (never delete a record), rewrite
   `## Slices`, and log
   `/wire:tickets-import | complete | refresh: <n> new, <c> changed, <r> removed`.

A changed ticket that is already open keeps its plan. The change is shown on
its next `/wire:work` open as a plan amendment to consider.

## Output

End with a plain-language report: tickets and slices written, plain work,
questions answered and how, decisions recorded, tracker links added, and what
can start now (from `ticket_delivery.py runnable <release>`). Name the command
that ran in full, as it would be typed (operating model rule 7):

```
Ran: /wire:tickets-import 02-customer-core --tracker linear
```

## Edge cases

- **A ticket in two releases.** Each release's map holds it once; the slices
  differ. Ask which release owns each step.
- **Sub-issues.** A Linear sub-issue or Jira sub-task is part of its parent
  ticket unless it names its own deliverable. Ask when unclear.
- **No tickets.** Say so and write nothing.
- **Release built from statement-of-work deliverables** (`custom`). Steps come
  from `/wire:custom-define`'s deliverable-to-command mapping in `status.md`.
  A ticket that maps to no command is plain work, and its record says so.

Execute the complete workflow as specified above.
