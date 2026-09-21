---
sidebar_position: 6
title: Management Commands
---

# Management Commands

Every engagement needs a certain amount of housekeeping around the artifacts themselves: a release has to be created before anything can be generated, its status has to be reported to the client from time to time and, when it is finished, it has to be closed down tidily. Management commands do that work, operating on releases and engagements as a whole (creating, archiving, reporting status and performing housekeeping), and none of them generate or validate individual artifacts. We take them in the order you are likely to meet them, starting with `/wire:new`.

## `/wire:new`

Creates a new release, and it is always the first Wire command you run for an engagement.

```
/wire:new
```

Wire prompts for:
1. Release type
2. Client name and project name
3. Delivery start date
4. Optional: Jira project key
5. Optional: Linear project
6. Optional: Document store (Confluence space or Notion database)
7. Optional: Document store parent page/database

Wire creates:
- `.wire/releases/YYYYMMDD_<client>_<type>/`, the engagement folder
- `.wire/releases/YYYYMMDD_<client>_<type>/config.yaml`, the engagement configuration
- `.wire/releases/YYYYMMDD_<client>_<type>/status.md`, the initial status report
- `.wire/releases/YYYYMMDD_<client>_<type>/execution_log.md`, an empty execution log
- `CLAUDE.md` update, adding project context if it is not already present

---

## `/wire:status`

Shows the current status of all active releases, or of a specific release.

```
/wire:status
/wire:status <release-folder>
```

Output includes:
- Phase and artifact completion counts per release
- Any open review gates
- Any validation failures
- Jira/Linear sync status (if configured)
- Last activity timestamp

With a specific release folder the output is expanded to show every artifact and its current state.

`/wire:status` also performs reconciliation when integrations are configured, syncing any missing Jira/Linear updates and flagging divergences between the local execution log and the external trackers, so that the board your client looks at matches the record on disk.

---

## `/wire:work`

Most work on a live platform arrives as a ticket against a release that already exists, not as a statement of work. `/wire:work` (v4.0.0, #265) is the front door for that work, and it adds no lifecycle of its own: it composes commands Wire already has.

```
/wire:work <release-folder> [ticket-key-or-description]
```

It reads the release for what bears on the ticket (the decisions log, the business rules register, the design documents, earlier iterations and the conventions) and says what it found before planning. It then checks the request against seven triggers that make a change larger than a ticket (a new source system, a new business concept, a grain change with downstream consumers, a security or data-residency change, a production cutover, work spanning several deliverables, a request that cannot be bounded) and, if any applies, refuses to plan it as an iteration and offers a formal release or phase instead. Otherwise it proposes a plan through `/wire:session-plan` in which every executable step names the Wire command or skill that performs it, its scope and what it produces, states what the plan leaves out and why, and offers Approve, Changes, Explain or Cancel. On approval the named commands run, scoped as written, through their ordinary precondition gates and validate steps; a design-document precondition the release never produced is presented as the gate's normal override, pre-filled with the ticket, and a technical precondition is never pre-filled. Anything that ran differently from the plan is logged as a deviation.

Publication goes through `/wire:utils-commit` and `/wire:utils-pr-create` on the client repository's own template, with the validate result, the rules cited and the decisions made attached. Technical acceptance (the client's PR review and merge) and business acceptance (a named owner confirming a definition or a number) are recorded separately, and a PR approval never satisfies the second. The iteration closes in two stages: a document patch pass that finds the release documents the change made stale and proposes the smallest patch to each, applied only with confirmation and never by regenerating; then `/wire:status-sync`. An iteration is closed only when the patch pass is clean or deferred with a reason, every validate step passed, every acceptance is satisfied by its owning role and the sync has run. Re-running the command on an open ticket resumes it, reads the PR state and looks in meeting recordings for an owner's confirmation, which it proposes and never records unasked.

The record is `iterations/<ticket>.md` in the release folder (ticket text, what the release already held, each plan version, what ran, decisions, patches, both acceptances) and an `## Iterations` table in `status.md`. A release is the durable work stream, an epic or a deliverable; a ticket is an iteration inside it. Do not create a release per ticket. On Gemini CLI the command presents the plan and the consultant types the commands. Chapter 4 of Part 1 walks one ticket through end to end; the deterministic rules (boundary, plan-step, acceptance, definition of done) are tested by `wire/tests/core/validate_work_iteration.py`.

---

## `/wire:status-sync`

What happens to the record when work is done outside a command run? Status tracking updates automatically only when work runs through Wire commands, and work done conversationally or with an agent's help, which is common in `custom` releases, leaves `status.md`, the execution log and the sprint plan behind. `/wire:status-sync` is the repair path for that (v3.11.8, #204): it reconciles a release's recorded state against evidence and then repairs the record with your confirmation, so that where `/wire:status` reports the record as it stands, `status-sync` fixes it when it has drifted.

```
/wire:status-sync <release-folder>
```

It diffs the recorded state (`status.md`, `execution_log.md`, the governing `sprint_plan.md`) against evidence from git history, files on disk and the log itself, classifies the drift deterministically (`record_behind`, `record_ahead`, `fields_incomplete`, `last_updated_stale`, `totals_stale`, `history_gap`) and presents a numbered drift report. Nothing is written without your explicit confirmation, and declining is side-effect-free. History is append-only (backfilled log rows carry the sync's own timestamp), and the command never downgrades a recorded state on the absence of evidence alone; `record_ahead` items are resolved one at a time with you. Run it before raising a PR for any work done outside command runs, as the PR checklist includes it.

To read the record rather than repair it, the [`project-review` skill](../reference/skills#project-review) reviews a whole engagement from the same evidence: the execution log, every `status.md` and the git history. It writes a review to `.wire/reviews/` and changes nothing.

---

## `/wire:archive`

Archives a completed or cancelled release, marking it as archived in the execution log, writing a final status snapshot and optionally exporting all of its artifacts to a client-facing package.

```
/wire:archive <release-folder>
```

Wire asks:
1. Reason for archiving (Completed / Cancelled / Superseded)
2. Whether to export a client package (Markdown files, rendered PDFs)
3. Whether to close associated Jira Epic / Linear Project (if configured)

Archived releases remain in `.wire/releases/` and are shown in `/wire:status` with an "Archived" badge, but they are not included in the active engagement counts.

---

## `/wire:utils-linear-create`

Creates the Linear project hierarchy for an engagement.

```
/wire:utils-linear-create <release-folder>
```

It creates a Linear Project, Issues (one per artifact) and Sub-issues (one per lifecycle step), and the Linear project and issue IDs are written to `.wire/releases/<release>/config.yaml` so that subsequent commands can sync to them.

---

## `/wire:utils-doc-analyze`

Analyses a source document and extracts the Wire-relevant information from it without creating any artifacts, which makes it a safe first step when a statement of work arrives.

```
/wire:utils-doc-analyze path/to/SoW.pdf
/wire:utils-doc-analyze path/to/SoW.pdf path/to/kickoff-notes.md
```

Output:
- Extracted deliverables with descriptions and acceptance criteria
- Wire match scores (how well each deliverable maps to an existing Wire command)
- Proposed engagement structure
- Open questions Wire cannot resolve from the document alone

It is useful for scoping an engagement before running `/wire:new`, as well as for verifying that a SoW is specific enough to drive Wire artifact generation.

---

## `/wire:utils-docstore-setup`

Configures or reconfigures the document store integration for a release.

```
/wire:utils-docstore-setup <release-folder>
```

This is the same configuration step that is offered during `/wire:new` Step 9.5, made available separately for releases that were set up without a document store.
