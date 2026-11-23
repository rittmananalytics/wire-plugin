---
description: "Read a release's tickets from Linear or Jira and propose the ticket map (kind, slices, Wire steps per ticket), using the Modality model where linked; turns on ticket delivery for the release"
argument-hint: "<release-folder> [--tracker linear|jira] [--project <name-or-key>] [--refresh]"
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
6. Resolve the release filter (wire#423). One tracker project often holds the
   tickets of several Wire releases, so each release records which tickets
   are its own. Run `ticket_delivery.py filter <release>`:
   - `ok`: use the filter it prints, with no prompt. This is every
     `--refresh` after the first import.
   - `marker_only`: `jira.release` is set in `status.md` and no import has
     used it yet. Use it, and say so.
   - `unset`: ask once: "Which tickets in `<project>` belong to this release?
     A Jira release (Fix versions), a label, or a JQL clause." Offer the Jira
     release named after the Wire release as the default. A release that
     owns the whole tracker project answers "all of them", and no filter is
     saved.
   - `differs`: `jira.release` in `status.md` and the filter the last import
     used are not the same. Stop, show both, and ask which is right. Change
     nothing until the consultant answers.

   `jira.release` in `status.md` is the source; `tracker_filter` in
   `tickets.yaml` records the filter the last import used. `jira.epic_key`
   keeps its meaning and is never the filter: a release spans several epics,
   and epics stay free for grouping work.

### Step 2: Read the tickets

- **Linear**: `list_issues` for the project, all states. For each issue read
  key, title, description, state, labels, milestone, estimate, URL and its
  "blocked by" relations.
- **Jira**: `searchJiraIssuesUsingJql` with the `jql` that
  `ticket_delivery.py filter <release>` prints: the project, narrowed by the
  release filter from Step 1 (a Jira release through Fix versions, a label,
  or a JQL clause). With no filter, `project = "<KEY>"`. Same fields, plus
  each ticket's Fix versions; "blocked by" from issue links of type Blocks.

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

A ticket whose description has both a `Kind:` line and a `Wire step:` line
states its kind and Wire steps (tickets written from a ticket template; plain
work says `Wire step: none`). Read those lines instead of proposing them: put
the ticket's description in the proposals file as `description`, and the
script uses the stated kind and steps and marks the entry
`kind_source: ticket`. The slice is still proposed as below. A ticket without
both lines, which is every ticket a person writes, takes the proposal route
unchanged.

For each other ticket, from its title and text:

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

The script reads stated kinds and steps, applies the recipes, uses Modality links over proposals, drops
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
6. Held by another release: run `ticket_delivery.py overlap <release> --keys
   <keys.json>` with the keys about to be mapped. For each ticket it lists,
   name the release that already holds it and ask: leave it there (the
   default, and it is dropped from this import), move it here, or keep it in
   both and say why. Never map a ticket twice without the consultant's
   answer.
7. In no tracker release, or in two: when the filter is a Jira release, list
   once the project's tickets that are in no Wire release's Jira release, or
   in more than one, with the question "which release?". Write the answer to
   the ticket's Fix versions only after the consultant confirms; a list of
   tickets is confirmed once, not ticket by ticket.
8. Not in any release: tracker projects with no matching Wire release, each
   with the choice: start a new release (`/wire:new`), add to an existing
   release, or ignore.
9. **confirm / adjust / cancel**.

On **adjust**, take the changes, re-run the script and present again. On
**cancel**, write nothing.

### Step 6: Write on confirmation

1. `tickets.yaml` in the release folder, in the shape of
   `specs/utils/ticket_delivery.md`, with `imported` and `imported_by`.
   `tracker_filter` holds the filter this import used (`{kind: release |
   label | jql, value: ...}`); it is left out when the release owns the whole
   tracker project. When the filter is a Jira release and `jira.release` in
   `status.md` is empty, set it to the same name.
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

1. Read the tracker as in Step 2, with the saved filter from Step 1 and no
   prompt, and propose as in Steps 3 and 4.
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
| YYYY-MM-DD HH:MMZ | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
```

### Field Definitions

- **Timestamp**: Current date and time **in UTC**, written `YYYY-MM-DD HH:MMZ`
  (24-hour, a literal `Z` after the minutes, no `T`, no seconds, no offset):
  `2026-10-17 14:05Z`. Get it with `date -u +"%Y-%m-%d %H:%MZ"` (or
  `python3 <wire>/scripts/log_time.py now`), never from the local clock. The
  same form is used for every time written into a log row, including an
  original time quoted in Detail (`ran 2026-10-17 14:28Z`), in the release log
  and in ticket run logs. From Wire 4.4.3; see "Time zones" below.
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
  - `blocked` — `specs/utils/precondition_gate.md` Step 2 stopped the command on an unmet blocking precondition and the consultant chose not to override; Detail is `gate: <dep_artifact>.<dep_action> required <outcome>, was <actual>` and the Command cell carries the command in full. The Wire mod's commands band shows these rows as `Not run: <command>, gate: <...>`
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

  When a persona is set for the run (`specs/utils/personas.md`), add
  ` as <persona>` to the value: `typed as delivery-manager`,
  `orchestrator [a1b2c3] as delivery-manager`. No persona: the value alone.

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
| YYYY-MM-DD HH:MMZ | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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
   Rows are compared as "Time zones" below says.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Update `status.md` keys in place, then check the file.** When a command
   records a result in `status.md`, it changes the existing key; it never adds
   a second copy of a key in the same block. A value worth keeping (an earlier
   approval date) moves to a `prior_<key>` field or stays in this log, never
   in a duplicate key, because YAML keeps only the last copy and ignores the
   first without an error (wire-plugin#2). The same applies to anyone editing
   the file by hand or by script. After writing `status.md` and before
   appending the row, run `python3 <wire>/scripts/status_file.py check
   .wire/releases/<release_folder>`. If it reports a problem in a line this
   command just wrote, fix it now. If the problem was there before, leave it,
   say so in the output and point to `/wire:status-sync <release_folder>`
   (`specs/utils/status_sync.md` Step 1b). In orchestrated mode the
   orchestrating session runs the check when it writes `status.md` from a
   lane's state file.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.
9. **One time zone.** Every Timestamp, and every time quoted in Detail, is UTC
   with the `Z` suffix. A row is never written in local time, and a time
   with no zone is never converted by guessing the zone it was written in.
10. **Review rows say what they are.** A review result recorded from a merged
    pull request, not from a review command run, follows
    `specs/utils/status_sync.md` Step 4g: By is the approver, Detail says
    `recorded from PR #<n> approved by <name>`, and Session is what ran the
    roll-up.

## Time zones

From Wire 4.4.3 every Timestamp is UTC, `YYYY-MM-DD HH:MMZ`. Before that the
rule said local time, and logs mixed UTC rows with rows in the writer's local
time, so a ticket could appear to close before it opened.

- **Writing.** `date -u +"%Y-%m-%d %H:%MZ"`. A row's time is the UTC time the
  command finished. A roll-up row's Timestamp is the UTC time of the roll-up.
- **Rows with no zone.** `YYYY-MM-DD HH:MM` without `Z` is a row written
  before 4.4.3. It stays valid, is never rewritten, and is read as "zone
  unknown": it may be in any zone from UTC-12 to UTC+14.
- **Anything else** (`2026-10-17T14:05Z`, `14:05+01:00`, `14:05 BST`) is
  unparseable and reported as such.
- **Ordering** (rule 6, `/wire:status-sync` Step 4f). Two rows in the same
  form compare on the values written. A UTC row next to a zone-unknown row is
  out of order only when no zone in that range puts the pair in order; when
  some zones do and some do not, the pair is `zone_unknown`, listed for
  information and not a defect. A log that changes from local time to UTC in
  British summer time (`15:05` then `14:10Z`) is therefore not flagged.
- **Never earlier than the last row.** A roll-up stamps its rows with the
  later of now and the last row's time when the last row is UTC. A last row
  with no zone is not copied into a new row.

The rule is implemented in `<wire>/scripts/log_time.py` (`now`,
`check <execution_log.md>`), used by `ticket_delivery.py merge-log` and tested
by `wire/tests/core/validate_execution_log_order.py`. The Wire mod's metrics
backfill (below) reads both forms: it matches a row on its command and date,
with a day's slack, not on its time.

## Metrics Backfill (Claude Code)

From 4.1.0 the Wire mod (`hooks/register.ts`, a function hook in the Claude
Code plugin) fills the metric cells. It replaces the `Stop` settings hook
(`hooks/wire-metrics.sh` and `wire_metrics.py`), which re-read the session
transcript after each turn.

1. Each Wire command opens a run when it starts: a typed `/wire:` command, or
   a Wire command called through the Skill tool by the orchestrating session,
   a lane or Autopilot.
2. Every model request adds its measured usage to the run open in its own
   loop (the main session, or one subagent). Counts come only from the usage
   the API reports, never estimates.
3. When that loop's turn ends, the run closes and the mod fills the
   Duration (only if still `n/a`), Tokens and Cost cells of the newest row
   whose Command cell names the command, whose Tokens cell is still `n/a`, and
   which is dated no earlier than the day before the run started (a date, not
   a time, because commands write the row's time themselves and it is often
   rough). It
   never touches another cell or row, and never widens a row without the
   metric columns.
4. A row written after the run closed (an orchestrating session writing a
   lane's row once the lane reports) is filled when that write happens.
5. Cost comes from the mod's price table; an unrecognised model leaves Cost
   at `n/a` with Tokens filled.

`/wire-usage` prints the session's runs with their duration, tokens and cost;
`/wire-ran` prints each run in full with its result (4.5.0), as the band above
the prompt draws it. The plugin's `metrics` option, or `WIRE_METRICS=false`,
turns the backfill off. On runtimes without the mod (Gemini CLI), the metric cells keep the
values the workflow wrote.

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
| 2026-02-22 14:30Z | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35Z | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40Z | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12Z | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00Z | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15Z | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30Z | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00Z | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15Z | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00Z | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30Z | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45Z | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00Z | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05Z | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20Z | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
| 2026-02-25 11:02Z | /wire:data_model-generate | complete | ticket CUS-199, ran 2026-02-25 09:40Z: 4 tables | Jane Smith | orchestrator [d4e5f6] | 9m 12s | 201544 | $1.51 |
| 2026-02-25 11:02Z | /wire:data_model-review | approved | recorded from PR #64 approved by John Doe (ticket CUS-199, approved 2026-02-25 10:55Z) | John Doe | orchestrator [d4e5f6] | n/a | n/a | n/a |
```

The last two rows are a ticket roll-up (`specs/utils/status_sync.md` Step 4g)
run by an orchestrating session: the first was rolled up from the ticket's run
log; the second records a review result from the ticket's merged pull request,
so By is the approver, Session is the session that ran the roll-up, and the
metric cells stay `n/a` because no review command ran.
