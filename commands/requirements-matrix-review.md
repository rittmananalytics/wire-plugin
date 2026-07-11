---
description: Internal RA review of the requirements matrix
argument-hint: <release-folder>
---

# Internal RA review of the requirements matrix

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
description: Internal RA review of the requirements matrix
---

# Requirements Matrix — Review

## Purpose

Internal RA review of the consolidated requirements matrix before the three analyses are run. Reviewer is the Head of Delivery + one peer Lead Consultant. Goal: catch classifications that don't match the supporting evidence, missed conflicts, or under-coverage that the analyses would otherwise inherit.

This review is **not** sponsor-facing. The sponsor sees the analyses output, not the matrix.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix_validation.md`
- All interview write-ups

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read the matrix, validation report, and reference the interview files.

### Step 2: Pull supporting context

If a document store is configured, follow `specs/utils/docstore_fetch.md` to pull any reviewer comments on the Confluence/Notion mirror of the matrix.

### Step 3: Present for review

Output:
1. The validation result and any FAILs/WARNINGs
2. The Hierarchy and PPT tag distribution previews
3. A list of the Conflicts log entries

Then prompt the reviewer:

```
Review focus (do not skip):

1. Hierarchy classifications — sample at least 5 rows and confirm each is the LOWEST tier whose absence blocks the requirement. Refusing to drop a requirement to `clean` because it sounds nicer is the most common failure here.

2. PPT classifications — for any row tagged `technology`, ask: is this really a technology problem, or is it a process problem dressed up? The playbook's failure-mode table specifically calls out the temptation to default to `technology`.

3. Conflicts — are there genuine contradictions buried in the matrix that aren't in the Conflicts log? If so, they need to surface in the Findings Playback as forced-decision items.

4. Under-coverage — are there in-scope domains where the matrix is suspiciously thin? Either there's nothing there (a finding in itself), or interviews were missing.

5. Sponsor's voice — does any row directly contradict something the sponsor said? Flag.
```

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the internal RA review of the requirements matrix?",
    "header": "Requirements Matrix Review",
    "options": [
      {"label": "Approved", "description": "Matrix is ready — proceed to the three analyses"},
      {"label": "Approved with reclassifications", "description": "Specific rows need tag changes; apply inline"},
      {"label": "Re-consolidate", "description": "Material issues with de-duplication or missing rows — regenerate from interviews"},
      {"label": "Reopen interviews", "description": "Gaps require a follow-up interview or a missed P0/P1 to be booked"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture corrections

If reclassifications were called, apply them inline. For each: record the original tag, new tag, and reviewer reason in a `## Review Decisions` section.

### Step 5: Update status

```yaml
artifacts:
  requirements_matrix:
    review: complete    # or "pending_rework" / "pending_followup"
```

### Step 6: Output summary

```
## Requirements Matrix Review Complete

**Outcome**: [Approved / Approved with reclassifications / Re-consolidate / Reopen interviews]
**Reclassifications applied**: [N]
**Conflicts added to log**: [N]

### Next Steps

[If approved]:
Run the three analyses (Hierarchy / PPT / Maturity Curve):
/wire:discovery-analyses-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

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
