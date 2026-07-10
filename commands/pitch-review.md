---
description: Review pitch with stakeholders and record appetite decision
argument-hint: <release-folder>
---

# Review pitch with stakeholders and record appetite decision

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
description: Review pitch with stakeholders and record the appetite decision
---

# Pitch Review Command

## Purpose

Facilitates the pitch review with decision-makers. This is the "betting table" moment — the key stakeholders decide whether to bet the team's time (the appetite) on this shaped solution. Records the outcome: approved, approved with conditions, or rejected with reasons.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/pitch.md` — must be validated

## Workflow

### Step 1: Locate and Read the Pitch

Resolve release folder. Read `planning/pitch.md`. Check status.md to confirm validation has been run.

### Step 2: Retrieve Meeting Context

Follow `specs/utils/meeting_context.md`:
- Search for transcripts mentioning the client, the release name, or pitch-related terms ("appetite", "bet", "scope")
- Surface any prior stakeholder concerns or decisions about scope (2–3 bullet points maximum)

If a document store is configured, follow `specs/utils/docstore_fetch.md`:
- Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
- This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
- Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context

### Step 3: Present the Pitch for Review

Output the full pitch content, prefaced with any meeting context.

Then output:
```
## Pitch Review — Betting Table

This is the decision point. Reviewing stakeholders decide whether to bet [appetite] on this shaped solution.

Key questions for reviewers:
1. Is the problem worth solving now?
2. Is the proposed solution directionally right (even if details will change)?
3. Is [appetite] the right time budget for this?
4. Are the no-gos and rabbit holes correctly identified?
```

### Step 4: Record the Appetite Decision

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the pitch review?",
    "header": "Pitch Review — Betting Table",
    "options": [
      {"label": "Approved — bet confirmed", "description": "We're committing the appetite to this shaped solution"},
      {"label": "Approved — appetite adjusted", "description": "The solution is right but the time budget needs to change"},
      {"label": "Approved — scope adjusted", "description": "The appetite is right but the solution scope needs narrowing"},
      {"label": "Needs reshaping", "description": "Directionally interesting but the solution needs more work before we bet"},
      {"label": "Rejected", "description": "Not the right problem or not the right time — record reasons"}
    ],
    "multiSelect": false
  }]
}
```

### Step 5: Collect Decision Details

Ask directly in chat:
```
Record the key decisions and reasoning from this review:
(e.g. "Approved. Narrowed to dashboard only, pipeline out of scope for this release. Start date: 15 April.")
```

### Step 6: Update the Pitch (if appetite or scope adjusted)

If appetite was adjusted, update Section 2 of pitch.md with the confirmed appetite.
If scope was adjusted, update Sections 5 (No-gos) and 8 (Downstream Releases) as appropriate.

Append a `## Review Record` section to pitch.md:
```markdown
## Review Record

**Date**: [today's date]
**Outcome**: [Approved / Adjusted / Needs reshaping / Rejected]
**Confirmed appetite**: [Small batch 1–2 weeks / Big batch 6 weeks]
**Key decisions**: [Summary of reviewer decisions]
**Conditions**: [Any conditions on the approval, if applicable]
```

### Step 7: Update Release Status

```yaml
pitch:
  review: "complete"   # or "pending_rework" / "rejected"
```

### Step 8: Output Review Summary

```
## Pitch Review Complete

**Outcome**: [outcome]
**Confirmed appetite**: [appetite]

### Next Steps

[If approved]:
Formalise as a release brief:
/wire:release-brief-generate [folder]

[If needs reshaping]:
Update the pitch and re-validate:
/wire:pitch-generate [folder]  (to regenerate with new inputs)
/wire:pitch-validate [folder]
/wire:pitch-review [folder]

[If rejected]:
Record the rejection reasons in the problem definition and consider whether to:
- Reframe the problem
- Revisit at a later date
- Close this discovery release
```

### Step 9: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Output Files

- Updated `.wire/releases/[folder]/planning/pitch.md` (review record appended)
- Updated `.wire/releases/[folder]/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

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
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
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
