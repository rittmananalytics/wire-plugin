---
description: Present migration batch acceptance pack for stakeholder sign-off
argument-hint: <release-folder> [--batch N 
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
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Present migration batch acceptance pack for stakeholder sign-off
argument-hint: <release-folder> [--batch N | --wave id]
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

- `--batch N` — review the acceptance pack for topological batch N specifically (the `dbt_audit.batch_number` scheme — `acceptance_pack_batch_N.md`).
- `--wave <id>` — review the acceptance pack for execution wave `<id>` specifically (the `migration_batching.csv` scheme — `acceptance_pack_batch_{wave_id}.md`, since `dbt-migration-generate` Step 1w substitutes the wave id directly into the same `batch_{N}` filename template). Accepts zero-padded (`B01`) or bare (`1`) forms, normalised identically to `dbt-migration-generate`'s `--wave`. Wave-id form and normalisation are the shared contract in `specs/utils/wave_resolution.md` (normative; accepts `2`, `B02`, `b2`, or the `W02` display form). `--batch` and `--wave` read different numbering schemes and cannot be combined — abort if both are supplied: `[wire] --batch and --wave read different numbering schemes and cannot be combined. Pick one.`

## Workflow

### Step 1: Determine Which Batch to Review

1. If `--batch N` is supplied, use that batch number. If `--wave <id>` is supplied, normalise it (per the **Flags** section) and use the normalised wave id in place of `N` everywhere below (`acceptance_pack_batch_{wave_id}.md`, `migration_acceptance_pack.batch_{wave_id}_review`).
2. Otherwise, scan `.wire/releases/$ARGUMENTS/migration/dbt/` for all `acceptance_pack_batch_*.md` files — this glob already matches both topological-batch and wave-labelled filenames. For each, check status.md for `migration_acceptance_pack.batch_{N}_review`. Select the highest N where the review status is `pending` or absent (comparing wave ids and topological batch numbers as separate pools — don't interleave `B01` with `3`).
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
