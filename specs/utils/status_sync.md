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
  - utils/ticket_delivery
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
| Ticket records and ticket run logs (`iterations/`), in a release with `delivery: tickets` | `execution_log.md` rows rolled up from merged tickets, `decisions.md`, the `## Slices` table, `## Iterations` rows (Step 4g) |

## Workflow

### Step 1: Resolve the Release Folder

1. Resolve the release folder from the argument or the inference above.
2. Verify `.wire/releases/<release_folder>/status.md` exists. If not, stop: suggest `/wire:status` to list releases, or `/wire:new` if no engagement exists in this repo.

### Step 1b: Check the Status File Can Be Read

Run `python3 <wire>/scripts/status_file.py check .wire/releases/<release_folder>`
before reading anything else. It reports a key that appears twice in one YAML
block (`yaml.safe_load` keeps the last copy without an error) and a file that
does not parse, in `status.md` and in each ticket record under `iterations/`,
with the file and line. Each problem carries its drift category:

| Script finding | Category | Proposal |
|---|---|---|
| `duplicate` | `status_duplicate_key` | Show both copies with their lines and values, and the evidence for which is newer: execution-log rows for that artifact and step, and `git log -L <line>,<line>:<file>` for when each line was written. Propose keeping the newer value as the key, and moving the other to a `prior_<key>` field when it is worth keeping (an earlier approval date), otherwise removing it. Ask, one at a time; the later line in the file is not always the newer value |
| `parse` | `status_unparseable` | Show the line and the parser's message, and propose the smallest edit that makes the file parse. Ask |

These two are resolved before Step 2, and before any other drift is
classified, because every later step reads values from the file. Nothing else
is proposed until the file reads cleanly; once it does, run the script again
and continue. A declined repair ends the sync with the report alone, as Step 6
allows. On a ticket branch, report only (see Edge Cases), except for a
duplicate in that ticket's own record.

In orchestrated mode this repair is made by the orchestrating session, the
single writer of `status.md`, after the director has chosen the value.

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
| A UTC row (`HH:MMZ`) next to a row with no zone, and some zones put the pair in order and some do not | `in_sync` | List the pair as `zone_unknown`, for information. Never convert the older row by guessing its zone |

Timestamps are UTC with a `Z` suffix from 4.4.3; a row without the suffix is
read as "zone unknown" (`specs/utils/execution_log.md`, "Time zones"). Run
`python3 <wire>/scripts/log_time.py check <release>/execution_log.md` for this
check; do not compare the rows by hand.

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

**4g. Ticket roll-up** (only when `status.md` has `delivery: tickets`;
`specs/utils/ticket_delivery.md`). Run on the release branch. For each ticket
whose pull request has merged into the release branch (front matter
`merged: true`, or `gh pr view` says merged and the record does not yet say
so) and whose run log has rows not yet in `execution_log.md`:

| Condition | Category | Proposal |
|---|---|---|
| Ticket merged, record says `merged: false` or nothing | `ticket_merge_unrecorded` | Set `merged: true` in the ticket record |
| Ticket run log has rows not yet rolled up | `ticket_rows_pending` | Append the rows from `python3 <wire>/scripts/ticket_delivery.py merge-log <release> <ticket>` (roll-up time in Timestamp, `ticket <key>, ran <original time>:` in Detail, ticket order, no duplicates). Both times are UTC with the `Z` suffix (`2026-10-17 15:40Z`, `ran 2026-10-17 14:28Z`); an original time the ticket log wrote without a zone (before 4.4.3) is copied as written, never converted |
| A review result in the ticket record (`review: approved`) comes from the ticket's merged pull request, not from a review command row in its run log | `ticket_review_from_pr` | Record it as a pull request approval (below). Never write it as a review command run |
| Ticket record has decisions not in `decisions.md` | `ticket_decisions_pending` | Copy them, next ids in sequence, citing the ticket |
| `## Slices` table differs from `ticket_delivery.py status <release> --markdown` | `slices_stale` | Replace the table |
| A step is complete for the release (every slice that has it) and `artifacts.<id>` does not say so | `record_behind` | Set the artifact's present lifecycle steps to done, with a `revision_history` entry: `complete across <n> slices (ticket roll-up)` |
| A step is complete in some slices only | `in_sync` | None. Note `<k> of <n> slices` in the report; never mark the artifact done early |

A ticket open on its branch is never rolled up: its rows stay in its own run
log until it merges. Rows already rolled up are recognised by their Detail
prefix and never added twice. The roll-up rows are appended after every other
backfilled row, in the order `merge-log` returns them.

**Review results recorded from a pull request** (4.4.3). When a ticket's
review result is a pull request approval (the reviewer approved the ticket's
pull request; no `/wire:<artifact>-review` ran), the roll-up records it as
what it is:

1. Read the approval: `gh pr view <n> --json number,url,reviews`. The pull
   request number comes from the ticket record's `| PR |` row, or
   `gh pr list --head <branch> --state merged`.
2. Run `python3 <wire>/scripts/ticket_delivery.py pr-review <ticket>
   <artifact> <pr.json> --session "<what ran the roll-up>" --names
   <names.json>` (`names.json` maps GitHub logins to names, from the team
   roster `.wire/engagement/team.yml` or the GitHub profile). It returns the
   log row and the `status.md` fields.
3. The row: Command `/wire:<artifact>-review`, Result `approved`, Timestamp
   the roll-up time in UTC, **By the approver** (the author of the latest
   approving review, never the person or agent running the roll-up), Detail
   `recorded from PR #<n> approved by <name> (ticket <key>, approved
   <time>Z)`, **Session what ran the roll-up** (`orchestrator [<id>]`, a lane
   label, or `typed` only when a person typed `/wire:status-sync`; ` as
   <persona>` when one is set), and `n/a` in the three metric cells because
   no review command ran.
4. `status.md`, on `artifacts.<artifact>`, when the step is complete for the
   release: `review: approved`, `reviewed_by` (every approver, comma
   separated), `reviewed_date` (the approval date, UTC) and `review_pr` (the
   pull request URL; a list when several pull requests approved slices of
   the step).
5. A pull request merged with no approving review records no review result.
   The script says so; report the step as still owing its review, with the
   command that holds it (`/wire:<artifact>-review <release>`).

This rule does not decide whether a pull request approval may stand as a
review; it makes the record show that the result came from one.

**4h. Ticket results missing** (only when `status.md` has `delivery: tickets`;
4.2.6, wire#297). Run on the release branch. For each merged ticket, run
`python3 <wire>/scripts/ticket_delivery.py progress <release> <ticket>` and
read its `missing` list: the actions its run-log rows or changed files show
and its record's `results:` does not hold.

| Condition | Category | Proposal |
|---|---|---|
| `missing` lists an action | `ticket_results_missing` | Write it to the ticket record's `results:` in the full form (`dbt: {generate: complete}`), keeping every value already there. Show the evidence beside each proposal |
| The ticket record's own run table or pull request shows a validate or review result that `missing` does not list (a build that passed, a pull request reviewed and merged) | `ticket_results_missing` | Propose it, marked as read from the record, with the line it comes from. Never propose a result the record does not state. A review result read from a pull request approval is logged by 4g's "Review results recorded from a pull request" rule, with the approver in By |
| `missing` is empty | `in_sync` | None |

A result already in the record is never changed by this check; a conflict
between the record and the evidence is reported for the consultant to decide.
Proposals are applied only on confirmation, and before the step states of
4g's last two rows are worked out, so a step the new results complete counts
as complete.

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

When Step 1b found problems, the report holds only those rows, for example:

```markdown
| # | Target | Drift | Proposed repair |
|---|--------|-------|-----------------|
| 1 | status.md line 12 | status_duplicate_key: `artifacts.dashboards.reviewed_date` at line 10 ("2026-10-20") and line 12 ("2026-09-30") | keep 2026-10-20 (dashboards-review logged 2026-10-20); move 2026-09-30 to `prior_reviewed_date` |
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
| 2026-08-21 14:30Z | /wire:status-sync | complete | 3 artifact repairs, 2 story updates, last_updated 2026-08-19 → 2026-08-21 | Jane Smith | typed | n/a | n/a | n/a |
```

## Edge Cases

- **No `execution_log.md`**: proceed on git and disk evidence alone; note it in the report and offer to create the log with backfilled rows.
- **No governing sprint plan found**: skip 4d, say so in the report. Not an error — not every release is governed by a sprint plan.
- **`last_updated` missing or unparseable**: treat the evidence window as unbounded and propose setting `last_updated` as part of the repair.
- **Shallow clone / no git history**: fall back to log and disk evidence; say so in the report.
- **Droughty releases**: steps are single-action (`status: not_started | complete`), so only rule 4a's file branch and 4c/4e apply — evidenced output on disk proposes `status: complete`.
- **Ticket delivery on a ticket branch**: do not repair the release record from a ticket branch. Say that the roll-up runs on the release branch after the pull request merges, and report drift only.
- **Uncommitted changes on disk**: files on disk count as evidence even when uncommitted; note "uncommitted" in the report so the consultant knows the PR still needs them.
