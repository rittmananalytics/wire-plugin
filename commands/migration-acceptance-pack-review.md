---
description: Present migration batch acceptance pack for stakeholder sign-off
argument-hint: <release-folder> [--batch N]
---

# Present migration batch acceptance pack for stakeholder sign-off

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Present migration batch acceptance pack for stakeholder sign-off
argument-hint: <release-folder> [--batch N]
---

## Auto-Delegation

This is a **review command**. Do NOT delegate to a subagent. The workflow below must execute in the main session — it requires real-time human interaction to capture the reviewer's decision.

---

## Data Safety — Read Before Proceeding

Before proceeding, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT run INSERT, UPDATE, DELETE, CREATE TABLE, DROP, or TRUNCATE
  against the source platform. Query it only.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not write to these):
  [list each production project ID]
```

If the current working context would write to a source platform or a blocked production project, stop immediately and report the conflict.

---

# Migration Acceptance Pack — Review

## Purpose

Formal stakeholder sign-off on a completed migration batch. Once all models in a batch have reached a terminal state (PASSED or FAILED) in the iterative translation + equivalency loop, this command presents the acceptance pack to the reviewer and records their decision. It is the human gate before proceeding to the next batch — or, if all batches are complete, before beginning cutover preparation.

## Prerequisites

- `dbt_migration.batch_N_generate: complete` in status.md
- `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md` exists

## Flags

- `--batch N` — review the acceptance pack for batch N specifically

## Workflow

### Step 1: Determine Which Batch to Review

1. If `--batch N` is supplied, use that batch number.
2. Otherwise, scan `.wire/releases/$ARGUMENTS/migration/dbt/` for all `acceptance_pack_batch_*.md` files. For each, check status.md for `migration_acceptance_pack.batch_{N}_review`. Select the highest N where the review status is `pending` or absent.
3. If no batch has a pending acceptance pack, list all batches and their current review status, then ask:
   ```
   All acceptance packs have been reviewed. Which batch would you like to re-review?
   Enter a batch number, or press Enter to cancel:
   ```
4. Load `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md`.

### Step 2: Retrieve Meeting Context

Follow `specs/utils/meeting_context.md`. Search for transcripts mentioning: "migration", "batch N", "acceptance", "sign-off", "equivalency".

If relevant meetings are found, output a brief bullet list — no more than five items — before presenting the acceptance pack. Label it clearly:

```
## Context from recent meetings
- [decision or action item — source: meeting title, date]
```

If no relevant meetings are found, proceed silently.

If a document store is configured, follow `specs/utils/docstore_fetch.md`:
- Pass `artifact_id: migration_acceptance_pack`, `artifact_name: acceptance_pack_batch_{N}`, `file_path: migration/dbt/acceptance_pack_batch_{N}.md`, and `project_id: $ARGUMENTS`
- Surface any reviewer comments added to the document store page since generation alongside the Fathom context

### Step 3: Present the Acceptance Pack

Output the full content of `acceptance_pack_batch_{N}.md`, then present the reviewer prompt:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[wire] Migration — Batch N Acceptance Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Acceptance pack content above]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reviewer — please confirm before responding:

  [ ] You have reviewed the model-by-model results table
  [ ] FAILED models have been noted and escalated, accepted
      as known gaps, or scheduled for a follow-up batch
  [ ] You are satisfied that PASSED models meet the
      equivalency thresholds agreed in the migration strategy

Your decision:

  A  Approve        — batch accepted, proceed to next batch
                      or cutover preparation
  R  Reject         — batch must be re-run or specific models
                      fixed before proceeding
  H  Hold           — accepted with reservations (list them);
                      proceed to next batch while tracking gaps

Enter A, R, or H:
```

Use `AskUserQuestion` for the decision:

```json
{
  "questions": [{
    "question": "What is your decision on Batch N?",
    "header": "Batch N Acceptance Decision",
    "options": [
      {"label": "Approve", "description": "Batch accepted — proceed to next batch or cutover preparation"},
      {"label": "Reject", "description": "Batch must be re-run or specific models fixed before proceeding"},
      {"label": "Hold", "description": "Accepted with reservations — list them; proceed to next batch while tracking gaps"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect Sign-Off Details

Ask:
```
Reviewer name (leave blank to use the engagement stakeholder name from status.md):
```

Read `engagement.stakeholder_map` from status.md if blank.

If the decision is **Reject** or **Hold**, ask:
```
Please describe the issues or reservations to record:
```

Capture:
- `decision` — Approve / Reject / Hold
- `reviewer` — name
- `date` — today's date (`YYYY-MM-DD`)
- `notes` — free-text feedback (Reject or Hold only; empty string for Approve)

### Step 5: Append Sign-Off Block to the Acceptance Pack

Append the following section to `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md`:

```markdown
## Sign-off

| Field | Value |
|-------|-------|
| Decision | APPROVED / REJECTED / HOLD |
| Reviewer | <reviewer name> |
| Date | <YYYY-MM-DD> |
| Notes | <feedback or reservations, or — if none> |
```

Substitute the actual values. Do not modify any earlier content in the file.

### Step 6: Update status.md

Write the following fields under `artifacts.migration_acceptance_pack`:

```yaml
artifacts:
  migration_acceptance_pack:
    batch_{N}_review: approved | rejected | hold
    batch_{N}_reviewer: "<reviewer name>"
    batch_{N}_review_date: "<YYYY-MM-DD>"
    batch_{N}_notes: "<feedback or empty>"
```

Use `approved`, `rejected`, or `hold` as the status value — lowercase, no spaces.

### Step 7: Output Review Summary and Next Steps

**If Approved**:

```
## Batch N — Accepted

Reviewed by: [reviewer], [date]

[If more batches remain:]
Next batch:
  /wire:dbt-migration-generate $ARGUMENTS --batch [N+1]

[If all batches are complete:]
All batches accepted. Proceed to cutover preparation:
  /wire:cutover-generate $ARGUMENTS
```

**If Rejected**:

```
## Batch N — Rejected

Reviewed by: [reviewer], [date]

Issues raised:
  [notes]

Re-run the batch after addressing the issues above:
  /wire:dbt-migration-generate $ARGUMENTS --batch N
```

**If Hold**:

```
## Batch N — Accepted with Reservations

Reviewed by: [reviewer], [date]

Reservations recorded:
  [notes]

Reservations are logged in status.md. Proceed to the next batch:
  /wire:dbt-migration-generate $ARGUMENTS --batch [N+1]

Track the reservations to resolution before cutover.
```

### Step 8: Post-Execution Hooks

Run the following in order:

1. **Execution log** — follow `specs/utils/execution_log.md`. Record the outcome as `approved`, `rejected`, or `hold`. Detail should include reviewer name.

2. **Jira sync** — follow `specs/utils/jira_sync.md`:
   - `release_folder`: `$ARGUMENTS`
   - `artifact`: `migration_acceptance_pack`
   - `action`: `review`
   - Status: the review outcome just written to status.md
   - Include reviewer name in the Jira comment; include feedback text if rejected or hold

3. **Doc store sync** — follow `specs/utils/docstore_sync.md` to push the updated acceptance pack (with sign-off block appended) to Confluence or Notion. Push regardless of decision — the sign-off record should be visible to all stakeholders in the document store.

4. **Auto-commit** — follow `specs/utils/commit.md`:
   - `release_folder`: `$ARGUMENTS`
   - `artifact`: `migration_acceptance_pack`
   - `action`: `review`

## Review Gate

Stakeholder sign-off on each batch's acceptance pack is required before proceeding to the next batch or to cutover preparation. The `/wire:cutover-generate` command will not proceed unless all batches show `batch_{N}_review: approved` or `batch_{N}_review: hold` in status.md. A `rejected` batch must be re-run and re-reviewed.

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
