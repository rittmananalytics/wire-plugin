---
description: Sponsor review of the delivery roadmap and Release 1 scope
argument-hint: <release-folder>
---

# Sponsor review of the delivery roadmap and Release 1 scope

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
description: Sponsor review of the delivery roadmap and Release 1 scope
---

# Delivery Roadmap — Review

## Purpose

Sponsor sign-off on the delivery roadmap. This is the second sponsor-facing review in a SOP discovery release (after the playback). Its job is to confirm Release 1 scope and the chosen delivery option so that `/wire:release-spawn` can chain into Release 1 with confidence.

If the roadmap was bundled into the playback (inline-roadmap pattern), this review is often a 15-minute confirmatory session. If deferred (deferred-roadmap pattern), this is a full sponsor meeting with its own Fathom recording.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md`
- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap_validation.md`
- `.wire/releases/$ARGUMENTS/playback/playback_meeting_notes.md`

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read inputs. Confirm validation has passed.

### Step 2: Pull meeting context

If a Fathom recording exists for the roadmap session, fetch it via the Fathom MCP and extract:
- Sponsor's verbal confirmation of preferred Delivery Option
- Any scope changes (additions to or removals from Release 1)
- Named follow-up actions

### Step 3: Present for review

Output:
1. The chosen Delivery Option
2. The Release 1 row count and breakdown
3. The named team + go-live date
4. Any FAILs/WARNINGs from validation

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the delivery roadmap review with the sponsor?",
    "header": "Delivery Roadmap Review",
    "options": [
      {"label": "Approved — Release 1 ready to spawn", "description": "Sponsor confirmed scope, option, and go-live"},
      {"label": "Approved with scope changes", "description": "Sponsor moved items in/out of Release 1; capture and update the matrix"},
      {"label": "Delivery option changed", "description": "Sponsor changed their mind on Build/Pair/Coach; capture the new option"},
      {"label": "Needs rework", "description": "Sponsor wants substantive changes — regenerate the roadmap"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture changes

Ask:
```
Record any specific changes from the sponsor (scope, option, dates, team):
```

Apply changes:
- **Scope moves**: edit the `Phase` column for affected rows in `requirements_matrix.md`. Re-run breakdown computation if the count changed materially.
- **Option change**: update `sponsor_validation.preferred_delivery_option` and update the roadmap headline.
- **Date/team changes**: update the Release 1 plan summary directly.

### Step 5: Update status

```yaml
artifacts:
  delivery_roadmap:
    review: complete    # or "pending_rework"

sponsor_validation:
  preferred_delivery_option: "<confirmed option>"
```

### Step 6: Output review summary

```
## Delivery Roadmap Review Complete

**Outcome**: [Approved / Approved with scope changes / Option changed / Needs rework]
**Delivery Option (confirmed)**: <Build / Pair / Coach>
**Release 1 size**: <N> rows
**Go-live**: <date>

### Next Steps

[If approved]:
Spawn Release 1 from this discovery:
/wire:release-spawn $ARGUMENTS

This will:
- Create `.wire/releases/02-<release-name>/` (next sequence number)
- Seed the new release's status.md with the chosen release_type (matching the delivery option)
- Pre-populate the Jira/Linear epic from the requirements_matrix Phase 1 rows
- Link back to this discovery release

[If rework]:
/wire:delivery-roadmap-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

### Step 8: Discovery release approval

Once `delivery_roadmap.review: complete` AND the Sponsor Validation Checklist on `findings_playback` is all-true, the discovery release is **approved end-to-end**. `/wire:status` will show this release as `approved` and `/wire:release-spawn` can chain forward.

If the sponsor outcome from the playback was **no-go** (every checklist item true except Solution Initiatives confirmed: false, or sponsor explicitly chose to not proceed), the discovery release is still **approved** as a discovery — the deliverable was the go/no-go decision. Record `status.md → go_no_go_decision: no_go` and do not spawn a delivery release.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md` (if changes captured)
- Updated `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (if scope moved)
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
