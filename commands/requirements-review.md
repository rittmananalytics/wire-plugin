---
description: Record stakeholder review of requirements
argument-hint: <project-folder>
---

# Record stakeholder review of requirements

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
description: Record stakeholder review feedback on requirements specification
argument-hint: <project-folder>
---

# Requirements Review Command

## Purpose

Record stakeholder feedback on the requirements specification. Captures approval or change requests and updates tracking.

## Usage

```bash
/wire:requirements-review YYYYMMDD_project_name
```

## Prerequisites

- Requirements must exist and pass validation
- `requirements.validate` should be `pass`

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `status.md`
2. Check that `requirements.validate == pass`
3. If not pass, warn user

**If validation not pass**:
```
Warning: Requirements have not passed validation yet.

Run `/wire:requirements-validate [folder]` before review.

Proceed anyway? (y/n)
```

### Step 2: Present Requirements for Review

**Output**:
```
## Requirements Review Session

**Project:** [PROJECT_NAME]
**Requirements File:** .wire/[folder]/requirements/requirements_specification.md

### Review Checklist

Please review the requirements and provide feedback:

- [ ] Executive summary accurately describes the project
- [ ] All functional requirements are clear and testable
- [ ] Non-functional requirements are realistic
- [ ] Data sources and owners are correct
- [ ] All SOW deliverables are documented
- [ ] Acceptance criteria are clear and measurable
- [ ] Timeline is achievable
- [ ] Risks and assumptions are complete
- [ ] Nothing important is missing

Take your time to review the full document.
```

### Step 2.5: Retrieve External Context (Optional)

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `requirements`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `requirements`
   - If Atlassian MCP is available, search Confluence for design docs and Jira for issue comments
   - Present any relevant findings
3. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
   - Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context
4. If neither service is available, proceed directly to Step 3

This step enriches the review with context from meeting recordings, Confluence documents, and Jira issue comments.

### Step 3: Gather Feedback

**Use AskUserQuestion**:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Review Status",
    "options": [
      {"label": "Approved", "description": "Requirements are complete and approved"},
      {"label": "Changes requested", "description": "Requirements need revisions"},
      {"label": "Needs discussion", "description": "Schedule workshop to clarify"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4a: If Approved

**Ask for reviewer details**:
```
Who approved the requirements? (Name and role, e.g., "Chris Loveday, Vice Principal")
```

**Output**:
```
## Requirements Approved ✅

**Reviewed by:** [Reviewer Name and Role]
**Date:** [Current Date]

Requirements are locked and ready for design phase.

### Next Steps

1. **Design data pipeline**: `/wire:pipeline_design-generate [folder]`
2. **Design data model**: `/wire:data_model-generate [folder]`
3. **Create mockups**: `/wire:mockups-generate [folder]`
```

**Update status.md**:
```yaml
requirements:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "[Reviewer Name]"
  reviewed_date: 2026-02-13
```

### Step 4b: If Changes Requested

**Ask for specific feedback**:
```
What changes are needed? Please describe the specific revisions required:
```

**Record feedback**:
```
## Requirements Changes Requested 🔄

**Reviewed by:** [Reviewer Name]
**Date:** [Current Date]

### Change Requests:

[User's feedback text]

### Next Steps

1. Update requirements based on feedback
2. Re-validate: `/wire:requirements-validate [folder]`
3. Re-submit for review: `/wire:requirements-review [folder]`
```

**Update status.md**:
```yaml
requirements:
  generate: complete
  validate: pass
  review: changes_requested
  feedback: "[User's feedback]"
  reviewed_date: 2026-02-13
```

### Step 4c: If Needs Discussion

**Output**:
```
## Requirements Need Discussion 💬

A workshop is recommended to clarify requirements.

### Next Steps

1. **Generate workshop materials**: `/wire:workshops-generate [folder]`
2. Conduct workshop with stakeholders
3. Update requirements based on workshop outputs
4. Re-validate and re-review
```

**Update status.md**:
```yaml
requirements:
  generate: complete
  validate: pass
  review: pending
  notes: "Workshop scheduled to clarify requirements"
```

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

### Step 6: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Edge Cases

### Requirements Not Validated

If validation hasn't been run:
```
Warning: Requirements have not been validated.

You should run validation first to catch any issues:
/wire:requirements-validate [folder]

Continue with review anyway? (y/n)
```

### Requirements Already Approved

If requirements already have `review: approved`:
```
Requirements are already approved.

Do you want to:
1. View approval details
2. Re-review (will overwrite previous approval)
3. Cancel
```

## Output

This command:
- Records review feedback in `status.md`
- Updates review status (approved/changes_requested/pending)
- Suggests next steps based on outcome

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
