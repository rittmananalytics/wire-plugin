---
name: project-review
description: Skill for generating a Wire Framework usage review for an engagement. Activates when the user asks to review Wire usage, audit how Wire was used on a project, or generate a project review. Reads only the engagement repository — git history, `.wire/releases/*/status.md` and the full execution log including its outcome, attribution, invocation, duration, token and cost columns where present — and needs no external service, account or telemetry. Produces a structured review document in `.wire/reviews/`.
---

# Project Review Skill

## On Activation

Before proceeding, append a one-line entry to the execution log of the release
being reviewed (`.wire/releases/<release_folder>/execution_log.md`), following
`specs/utils/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | project-review | activated | project review or audit work triggered this skill | <by> | <session> | n/a | n/a |
```

If the file does not exist, create it with the standard header first. If the
review covers several releases, log against the release named in the request, or
the most recently active one. If the repository has no `.wire/` directory, skip
this step.

---

## When This Skill Activates

Activate when the user asks to:

- Review Wire Framework usage for a client or project
- Audit how an engagement was delivered
- Generate a project review, usage report or Wire adoption report
- Understand how Wire was used (or not used) on a project

**Keywords to watch for:**

- "project review", "usage review", "Wire review"
- "how was Wire used on [client]", "audit [client] usage"
- "generate a review for [client]"

---

## What This Skill Reads

Everything comes from the engagement repository. There is no telemetry, no issue
tracker, no meeting recorder and no warehouse query. Any organisation with a
Wire engagement repository can run this review.

| Source | Path | What it gives you |
|---|---|---|
| Execution log | `.wire/releases/*/execution_log.md` | Every Wire command and skill run: when, which command, the outcome, a one-line detail, who it is attributable to, what invoked it, how long it took, and tokens and cost where the metrics hook measured them |
| Release status | `.wire/releases/*/status.md` | Artifact-by-artifact state, approvals, recorded precondition overrides, parked decisions, iterations, the release claim |
| Git history | the repository itself | What actually changed, when, by whom, and in which files, including work done with no Wire command at all |
| Engagement context | `.wire/engagement/context.md` | Client, scope, stakeholders, technology stack, release list, orchestration mode |
| Release briefs | `.wire/releases/*/brief.md` | What each release set out to do |
| Decisions | `.wire/releases/*/decisions.md` | Design decisions recorded during delivery |
| Release-type definition | `release-types/<type>.yaml` in the installed plugin | The artifacts each release type defines, and which are required. This is the denominator for coverage |

Read other local files under `.wire/` as you find them (research notes, call
notes already saved into the repository, iteration records). Never call an
external service to fetch more.

---

## Step 1 — Gather Parameters

Collect two inputs. Ask both in a single message:

> To generate the project review I need two things:
>
> 1. **The engagement repository** — a path to a local clone, or a git URL I
>    should clone. If we are already in it, say so.
> 2. **Client or engagement name** *(optional)* — used in the report title. If
>    you leave it blank I will take it from `.wire/engagement/context.md`.

If the user gives a git URL, clone it to a scratch directory:

```bash
git clone <REPO_URL> <scratch_dir>/<engagement>-review
```

Wait for the answers before proceeding. Do not ask for a telemetry project name,
an issue-tracker key or a meeting-recorder account: this review uses none of
them.

---

## Step 2 — Gather Data (run all sources in parallel)

Run the following in parallel. Do not wait for one before starting the others.

### 2a — The execution logs

Read every `.wire/releases/*/execution_log.md`.

**Read the header first, per file.** The log has grown columns over time, and a
single file can legitimately hold rows of several shapes
(`specs/utils/execution_log.md`, "Legacy five-column rows"):

| Shape | Columns |
|---|---|
| Current (nine) | Timestamp, Command, Result, Detail, By, Session, Duration, Tokens, Cost (USD) |
| Six | Timestamp, Command, Result, Detail, By, Session |
| Four | Timestamp, Command, Result, Detail |

Parse positionally and treat a missing column as **unknown**, never as a value.
A row with no Session column is not `typed`, it is unknown. A row with no metric
columns is unmeasured, not instant and not free. Report the unknowns as their own
count rather than folding them into a percentage. Record which shapes each file
holds and from which date the current shape begins: that date is usually when the
engagement moved to a newer Wire version, and it is worth stating.

Parse each row into: release folder, timestamp, command, result, detail, by,
session, duration, tokens, cost. Then extract the structure inside three of
those fields.

**The Result vocabulary** is closed. Bucket every row by it:

| Result | Meaning for the review |
|---|---|
| `complete` | a generate finished |
| `pass` / `fail` | a validate outcome |
| `approved` / `changes_requested` | a review outcome |
| `override` | a precondition was overridden, or an advisory gate was satisfied by a ruling |
| `mode` | the director handed control over, or took it back |
| `created` / `archived` / `removed` | a release lifecycle event |
| `activated` | a skill fired (the Command column reads `skill`, and Result holds the skill identifier) |

**The Detail field on an `override` row is structured.** Two forms:

```
<artifact>.<step> required <outcome>, was <state> — overridden by <name>: <reason>
<artifact>.<step> required <outcome>, was <state> — ruling <id> (<name>): <reason>
```

Pull out the artifact, the step, the required outcome, the actual state, the
person and the reason. The two forms are different events: the first is a
consultant deciding to proceed past a block, the second is an advisory gate
satisfied by a director's ruling. Count and report them separately.

**The Session field is structured too.** Four families, and the first two carry
more than their family name:

| Value | What to extract |
|---|---|
| `typed` | a person typed the command |
| `orchestrator [a1b2c3]` | the orchestrating session, plus its session id |
| `dbt-developer [staging 1/2]` | the lane name, plus its batch or slice label |
| `autopilot` | an autopilot run |

Count distinct orchestrator session ids and distinct lane names. The lane labels
tell you how work was sliced, and overlapping lane timestamps tell you how much
ran in parallel.

The result set can be large on a long engagement. If it does not fit comfortably
in context, pass the files to a subagent with this brief:

```
Parse the Wire execution logs at <paths>. Each is a markdown table. Read each
file's header first: rows may have nine columns (Timestamp, Command, Result,
Detail, By, Session, Duration, Tokens, Cost), six (no metrics) or four (no By or
Session). Parse positionally. A missing column is UNKNOWN, never a default.

Produce:
1. Row count per column shape, and the date the nine-column shape begins
2. Row count, distinct commands, distinct people (By), date range, active days
3. Count per command, and count per Result value across the closed vocabulary:
   complete, pass, fail, approved, changes_requested, override, mode, created,
   archived, removed, activated
4. Every `override` row parsed into artifact, step, required outcome, actual
   state, person, reason, and whether it is a consultant override ("overridden
   by X:") or a ruling ("ruling R-n (X):"). Keep the reason text verbatim
5. Every `fail` and `changes_requested` row, with every row that followed it for
   the same artifact until it reached pass or approved
6. Per artifact, the full ordered sequence of generate/validate/review rows, so
   rework loops and re-runs are visible
7. Session parsed into family (typed, orchestrator, lane, autopilot, unknown),
   plus distinct orchestrator session ids and distinct lane names with their
   batch labels
8. Every `mode` row, in order, with its Detail
9. Every `skill` row: skill identifier, count, dates
10. Total Duration where present, count of rows with `n/a`, count of rows with no
    Duration column at all
11. Total Tokens and Cost across rows where both are numeric, the row count those
    totals cover, and the count of rows unmeasured
12. Any row whose timestamp is earlier than the row above it, naming both rows
```

### 2b — The release status files

Read every `.wire/releases/*/status.md`. For each release take:

- the release type, the active profile if it has one, and the current phase
- every artifact and the state of its generate, validate and review steps
- the `precondition_overrides` block, in full
- parked or open decisions
- the `## Iterations` table, if the release has one
- `agents.coordinator_session`, if present: the release claim
- `wire_plugin_version` and `last_upgraded_at`, if present

Cross-check the `precondition_overrides` block against the `override` rows in the
log. The two should agree. Where they do not, that is a finding in its own right.

### 2c — Git history

```bash
git log --all --date=short --pretty=format:'%H|%ad|%an|%s' --numstat
```

Build, per commit: SHA, date, author, subject, and the files changed. Also take
the branch list and, where the repository uses pull requests, the merge commits.
Keep the full file-path list per commit: which part of the tree a commit touched
is how you tell artifact work from code work.

### 2d — Engagement context and briefs

Read `.wire/engagement/context.md`, every `.wire/releases/*/brief.md` and every
`.wire/releases/*/decisions.md`. Note `orchestration.mode` if it is set: a
release running in `manual` mode is expected to show `typed` sessions throughout,
and that is not a finding.

### 2e — The release-type definitions

For each release type that appears in the repository, read its
`release-types/<type>.yaml` from the installed plugin. Take the full artifact
list per phase and the `required` flag on each. If a release type's YAML cannot
be found (a `custom` release with generated specs, for example), say so and use
the artifacts named in that release's own `status.md` instead.

---

## Step 3 — Analyse the Data

### Coverage

Three measures, each stated with its denominator:

**Artifact coverage.** Per release: artifacts whose review step reached
`approved` divided by the artifacts the release type marks `required: true`.
Optional artifacts are counted separately, never folded into the required
figure.

**Lifecycle coverage.** Per artifact reached, did all three of generate, validate
and review run? Count artifacts with a complete triad, artifacts that stopped
after generate, and artifacts that stopped after validate.

**Commit coverage.** An estimate, and label it one. A commit counts as covered
when its timestamp falls inside a logged command's run window. The window is the
log row's timestamp through that timestamp plus its Duration. Rows with `n/a`
duration, and rows from a log shape with no Duration column, get a default window
of 30 minutes; state that you used the default and how many rows it applied to.
Report covered commits, uncovered commits and the percentage.

### Rework: what the re-run rows show

The log holds one row per execution, so a re-run is visible as a repeat. This is
the closest thing to a quality signal the record carries, and it is worth
reporting properly.

Per artifact, walk the ordered sequence of its rows and count:

- **rework loops**: each `fail` or `changes_requested` followed by another
  `complete` for the same artifact
- **time to green**: the elapsed time from the first `complete` to the first
  `approved`, and the working time inside that (the sum of the Duration cells,
  where present), so a long calendar wait for a reviewer is not read as effort
- **re-runs with no failure between them**: a `complete` following a `complete`
  with no `fail` in between usually means the command was aborted and restarted,
  and it is worth naming

Rank artifacts by rework loops. The top of that list is where the framework, the
inputs or the brief was hardest to work with, and it is the most useful single
table in the review.

### Sequence

For each artifact, check the order in the log:

- a `complete` (generate) before the first `pass` (validate)
- a `pass` before the first `approved` (review)

Count violations and list them. A violation is either a real gap or an override,
and the override rows tell you which.

### Overrides, rulings and failures

List every `override` row and every `precondition_overrides` entry in full, with
the parsed artifact, step, person and the reason as written. Split consultant
overrides from ruling-satisfied advisory gates: they are different decisions.
Do not summarise these into a count alone: an override is an attributable
decision, and the record exists to be read.

List every `fail` and `changes_requested` row with what followed it.

### How the work was invoked

Count rows by Session family: `typed`, `orchestrator`, lane, `autopilot`, plus
unknown for rows from an older log shape. This says whether the engagement was
driven by typed commands, by the release director model, or by autopilot, and it
is the one measure that separates a 4.0-era engagement from a 3.x-era one.

Then go further than the family count:

- **Orchestrating sessions**: how many distinct session ids, and what each one
  covered. A release should carry one claim at a time
  (`agents.coordinator_session` in `status.md`), so several ids in one window is
  worth a look.
- **Lanes**: which lanes ran, how often, and with what batch labels. Overlapping
  lane timestamps show how much ran in parallel and where the real throughput
  came from.
- **Control handovers**: every `mode` row, in order. These mark where the
  director took the keyboard back, and a cluster of them usually sits next to a
  hard problem.
- **Single-writer conformance**: in orchestrated mode only the orchestrating
  session appends to the log. A lane-labelled row that appears where the mode was
  orchestrated is a record defect, not throughput.

### Skill activations

The log captures skills as well as commands: `skill` in the Command column, the
skill identifier in Result. Report which skills fired, how often and when. A
skill that fires repeatedly next to uncovered commits is a signal that work was
being done with the skill rather than the command, which is a legitimate finding
and not necessarily a fault.

### Effort and cost

Sum Duration per release and per command where present. Say how many rows carry
`n/a` and how many came from a log shape with no Duration column at all.

Sum Tokens and Cost only across rows where the metrics hook filled both, and
state the number of rows those totals cover and the number unmeasured. Where
coverage is high enough to be meaningful, give cost per release, cost per
artifact and the most expensive individual commands. Never estimate a token count
or a cost for a row that carries `n/a`: the spec forbids it, and a guessed figure
in a client-facing audit trail is worse than a blank.

Note that the metrics hook runs on Claude Code only. An engagement delivered on
another runtime will show no metrics at all, and that is a fact about the
runtime, not about the work.

### Record defects

The log is meant to be append-only and in order. Report, without judgement:

- rows whose timestamp precedes the row above them
- `override` rows in the log with no matching `precondition_overrides` entry in
  `status.md`, or the reverse
- artifacts marked done in `status.md` with no corresponding row in the log
- fields still reading `TBD` or `null` in an artifact block that has passed review

`specs/utils/status_sync.md` classifies the same drift and can repair it. Point to
it rather than repairing anything here: this skill reads, it does not write to the
record.

### Work done outside Wire

This is where the git history earns its place. For every commit not covered by a
command window, group by what it touched:

- `.wire/` artifact files changed with no command run: the artifact was edited by
  hand, or produced conversationally
- code, model or configuration files with no command run: delivery work done
  outside the framework
- everything else

For each group, give the commit count, the date range, the people involved and
the file paths. Quote commit subjects where they explain what was being done.
Then identify which Wire command would have produced that work, where one exists.

### Gaps

- Wire commands the release type defines, that were directly applicable, and that
  never ran. Cite the commit or the artifact file that shows the equivalent work
  was done by hand.
- Recurring manual patterns: the same kind of uncovered commit appearing five or
  more times with no Wire command that covers it.

---

## Step 4 — Write the Review Document

Create the review at:

```
.wire/reviews/{YYYY-MM}-wire-usage-review.md
```

in the repository under review, using today's year and month. If the user asks
for it somewhere else, write it there instead.

The document follows this structure:

---

```markdown
# Wire Framework Usage Review — {ENGAGEMENT_NAME}

**Engagement:** {ENGAGEMENT_NAME}
**Review date:** {MONTH YEAR}
**Evidence:** git history, `.wire/releases/*/status.md`, `.wire/releases/*/execution_log.md`
**Period covered:** {FIRST_EVIDENCE_DATE} – {LAST_EVIDENCE_DATE}
**People:** {LIST, from the execution log By column and git authors}

---

## Contents

1. Summary
2. Engagement Overview
3. Coverage
4. Rework and Time to Green
5. Release-by-Release Analysis
6. Sequence, Overrides and Failures
7. How the Work Was Invoked
8. Effort and Cost
9. Work Done Outside Wire
10. Gaps: Commands That Applied and Never Ran
11. Recurring Manual Patterns
12. Record Quality
13. Recommendations

---

## 1. Summary

[3 to 5 paragraphs. Lead with the coverage figures and the single most important
finding. Cover what Wire was used for against what the release types define, where
rework concentrated, the highest-friction manual work, and the top three
recommendations.]

---

## 2. Engagement Overview

### Client and scope
[1 to 2 paragraphs from context.md]

### Technology stack
[Table: layer, technology. From context.md]

### Releases
[Table: # | folder | release type | status | orchestration mode | scope]

### Stakeholders
[Table from context.md]

### Evidence shape
[Which log column shapes appear, the row count of each, and the date the current
nine-column shape begins. State plainly what is unknowable from the older rows.]

---

## 3. Coverage

### Artifact coverage
[Table: release | required artifacts | approved | coverage % | optional artifacts approved]

### Lifecycle coverage
[Table: release | artifacts reached | full generate-validate-review triad | stopped after generate | stopped after validate]

### Commit coverage
[Table: release | commits | covered by a command window | uncovered | covered %]
[State the window rule used and how many rows took the 30-minute default.]

### Commands run
[Table: command | runs | outcome mix. Every command that appears in the log.]

### Skills activated
[Table: skill | activations | date range | what was happening around them]

---

## 4. Rework and Time to Green

### Artifacts by rework loops
[Table: artifact | generate runs | validate fails | changes requested | rework loops | time to green (elapsed) | working time (summed duration)]
[Ranked by rework loops, highest first.]

### What the rework was
[One short paragraph per artifact at the top of that table: what the fail details
and review feedback actually said, quoted from the Detail column.]

### Re-runs with no failure between them
[Table: artifact | date | rows | likely cause]

---

## 5. Release-by-Release Analysis

[One section per release:
- release type, profile, dates, people, orchestration mode
- commands run, in order, with outcomes
- artifacts approved, artifacts started and not finished, artifacts never started
- rework inside this release
- what the git history shows happened alongside
- status.md quality: fields filled, fields left as TBD or null
- gaps specific to this release]

---

## 6. Sequence, Overrides and Failures

### Sequence violations
[Table: artifact | what the log shows | whether an override covers it]

### Consultant overrides
[One row per override: date, artifact, step, required outcome, actual state, who,
reason as written. Reproduce the reason verbatim.]

### Advisory gates satisfied by a ruling
[Same shape, with the ruling id.]

### Failures and requested changes
[Table: date | command | result | detail | what followed | time to a passing or approved state]

---

## 7. How the Work Was Invoked

### Invocation mix
[Table: typed | orchestrator | lane | autopilot | unknown, with counts and percentages.
Percentages exclude the unknown rows; say so.]

### Orchestrating sessions
[Table: session id | date range | releases touched | commands dispatched]

### Lanes
[Table: lane | runs | batch labels | date range | commands run]
[Note where lane timestamps overlap, and what ran in parallel.]

### Control handovers
[Table: date | direction | detail. Every `mode` row, in order.]

---

## 8. Effort and Cost

### Logged duration
[Table: release | total duration | rows with a duration | rows with `n/a` | rows from a log shape with no duration column]

### Measured tokens and cost
[Table: release | tokens | cost | rows covered | rows unmeasured]
[If measurement coverage is below a third of rows, give the totals and say they
are not representative rather than extrapolating.]

### Most expensive commands
[Table: command | runs measured | tokens | cost | cost per run]

---

## 9. Work Done Outside Wire

### `.wire/` artifacts edited by hand
[Table: file | commits | dates | author | what the commit subjects say]

### Delivery work with no command run
[Table: area of the tree | commits | dates | authors | what was being done]

### Everything else
[Table: same shape]

---

## 10. Gaps: Commands That Applied and Never Ran

[Table: command | what the release type expects it to produce | evidence the work
was done by hand (commit SHA or artifact path) | why it probably was not used]

---

## 11. Recurring Manual Patterns

[One subsection per pattern:
- pattern name, and a proposed command name if there is no command for it
- evidence: commit subjects and paths, with the occurrence count
- what a command would do, what it would take as input and what it would produce]

Only include patterns with five or more occurrences. If there are none, say so.

---

## 12. Record Quality

[Table: defect | count | examples]
[Covers out-of-order timestamps, overrides in the log with no `status.md` entry
and the reverse, artifacts done in `status.md` with no log row, and fields still
reading TBD or null after review. Close with a pointer to
`/wire:status-sync <release-folder>` as the repair path.]

---

## 13. Recommendations

[Numbered R1 to Rn. Each with a title, a priority (high, medium, low), the
problem it solves, the proposed change and the spec file to create or modify.]

Group by: (a) new Wire commands, (b) changes to existing commands, (c) process
and adoption changes.

---

## Appendix: Evidence

[Table: source | path | records]
[State the commit range read, the release folders read, the execution log row
count and its column-shape breakdown. Name anything that was missing: a release
with no execution log, a release type whose YAML could not be found, a period
with no commits, a runtime that wrote no metrics.]

---

*Review generated {DATE} from the repository at {REPO_PATH}, commit {HEAD_SHA}.
Evidence cut-off: {LAST_EVIDENCE_DATE}.*
```

---

## Step 5 — Offer to Commit

Show the user the file path and a short summary of the findings. Then offer to
commit it:

```bash
git add .wire/reviews/
git commit -m "docs: Wire Framework usage review ({YYYY-MM})"
```

Do not push, and do not commit to the default branch without asking. If the user
wants it pushed, branch first and say which branch you used.

---

## Quality Checks Before Finishing

- [ ] Every section is populated, with no `[placeholder]` text left
- [ ] Each coverage figure states its denominator
- [ ] Commit coverage is labelled an estimate, and the window rule is stated
- [ ] Rows from older log shapes are counted as unknown, never as a default value
- [ ] The log's column-shape breakdown appears in Section 2 and the appendix
- [ ] Every override appears with its reason as written, not summarised, and
      consultant overrides are separated from ruling-satisfied advisory gates
- [ ] The rework table is ranked and quotes the actual fail and review details
- [ ] Orchestrator session ids and lane labels are reported, not just the family
      counts
- [ ] Token and cost totals name the rows they cover and the rows unmeasured, and
      no `n/a` row has been estimated
- [ ] Every release folder in the repository has its own section in Section 5
- [ ] Gap analysis cites a commit SHA or an artifact path for each row
- [ ] Recurring patterns have five or more documented occurrences, or the section
      says there are none
- [ ] Record defects are reported as findings, and nothing in the record was
      repaired by this skill
- [ ] The appendix names everything that was missing from the evidence
- [ ] No claim in the review depends on a source outside the repository

---

## Notes

- **A release with no execution log** is a normal finding, not an error. It means
  the work was done outside Wire commands, or the release predates the log. Say
  so in the appendix and fall back to git history and `status.md` for that
  release.
- **A repository with no `.wire/` directory** cannot be reviewed for Wire usage.
  Say so plainly and offer a git-only summary of what was delivered instead.
- **Older rows are shorter, not emptier.** A four- or six-column row is missing
  the columns, not carrying a default. Never report an engagement as "0%
  orchestrated" when the rows simply predate the Session column.
- **Duration, Tokens and Cost are often `n/a`.** The metrics hook fills them on
  Claude Code only, and only for runs it saw. Report what is there and count what
  is not. Never estimate.
- **Commit coverage is a heuristic.** A commit can fall inside a command's window
  and have nothing to do with it, and a commit made an hour after a command can be
  its direct result. Use it as a rough shape, and let the per-release analysis in
  Section 5 carry the real judgement.
- **The By column and the git author can disagree.** `By` is the git user
  configured on the machine that ran the command; the commit author is whoever
  committed. Where they differ, report both rather than picking one.
- **Command names change between versions.** A log row naming a command that no
  longer exists tells you which Wire version the engagement was on. Note it in
  Section 5 rather than treating it as an error.
- **A high override count is not automatically a problem.** The gate exists to
  make a skip visible and attributable, so a recorded override is the mechanism
  working. Read the reasons: a pattern in them is the finding, not the count.
- Review documents live in the engagement repository, under `.wire/reviews/`, so
  the record stays with the work it describes.
