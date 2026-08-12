---
description: Draft the top-N client ask list from the register's blocker taxonomy — capped, and guarded against re-asking anything the answers ledger holds
argument-hint: <release-folder> [--max N]
---

# Draft the top-N client ask list from the register's blocker taxonomy — capped, and guarded against re-asking anything the answers ledger holds

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
description: Derive the top-N client ask list from the register's blocker taxonomy, capped and guarded against re-asking anything the answers ledger already holds
argument-hint: <release-folder> [--max N]
---

# Utils — Ask List Generate

## Purpose

Derives the client ask list — the handful of questions and unblocks the delivery needs from the client right now — from the release's own state, instead of a consultant compiling it by hand (#179). Two documented failures motivate the two rules baked in: a 50-item ask list the client pushed back on in writing (hence the hard cap), and questions re-asked after the client had already answered them (hence the ledger guard).

**The output is a draft for the consultant to review and send. It is never auto-posted.**

## Configuration

- `client_comms.ask_list_max` in status.md (default 5) — the hard cap; `--max N` overrides for one run.
- `client_comms.answers_ledger` (default `decisions.md`) — the dated answers ledger `utils-client-watch` maintains.

## Workflow

### Step 1 — Collect candidate asks from the blocker taxonomy

Candidates come from machine state, not memory — each with its blocking reason, the models/objects it blocks, and the count:

- Register rows blocked on client-side inputs: `deferred` models whose `notes` name a client dependency (a source object not yet landed, a grant not yet made).
- `dbt-migration-batch-raise --dry-run` block reasons that resolve to a client action (an unmerged client base branch, a repo permission).
- Unresolved tenant-predicate registry rows awaiting a client ruling (`region-tagging-review` pile).
- Open human gates whose owner is the client (`data-residency-assessment-review` DPO items, UAT attestations).
- `migration-drift` findings needing a client decision (a removed source model with live downstream syncs).
- Any `cross_release_triggers` entry whose condition needs client-side confirmation.

### Step 2 — The re-ask guard (mechanical)

Check every candidate against the answers ledger before it can enter the list. A candidate whose topic matches a ledger entry — same object/gate/config key, or a normalised-question match — is **refused a slot**: it is listed separately under "already answered" with the ledger entry's date and verbatim answer, and the answer is applied instead of the question being re-asked. Tests mirror this guard (`wire/tests/platform_migration/validate_ask_list_guard.py`).

### Step 3 — Rank and cap

Rank the surviving candidates by unblock value (models unblocked, gates cleared — largest first; a cutover-path blocker outranks a long-tail model). Take the top `ask_list_max`. Everything below the cap is retained in the draft's "parked asks" appendix, not silently dropped — the cap bounds what the client is asked, not what the release tracks.

### Step 4 — Write the draft

`.wire/releases/$ARGUMENTS/client_comms/ask_list_{{DATE}}.md`: the capped list (one ask per line: the question, what it unblocks, the count), the "already answered" section (asks the guard refused, with their ledger answers), and the parked appendix. The consultant edits and sends; on sending, `utils-client-watch` tracks the post for replies.

### Step 5 — Report

One line per section count. Never post to any channel from this command.

## Post-Execution Hooks

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
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
