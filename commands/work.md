---
description: Work a ticket inside an existing release — plan with a command or skill named per step, run only the approved plan, publish via the client's PR, patch stale documents and reconcile the record
argument-hint: <release-folder> [ticket-or-description]
model: claude-fable-5
---

# Work a ticket inside an existing release — plan with a command or skill named per step, run only the approved plan, publish via the client's PR, patch stale documents and reconcile the record

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
    'command': 'work',
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
artifact: work
domain: work
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder the ticket belongs to"
  optional:
    - name: ticket
      description: "Ticket key (e.g. NWR-31) or a one-line description of the change. Omitted: Wire lists the release's open iterations and asks."
description: Work a ticket inside an existing release — read the release for what bears on it, plan with a Wire command or skill named for every step, run only the approved plan, publish through the client's pull request, then patch the release documents the change made stale and reconcile the record
argument-hint: <release-folder> [ticket-or-description]
delegates_to:
  - session/plan
  - utils/precondition_gate
  - utils/execution_log
  - utils/status_sync
  - utils/pr_create
  - utils/commit
  - utils/meeting_context
  - utils/director_operating_model
workload: planning
---

# Wire Work Command

## Purpose

Most work on a live platform arrives as a ticket against a release that already exists, not as a statement of work. `/wire:work` is the front door for that work. It is not a new command family and it does not add a lifecycle: it composes commands and utilities Wire already has, in this order:

1. Read the release for everything that bears on the ticket (requirements, design documents, business rules register, decisions log, earlier iterations, conventions).
2. Decide whether the request is a ticket-sized change or something larger, and say so.
3. Propose a plan in which **every executable step names the Wire command or skill that performs it**, in method order (agree definitions, design, build, test, semantic layer, dashboards, publish).
4. Run only the approved plan, each command scoped to the ticket, with the ordinary gates and validate steps.
5. Publish through the client's pull request and treat the client's review as technical acceptance.
6. Close in two stages: patch the release documents the change made stale (with confirmation), then run `/wire:status-sync`.

The release is the durable work stream (an epic, a deliverable, a platform). The ticket is an **iteration** inside it. Do not create a release for a ticket; the context a ticket needs lives in the release it changes (wire#265).

The rules of `specs/utils/director_operating_model.md` apply unchanged: one writer of `status.md` and `execution_log.md`, decisions recorded with a name and reason, nothing approved on the consultant's behalf. `/wire:work` is a way of planning from a ticket instead of from the release-type graph; it is not a way round the record.

## Usage

```bash
/wire:work <release-folder> [ticket-or-description]

/wire:work 01-store-performance NWR-31
/wire:work 01-store-performance "add returns rate to the Sales Overview page"
/wire:work 01-store-performance            # lists open iterations and asks
```

Accept both `releases/01-store-performance` and bare `01-store-performance`.

## When to use it, and when not

Use `/wire:work` when the change is bounded, sits inside an existing release, and does not alter the release's design. Typical: a new measure or tile, a new column on an existing fact, a definition change, a bug fix, a rename, a test, a documentation fix.

Do **not** treat a request as an iteration when any of the following is true. Step 3 checks for them and refuses, with the reason, offering a formal release or a formal phase instead:

| Trigger | Why it is larger than a ticket |
|---|---|
| A new source system | Needs a source assessment, a pipeline and usually new concepts |
| A new business concept (entity) | Changes the conceptual model the release was designed from |
| A grain change on a table with downstream consumers | Every dependant needs re-validating; it is a design change |
| Security, permissions or data-residency change | Governed change with its own review gates |
| Production cutover or platform switch | Point of no return; belongs to a runbook and a ruling |
| Work spanning several deliverables or teams | Coordination, not a ticket |
| A request that cannot be bounded in one sentence | Not plannable as a ticket |

## Workflow

### Step 0: Mode and claim

1. Resolve the execution mode per `specs/utils/director_operating_model.md` (runtime, conversation, engagement). On Gemini CLI the mode is `manual`: `/wire:work` still opens the iteration, reads the release, proposes the plan and closes the iteration, but the consultant types the approved commands; record each as `typed`.
2. Read `agents.coordinator_session` in the release's `status.md`. If another session holds a live claim (heartbeat within 30 minutes), warn and name the holder before continuing. Do not dispatch lanes from `/wire:work`; a ticket is one foreground piece of work.
3. Set `WIRE_INVOKED_BY=orchestrator` for every command this run invokes on the consultant's behalf, so the execution log's Session column and telemetry's `invoked_by` distinguish them from typed runs.

### Step 1: Resolve the release and open or resume the iteration

1. Locate `.wire/releases/<release-folder>/status.md`. If it does not exist, stop: "No release at `<path>`. `/wire:work` runs inside an existing release. To start a new one run `/wire:new`."
2. Resolve the ticket:
   - A key (matches `[A-Z][A-Z0-9]+-\d+` or the engagement's tracker key pattern): use it as the iteration id. If Jira or Linear is configured, fetch the ticket title and text and show them; if not, ask for the ticket text.
   - A description: derive a short slug for the iteration id (`add-returns-rate`) and use the description as the ticket text.
   - Omitted: list the `## Iterations` table rows whose state is not `closed`, and ask which to resume or whether to open a new one.
3. If `.wire/releases/<release-folder>/iterations/<id>.md` exists, this is a **resume**: read it and go to Step 8. Otherwise create it from the template in "Iteration file" below, add a row to `## Iterations` in `status.md` with state `open`, and append an execution-log row: `/wire:work | complete | iteration <id> opened: <title, 80 chars>`.

### Step 2: Read the release for what bears on the ticket

Read, in this order, and keep notes for Step 4:

1. `status.md`: artifact states, `## Iterations` (what has been done since go-live, in particular anything touching the same tables, measures or pages), blockers.
2. `decisions.md` (or the Decisions section of `status.md`): every decision that names an object the ticket touches, with its date and reason.
3. The business rules register (`business_rules/register.md` in the release, or the engagement-level one if the release points to it): rules that define, or should define, any number the ticket asks for. Note the gap when a metric has no rule.
4. Requirements and design documents (`requirements/*.md`, `design/conceptual_model.md`, `design/data_model.md`, `design/pipeline_design.md`, `design/viz_catalog.md`, `design/mockups/*`): which requirement, entity, table, measure or page the ticket touches; whether the design already allows the change (a page with room for another tile, a fact that already carries the needed column).
5. Conventions: `.wire/conventions/<domain>.yml` if present, else the framework defaults.
6. The client repository: the models, views and dashboards named by the ticket, and whether the repository has a pull request template (`.github/PULL_REQUEST_TEMPLATE.md` or similar).

Then say what you found, in plain words, before planning: what has changed on the release since it was last opened, which earlier decisions bear on this ticket (with dates and reasons), whether the definition the ticket needs exists in the register, and which documents the change will touch. Ask one question only if the plan depends on it (for example, a definition the ticket leaves ambiguous), propose the reading most consistent with the release, and flag it for the owner. Do not ask what the release already answers.

### Step 3: Boundary check

Test the ticket against the trigger table in "When to use it, and when not". Behavioural test: `wire/tests/core/validate_work_iteration.py` (iteration boundary).

- **No trigger:** continue to Step 4.
- **Any trigger:** do not plan it as an iteration. Say which trigger(s) apply and why, in the ticket's own terms, then offer two shapes with a recommendation: a new release alongside this one (name the release type that fits and the first step it would take), or a formal phase added to this release (which reopens the design documents). Record the outcome on the iteration file as `state: escalated`, with the trigger(s), and in the execution log: `/wire:work | complete | iteration <id> escalated: <trigger>`. Stop. Whatever the consultant chooses runs through `/wire:new` or the release's formal commands, not through `/wire:work`.

### Step 4: Plan, with a command or skill named for every step

Follow `specs/session/plan.md` with the ticket as the objective, and the notes from Step 2 as the context. The plan must satisfy the plan-step rule (tested by `wire/tests/core/validate_work_iteration.py`):

| Column | Rule |
|---|---|
| Step | Numbered, in method order: agree definitions, design change (if any), build, test, semantic layer, dashboards, publish, acceptance |
| Type | One of `command`, `skill`, `human`, `external`, `decision`, `investigation` |
| Command or skill | For `command`: the exact `/wire:` command. For `skill`: the skill identifier, and the reason no command covers the step. For `human`, `external`, `decision`: who. For `investigation`: what is read and that nothing is written |
| Scope | The objects the step is allowed to touch, named (one model, one view, one dashboard, one rule). "Only" is the default; widening is a plan amendment |
| Produces | The file, register entry, report, PR or decision the step leaves behind |

Then state what the plan deliberately leaves out and why ("the ticket does not add a concept or change a grain, so the requirements and the data model are not redrafted; the lines this changes are patched at close and shown first"). A plan that omits a build or a test step for a code change must say why.

Offer four answers: **Approve / Changes / Explain <step> / Cancel**. On Explain, give the consequence of skipping the step in the release's own terms (which objects would carry no citation, what the validate step would warn about, how many implementations would need to stay in step), not a general principle. On Approve, write the plan into the iteration file as **plan v1** with the approver's name and timestamp, and continue. On Cancel, record `state: cancelled` and stop.

Typical plan for a metric-and-tile ticket, so the shape is clear:

```
| # | Step | Type | Command or skill | Scope | Produces |
|---|---|---|---|---|---|
| 1 | Agree the definition | command | /wire:business-rules-generate 01-store-performance --domain returns | 1 new rule, cites BR-9 | BR-15 (proposed, owner: ops director) |
| 2 | Change the sales fact | command | /wire:dbt-warehouse-generate 01-store-performance | wh_sales__orders_fact only | 2 measures, schema.yml, meta.wire_business_rule: BR-15 |
| 3 | Build and test | command | /wire:dbt-validate 01-store-performance | state:modified+ | PASS/FAIL report |
| 4 | Add the measure | command | /wire:semantic_layer-generate 01-store-performance | sales explore only | LookML measure returns_rate |
| 5 | Add the tile | command | /wire:dashboards-generate 01-store-performance | Sales Overview, 1 tile | dashboard LookML |
| 6 | Publish | command | /wire:utils-pr-create 01-store-performance | this branch | PR on the client template with evidence |
| 7 | Code review | external | client analytics engineer | PR | technical acceptance |
| 8 | Confirm the definition | decision | ops director | BR-15 | BR-15 agreed |
```

### Step 5: Run the approved plan

Run the steps in order. For each `command` step:

1. Say, in one sentence, what the command will do and to which objects, before it runs.
2. Invoke the **real** command with the scope from the plan. Do not do by hand what a named command does; that is the failure `/wire:work` exists to prevent. If you find yourself about to write a model, view or dashboard directly, stop and run the command.
3. The command's own precondition gate runs as normal (`specs/utils/precondition_gate.md`). If it blocks on a **design-document** precondition that the release never produced (a `custom` release with no data model, for instance), present the gate's override prompt with the reason pre-filled: `ticket-scoped change under /wire:work, iteration <id>`; the consultant confirms or declines; the override is recorded exactly as the gate records any override. A blocking precondition on a **technical** artifact (validate PASS before review, a runbook before cutover) is never pre-filled; it stops the plan.
4. The command's auto-validate runs as normal. Report the result in the command's own terms (checks passed, tests failed and on which rows).
5. Each command writes its own execution-log row as it always does. In orchestrated mode `/wire:work` is the single writer and appends them from the command's report.

For `skill` steps: activate the skill, log the activation row (`skill | <identifier> | activated | iteration <id> step <n>`), and do the work under the skill's conventions with the plan's scope.

For `human`, `external` and `decision` steps: do nothing but record that the step is waiting and on whom.

**Plan amendments.** When a step's result changes what should happen next (a failing test that needs a modelling decision, a scope that must widen, a step that turns out to be unnecessary): stop, say what was found and on which rows or objects, offer the options with a recommendation and what each would disturb, and wait. Record the answer in `decisions.md` with the reason, write **plan v(n+1)** to the iteration file with the change marked, and continue. Never widen scope, add a step or substitute a command silently.

**Deviations.** If what ran differs from what was approved, the execution-log row's Detail says so: `deviation: different command (<approved> -> <ran>)`, `deviation: scope widened to <objects>`, `deviation: out of sequence`, or `deviation: typed by consultant` (the last is a mode change, not a fault). `/wire:status-sync` reads these.

### Step 6: Publish and separate the two acceptances

1. Run `/wire:utils-commit <release> work <id>` then `/wire:utils-pr-create <release>` on the client repository's own template where one exists. The PR body carries: the ticket, the plan steps, the validate result, the convention lint result, the business rules cited, the decisions made during the work with their reasons, and the document patches from Step 7 once applied.
2. Record the PR number and URL on the iteration file and in the `## Iterations` row. State: `awaiting_review`.
3. Keep **technical acceptance** (PR review and merge by the client's engineer) and **business acceptance** (confirmation of a definition or a number by the person who owns it) separate on the iteration file. A PR approval satisfies the first. It never satisfies the second, whoever approved it, because a code reviewer does not own a business definition. Say so in the report if both are outstanding.

### Step 7: Close, in two stages

**Stage 1: document patch pass.** Before the record is reconciled, find the release documents the change has made stale and propose the smallest patch to each:

1. Collect the objects the iteration changed: model names, column and measure names, dashboard and tile names, business rule ids, requirement ids.
2. Search the release folder's documents (`requirements/`, `design/`, `business_rules/`, `deployment/`, `documentation/`) for each object. For each hit, decide whether the text is now wrong (a column list without the new column, a requirement status that is now implemented, a definition that has changed) or still true.
3. For each stale document, propose the minimal patch as a diff, with the reason, and ask: **apply / show full / defer**. Follow `specs/utils/stale_artifact_check.md`'s posture: never write without confirmation. A deferred patch is recorded on the iteration file with the reason and surfaces in `/wire:status-sync` and on the next `/wire:work` open.
4. Never regenerate a document to patch it. A regenerate rewrites lines the ticket did not touch.
5. Applied patches are committed on the ticket branch and listed in the PR body.

**Stage 2: state sync.** Run `/wire:status-sync <release>`. It reconciles `status.md`, the execution log, sprint-plan state and the next action against the evidence the iteration produced, with the consultant's confirmation as it always does.

**Definition of done** (tested by `wire/tests/core/validate_work_iteration.py`). An iteration is `closed` only when all four hold:

1. Document patch pass clean, or every stale document explicitly deferred with a reason.
2. Every validate step in the plan reported PASS (or the failure was resolved by a recorded decision and re-run to PASS).
3. Every acceptance step is satisfied by the role that owns it: technical acceptance by the client's reviewer, each business definition or number by its named owner.
4. `/wire:status-sync` completed.

If any does not hold, the iteration stays open with `state: awaiting_review` or `awaiting_owner`, and the report ends with exactly who or what it is waiting on. Never call an iteration done because the code was merged.

On close: set `state: closed` with the timestamp; append `/wire:work | complete | iteration <id> closed: <steps run>/<steps planned>, PR #<n> merged, <k> decisions, <m> patches`.

### Step 8: Resume

On a resume (Step 1 found the iteration file):

1. Report the iteration's state and what it is waiting on.
2. If a PR is recorded and `gh` is available, read its review and merge state; update the iteration file and say what changed (`PR #91 approved by <login> and merged <date>: technical acceptance satisfied`). Without `gh`, ask.
3. For each outstanding business acceptance, follow `specs/utils/meeting_context.md`: search recordings since the iteration opened for the owner confirming the definition or number. If found, quote it with the timestamp and **propose** recording it as the confirmation; never record it unasked.
4. If plan steps remain, continue from Step 5. If all steps are done, run Step 7.

## Iteration file

`.wire/releases/<release-folder>/iterations/<id>.md`:

```markdown
# Iteration <id>: <title>

| Field | Value |
|---|---|
| Ticket | <key or slug>, <tracker URL if any> |
| Opened | YYYY-MM-DD HH:MM by <name> |
| State | open \| awaiting_review \| awaiting_owner \| closed \| escalated \| cancelled |
| Branch | <branch> |
| PR | #<n> <url> |
| Technical acceptance | pending \| approved by <login> on <date> (PR #<n>) |
| Business acceptance | <rule or number>: pending \| confirmed by <owner> on <date>, source: <recording or message> |
| Closed | YYYY-MM-DD HH:MM |

## Ticket text
<verbatim>

## What the release already held
<Step 2 notes: earlier decisions with dates, rules present or missing, documents touched>

## Plan v1 (approved by <name>, YYYY-MM-DD HH:MM)
<the plan table>
Left out, and why: <...>

## Plan v2 (amended YYYY-MM-DD HH:MM, reason: <...>)
<only the changed rows, marked>

## Run
| Step | Ran | Command or skill | Scope | Result | Deviation |

## Decisions made during the work
<id, text, reason, by — the same rows as in decisions.md>

## Document patches
| Document | Change | Status (applied \| deferred: reason) |
```

## `## Iterations` table in status.md

Added to `status.md` after `## Artifact Status Summary` if absent:

```markdown
## Iterations

| Ticket | Title | Branch | PR | State | Opened | Closed |
|--------|-------|--------|----|-------|--------|--------|
```

One row per iteration, updated in place (this table is a summary, not a log; the log is `execution_log.md` and the iteration file).

## Output

End every run with a plain-language report: the iteration id and state, the steps run and their results, decisions made, the PR and its state, the two acceptances and who each waits on, patches applied or deferred, and what happens next. Name the commands that ran, in full and as they would be typed (`/wire:` prefix, release folder, flags), so the consultant can answer "which command did that?" without looking and could re-run any step by copying the line (operating model rule 7).

## Gemini CLI

Gemini has no skills or agents. `/wire:work` runs Steps 1 to 4 and 7 unchanged, and presents Step 5 as the list of commands for the consultant to type in order, updating the iteration file from the record after each. Every row is `typed`.

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
