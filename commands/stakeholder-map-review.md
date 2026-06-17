---
description: Confirm stakeholder map with sponsor
argument-hint: <release-folder>
---

# Confirm stakeholder map with sponsor

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
description: Confirm the stakeholder map with the sponsor
---

# Stakeholder Map — Review

## Purpose

Sponsor confirmation of the stakeholder map. This is the first sponsor-facing review in a SOP discovery release — its job is to confirm who RA will interview, lock in booking owners, and surface any politically sensitive omissions before Phase 2 starts. Usually folded into the kick-off meeting but can be run separately if the kick-off has already happened.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map_validation.md` (if present)

## Workflow

### Step 1: Locate the map

Resolve `$ARGUMENTS`. Read both files.

### Step 2: Pull meeting context

Follow `specs/utils/meeting_context.md`:
- Search Fathom for kick-off or pre-kick-off conversations referencing this release
- Look for sponsor mentions of named individuals, "definitely include X", "skip Y", "ask Z about A"

### Step 3: Present for review

Output the stakeholder table and the domain-coverage summary from the validation report. Highlight:
- Any FAIL items from validation
- Any P0/P1 marked `Sceptical` (sponsor should know who's pushing back)
- Any domains with zero coverage

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the stakeholder map review with the sponsor?",
    "header": "Stakeholder Map Review",
    "options": [
      {"label": "Approved", "description": "Sponsor confirmed the list; bookings can start"},
      {"label": "Approved with additions", "description": "Sponsor added named stakeholders or changed priorities"},
      {"label": "Approved with removals", "description": "Sponsor flagged people RA should not interview (political / scheduling)"},
      {"label": "Needs rework", "description": "Sponsor wants the map redrafted (rare — usually means scope changed)"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect detailed changes

Ask:
```
Record any specific changes (additions, removals, priority shifts):
```

For each change, update the map directly:
- Add rows for new stakeholders
- Remove (or mark `OUT - sponsor decision`) for removals — do not silently delete; note them so the audit trail is preserved
- Update priorities/booking owners as instructed

### Step 5: Update status

```yaml
artifacts:
  stakeholder_map:
    review: complete    # or "pending_rework"
```

### Step 6: Output review summary

```
## Stakeholder Map Review Complete

**Outcome**: [Approved / Approved with additions / Approved with removals / Needs rework]
**Stakeholders added**: [N]
**Stakeholders removed**: [N]
**Priorities changed**: [N]

### Next Steps

[If approved]:
Begin Phase 2 — book and run interviews. For each stakeholder:
/wire:stakeholder-interview-generate $ARGUMENTS --stakeholder <slug>

If you haven't run the kick-off yet:
/wire:kickoff-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

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
