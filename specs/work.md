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
  - utils/ticket_delivery
  - utils/repos
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

**Releases built from tickets** (`delivery: tickets` in `status.md`, 4.2.0, wire#279). When a release is built ticket by ticket from a tracker, `/wire:work` is how each ticket is worked, including the main build tickets. The ticket map (`tickets.yaml`, written by `/wire:tickets-import`) says which slices and Wire steps each ticket covers, and `specs/utils/ticket_delivery.md` holds the rules. Four things change, each marked **Ticket delivery** in the steps below: the scope check reads the ticket map, every command step runs with `--slice`, the ticket branch writes only the ticket's own files, and the release record is updated when the pull request merges. Without `delivery: tickets`, nothing below changes.

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

**Ticket delivery.** When `status.md` has `delivery: tickets`:

- Read `tickets.yaml`. A ticket in the map has a record with `state: planned` from the import: this is its first open, not a resume. Set `state: open` in the record's front matter and continue at Step 2.
- Before writing anything, run `ticket_delivery.py holder <release> <ticket>` (wire#423). `here`: go on. `other`: the ticket is in another release's map. Say so, name that release and offer to switch to it; go on in the named release only if the consultant says to, and record their reason in the iteration file. `several`: two releases hold the ticket; ask which one this work belongs to. `none`: the ticket is in no ticket map; with a Jira release filter in use, read the ticket's Fix versions and offer the release whose `jira.release` matches. When `/wire:work` is given a ticket and no release, use the release `holder` finds and say which it is.
- A ticket in no map and no release's Jira release: say so, and offer `/wire:tickets-import <release> --refresh` to add it. If the consultant goes on without it, it is an ordinary iteration and Step 3's ordinary boundary check applies.
- Cut the ticket branch from the release branch (`specs/utils/git_workflow.md`), named from the ticket key and title. Everything from here to Step 6 is written on that branch.
- On the ticket branch, write only the ticket record (`iterations/<id>.md`), the ticket run log (`iterations/<id>.execution_log.md`) and the files the plan's commands produce. Do not write `status.md`, `execution_log.md`, `tickets.yaml` or `decisions.md` there; the `## Iterations` row and the opened log row go to the ticket run log and are added to the release record when the pull request merges (`specs/utils/ticket_delivery.md`, "One record per ticket"). This is what stops ticket branches clashing on the record files.

### Step 2: Read the release for what bears on the ticket

Read, in this order, and keep notes for Step 4:

1. `status.md`: artifact states, `## Iterations` (what has been done since go-live, in particular anything touching the same tables, measures or pages), blockers.
2. `decisions.md` (or the Decisions section of `status.md`): every decision that names an object the ticket touches, with its date and reason.
3. The business rules register (`business_rules/register.md` in the release, or the engagement-level one if the release points to it): rules that define, or should define, any number the ticket asks for. Note the gap when a metric has no rule.
4. Requirements and design documents (`requirements/*.md`, `design/conceptual_model.md`, `design/data_model.md`, `design/pipeline_design.md`, `design/viz_catalog.md`, `design/mockups/*`): which requirement, entity, table, measure or page the ticket touches; whether the design already allows the change (a page with room for another tile, a fact that already carries the needed column).
5. Conventions: `.wire/conventions/<domain>.yml` if present, else the framework defaults.
6. The client repository: the models, views and dashboards named by the ticket, and whether the repository has a pull request template (`.github/PULL_REQUEST_TEMPLATE.md` or similar).
7. Related repos, on acceptance only (`specs/utils/repos.md`, wire#381). If the engagement lists related repos (`python3 <wire>/scripts/related_repos.py list` shows any) and the ticket names a source, table, model or DAG, offer one lookup in the repos whose role matches what it names. Do not search before the person accepts.

   | The ticket names | Offer a lookup in roles |
   |---|---|
   | A dbt source, staging table or model | `dbt`, `code` |
   | A DAG, schedule, load job or landing table | `orchestration`, `ingestion`, `code` |
   | A LookML view, explore or dashboard | `lookml`, `code` |
   | An Omni topic or document | `omni`, `code` |

   A name can match more than one row (a landing table is read by dbt and written by a DAG); take every matching role. The repo's `lookup` setting decides what happens next:

   - `offer` or `auto`: offer the lookup, all such repos in one question: "The ticket names `orders_raw`. Look it up in `airflow` (orchestration) and `dbt` (dbt)? (yes / no / pick)".
   - `on_request` (the default): do not offer. Name the repos in one line ("`airflow` (orchestration) may hold `orders_raw`; ask to look it up") and look only if the person asks.
   - The person asked for a lookup in the ticket or the conversation: look in the repos they named, whatever the setting.

   If a repo to be searched is `not fetched` or was fetched more than a day ago, say so and offer `/wire:utils-repos refresh <id>` first. The rule is tested by `wire/tests/core/validate_work_iteration.py` (Part 5).

   On yes, run `related_repos.py find <name> --repo <id>` for each repo and show the hits with their citations. Record the hits the person keeps in the iteration file's `## Related repo lookups` table, each with its citation `<id>@<short commit>:<path>` and what it showed (the DAG that writes the table, its schedule and file format, the models that read it). On no, record nothing and do not offer again for the same name in this iteration. Never write to a related repo: a change one needs is named in the plan as an `external` step for whoever owns that repository.

**Ticket delivery.** Also read, for each of the ticket's slices: its row in the `## Slices` table and the tickets that covered it before; the slice's design, from `python3 <wire>/scripts/ticket_delivery.py design-source <release> --slice <slice>` (Wire's `data_model` section, or the table in the Modality physical model, named with its file and columns); and which ticket approved that design. Say whether the ticket's own steps can start (`ticket_delivery.py runnable <release>`): what it waits on, by ticket, and any blocker on record.

Then say what you found, in plain words, before planning: what has changed on the release since it was last opened, which earlier decisions bear on this ticket (with dates and reasons), whether the definition the ticket needs exists in the register, and which documents the change will touch. Ask one question only if the plan depends on it (for example, a definition the ticket leaves ambiguous), propose the reading most consistent with the release, and flag it for the owner. Do not ask what the release already answers.

### Step 3: Boundary check

Test the ticket against the trigger table in "When to use it, and when not". Behavioural test: `wire/tests/core/validate_work_iteration.py` (iteration boundary).

**Ticket delivery.** For a ticket in the ticket map, the check reads the map, not the release's original design. Run `ticket_delivery.py scope <release> <request.json>` with the objects the request adds (each with its trigger) and any other trigger:

- A new source or a new table that is one of this ticket's slices is **planned work**: accepted. Say so: "the ticket builds a new table; the table is in the ticket map, so this is planned work".
- A new source or table that is not one of this ticket's slices is refused, with options: a new ticket in the tracker (then `/wire:tickets-import --refresh`), or a new ticket in this release, which widens the release and is agreed with the lead consultant first. Offer to start the ticket without it (outcome `partial`).
- The other triggers (grain change with dependants, security or residency, cutover, spanning deliverables, unbounded) apply as below, ticket map or not.

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

**Ticket delivery.** Every command step that makes or checks release documents or code carries `--slice <slice>` (`specs/utils/ticket_delivery.md`, "The `--slice` option"), and the plan covers the ticket's steps from the ticket map. Steps other tickets cover for the same slice (a requirements ticket for the whole release, a design ticket for four tables) are left out and named as such. Where the slice's design source is `modality_physical`, step 1 records the design from the Modality model (`/wire:data_model-generate <release> --slice <slice>`) instead of designing the table; where it is Wire's own, the plan designs the table and adds a `decision` step for the lead consultant to approve the design before the build. Name the branch and the release branch it is cut from.

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
6. **Ticket delivery.** The row goes to the ticket run log, `iterations/<id>.execution_log.md`, not to `execution_log.md`. After each action, write its result to `results:` in the ticket record's front matter, one value per action (`dbt: {generate: complete, validate: pass}`). A step done under a skill by direct edit, rather than by its command, records its result the same way, with the evidence in the step's Run row (`build 22 of 22`). Record the ticket's branch in the front matter (`branch:`) when the branch is cut. A blocker found during the run is written to `blocked:` with its reason, and cleared when it lifts.

For `skill` steps: activate the skill, log the activation row (`skill | <identifier> | activated | iteration <id> step <n>`), and do the work under the skill's conventions with the plan's scope.

For `human`, `external` and `decision` steps: do nothing but record that the step is waiting and on whom.

**Plan amendments.** When a step's result changes what should happen next (a failing test that needs a modelling decision, a scope that must widen, a step that turns out to be unnecessary): stop, say what was found and on which rows or objects, offer the options with a recommendation and what each would disturb, and wait. Record the answer in `decisions.md` with the reason, write **plan v(n+1)** to the iteration file with the change marked, and continue. Never widen scope, add a step or substitute a command silently.

**Deviations.** If what ran differs from what was approved, the execution-log row's Detail says so: `deviation: different command (<approved> -> <ran>)`, `deviation: scope widened to <objects>`, `deviation: out of sequence`, or `deviation: typed by consultant` (the last is a mode change, not a fault). `/wire:status-sync` reads these.

### Step 6: Publish and separate the two acceptances

1. Run `/wire:utils-commit <release> work <id>` then `/wire:utils-pr-create <release>` on the client repository's own template where one exists. The PR body carries: the ticket, the plan steps, the validate result, the convention lint result, the business rules cited, the decisions made during the work with their reasons, the related repo lookups from Step 2 with their citations (`<id>@<short commit>:<path>`), and the document patches from Step 7 once applied.
2. Record the PR number and URL on the iteration file and in the `## Iterations` row. State: `awaiting_review`.
   **Ticket delivery.** The pull request goes into the release branch. Record the PR on the ticket record only; say that `status.md` and `execution_log.md` are updated when the pull request merges. If the tracker is connected, move the ticket to its review state with a link to the pull request.
3. Keep **technical acceptance** (PR review and merge by the client's engineer) and **business acceptance** (confirmation of a definition or a number by the person who owns it) separate on the iteration file. A PR approval satisfies the first. It never satisfies the second, whoever approved it, because a code reviewer does not own a business definition. Say so in the report if both are outstanding.

**Review rules and tested-in-dev evidence (wire#380).** These apply to every PR this step raises. Settings come from `.wire/engagement/review_profile.yml` (schema in `wire/schemas/review-profile-schema.md`); without it, the defaults there apply.

- **Rule findings are never blocking.** Each convention lint finding on the changed files carries a disposition: `fixed`, `justified` (with a reason) or `acknowledged`. Ask the consultant for any finding without one; an unanswered finding is listed as `open`, not hidden and not a reason to hold the PR.
- **A requirements table per ticket.** Each requirement from the ticket is `met`, `not met` or `can't tell`, with evidence. `met` without evidence is `can't tell`. A `not met` requirement is a deviation: raise it as a question to the ticket owner in the PR body and the report; do not decide it.
- `wire/scripts/review_rules.py` builds both tables from the findings and the requirements; paste its output into the PR body under the client template's headings.
- **Tested in dev.** For a change to Airflow code, with `tested_in_dev` not `off`, run `/wire:utils-dev-test-evidence <release>` before `/wire:utils-pr-create` (after `/wire:utils-ci-parity` where the plan has it) and carry its table in the body, at the top when the verdict is not `yes`. The verdict does not block the PR.
- An Airflow ticket's plan names the commands for each step: `/wire:pipeline-generate` (an ingestion load) or `/wire:orchestration-generate` (a schedule change, existing Airflow estate mode), their validate commands, `/wire:utils-dev-deploy`, a `human` step for the run in dev, `/wire:utils-dev-test-evidence`, then publish.

### Step 7: Close, in two stages

**Stage 1: document patch pass.** Before the record is reconciled, find the release documents the change has made stale and propose the smallest patch to each:

1. Collect the objects the iteration changed: model names, column and measure names, dashboard and tile names, business rule ids, requirement ids.
2. Search the release folder's documents (`requirements/`, `design/`, `business_rules/`, `deployment/`, `documentation/`) for each object. For each hit, decide whether the text is now wrong (a column list without the new column, a requirement status that is now implemented, a definition that has changed) or still true.
3. For each stale document, propose the minimal patch as a diff, with the reason, and ask: **apply / show full / defer**. Follow `specs/utils/stale_artifact_check.md`'s posture: never write without confirmation. A deferred patch is recorded on the iteration file with the reason and surfaces in `/wire:status-sync` and on the next `/wire:work` open.
4. Never regenerate a document to patch it. A regenerate rewrites lines the ticket did not touch.
5. Applied patches are committed on the ticket branch and listed in the PR body.

**Stage 2: state sync.** Run `/wire:status-sync <release>`. It reconciles `status.md`, the execution log, sprint-plan state and the next action against the evidence the iteration produced, with the consultant's confirmation as it always does.

**Ticket delivery.** Stage 1 runs on the ticket branch before merge where it can; patches found after merge are committed to the release branch. When the pull request has merged, set `merged: true` in the ticket record, then run `/wire:status-sync <release>` on the release branch. Its Step 4g rolls the ticket up: the ticket run log's rows are added to `execution_log.md`, the ticket's decisions to `decisions.md`, and the `## Slices` table and `## Iterations` row are rewritten, all on confirmation. A merged ticket whose business acceptance is outstanding stays `awaiting_owner`; its cells still show complete, because the code is built and tested.

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

In a ticket-built release the file starts with the front matter block in `specs/utils/ticket_delivery.md` ("The ticket record's front matter"): `ticket`, `state`, `merged`, `blocked`, `results`.

```markdown
# Iteration <id>: <title>

| Field | Value |
|---|---|
| Ticket | <key or slug>, <tracker URL if any> |
| Opened | YYYY-MM-DD HH:MM by <name> |
| State | planned \| open \| awaiting_review \| awaiting_owner \| closed \| escalated \| cancelled |
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

## Related repo lookups
| Name looked up | Citation | What it showed |
<one row per hit kept, e.g. orders_raw | airflow@1a2b3c4:dags_shop/load_orders.py | written nightly at 02:00, parquet, truncate and load>

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
