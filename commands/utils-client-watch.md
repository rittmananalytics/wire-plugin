---
description: One client-watch tick — channel replies to tracked posts recorded in the answers ledger, merged client PRs advance the register and fire the post-merge action
argument-hint: <release-folder>
---

# One client-watch tick — channel replies to tracked posts recorded in the answers ledger, merged client PRs advance the register and fire the post-merge action

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

## Workflow Specification

---
description: One client-watch tick — read the client channel for replies to tracked posts and the client repos for merged PRs, record rulings in the answers ledger, fire the configured post-merge action
argument-hint: <release-folder>
---

# Utils — Client Watch

## Purpose

One tick of the client-communication watch (#179). During delivery, two classes of client signal arrive asynchronously and go stale when nobody is watching: replies in the client channel (rulings, answers to open asks) and merges of our PRs in the client repos. On a live engagement, both ran as session-local practice — and its absence as product produced two documented failures: questions the client had already answered were re-asked (twice), and merged PRs sat undetected until someone thought to look.

This command is designed to run headless on a schedule (a cron/scheduler invoking one tick), configured entirely from status.md — nothing is hardcoded.

## Configuration (status.md)

```yaml
client_comms:
  slack_channel_id: "<id>"          # required; unset disables the tick cleanly with a note
  ask_list_max: 5                   # consumed by utils-ask-list-generate, kept here as the one config block
  answers_ledger: "decisions.md"    # release-relative path to the dated answers ledger
  post_merge_action: "/wire:equivalency-post-merge-verify"   # fired when an own PR merges
```

Client repos come from `migration.client_repos` — the same list `dbt-migration-batch-raise` and `utils-ci-parity` read; this command adds no second repo registry.

## State

`.wire/releases/$ARGUMENTS/client_comms/watch_state.json` — the tracked-post list (message refs this release has posted to the channel and is awaiting replies on) and the last-tick cursors (per-channel last-read timestamp, per-repo last-seen merged PR). Rewritten at the end of each tick; a killed tick loses at most one tick's cursor advance and the next tick re-reads idempotently.

## Workflow (one tick)

### Step 1 — Read the channel

Read `client_comms.slack_channel_id` since the last cursor. For each reply that answers a tracked post or states a ruling ("option B", "approved", "use the June floor"), append an entry to the answers ledger (`client_comms.answers_ledger`):

```markdown
## {{DATE}} — <topic>
**Asked**: <the tracked post's question, one line>
**Answer (verbatim)**: "<the client's words, quoted exactly>"
**Consequence**: <what this settles — the config set, the gate cleared, the approach ruled out>
**Ref**: <channel permalink>
```

The verbatim quote is the point: a paraphrase is how a ruling drifts. Remove the answered post from the tracked list. A reply that is discussion rather than an answer stays tracked, noted.

### Step 2 — Read the client repos

For each `migration.client_repos` entry, `gh pr list --state merged` since the last cursor, filtered to this release's PRs (the register's `pr_url` values). For each newly-merged PR:

1. Advance its models in `migration/migration_register.csv` to `delivery_stage: merged` (the same transition `dbt-migration-batch-raise` Step 7 performs on demand — one contract, two triggers).
2. Fire `client_comms.post_merge_action` for the merged models (default: `/wire:equivalency-post-merge-verify`).

### Step 3 — Report once

Terminal report only (the fleet's report-once protocol, `specs/utils/migration_fleet.md`): new answers recorded (count + topics), PRs merged (count + urls), actions fired, posts still tracked. A tick with nothing new reports one line and exits.

### Step 4 — Update state

Rewrite `client_comms/watch_state.json` with the advanced cursors and the surviving tracked-post list.

## The ledger as a gate

The answers ledger is not an archive — it is the input to the re-ask guard. Any command about to surface a question to the client (`utils-ask-list-generate` mechanically; anything else by convention) checks the ledger first: an entry matching the question means the client has already answered, and the answer is used, not re-asked. Re-asking an answered question is the single fastest way to burn client patience with an agentic delivery.

## Post-Execution Hooks

After the tick, run:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

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

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
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
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
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

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
