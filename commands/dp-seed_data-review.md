---
description: Record stakeholder review of seed data
argument-hint: <project-folder>
---

# Record stakeholder review of seed data

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
description: Record stakeholder review of seed data
argument-hint: <project-folder>
---

# Seed Data Review Command

## Purpose

Record stakeholder feedback on the generated seed data. Captures approval or change requests and updates tracking. The reviewer should verify the seed data is realistic, domain-appropriate, and sufficient for initial dashboard visualization.

## Usage

```bash
/wire:dp-seed_data-review YYYYMMDD_project_name
```

## Prerequisites

- `seed_data.validate` must be `pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Verify `artifacts.seed_data.validate` is `pass`

If not met:
```
Error: Seed data must pass validation first.

Run: /wire:dp-seed_data-validate <project>
```

### Step 2: Present Review Summary

**Process**:
1. Read `.wire/<project-folder>/dev/seed_data/README.md`
2. Read a sample of the seed CSV files (first 5-10 rows of each)
3. Present a summary:

```
## Seed Data Review

**Files:** [count] CSV seed files
**Total rows:** [count]

### Overview
[Summary from README.md]

### Sample Data Preview
[First few rows from key tables]

### Review Criteria
- Is the data realistic for the [client/domain] context?
- Are the value distributions reasonable?
- Is there enough data variety for meaningful dashboard visualizations?
- Are the entity names and categories domain-appropriate?
```

### Step 3: Collect Review Decision

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the review decision for the seed data?",
    "header": "Review",
    "options": [
      {"label": "Approved", "description": "Seed data is realistic and sufficient for initial development"},
      {"label": "Changes requested", "description": "Seed data needs modifications before proceeding"}
    ],
    "multiSelect": false
  }]
}
```

If "Changes requested", ask in chat:
```
What changes are needed? Please describe the issues with the seed data.
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.seed_data section:

**If approved**:
```yaml
seed_data:
  generate: complete
  validate: pass
  review: approved
  reviewed_date: [today's date]
  reviewer: [reviewer name if provided]
```

**If changes requested**:
```yaml
seed_data:
  generate: complete
  validate: pass
  review: changes_requested
  reviewed_date: [today's date]
  reviewer: [reviewer name if provided]
  review_notes: [summary of requested changes]
```

3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `seed_data`
- Action: `review`
- Status: the review state just written to status.md

### Step 6: Confirm and Suggest Next Steps

**If approved**:
```
## Seed Data Review: Approved

### Next Steps
1. **Generate dbt project**: `/wire:dp-dbt-generate <project>`
   The dbt project will use these seed files as its data source
```

**If changes requested**:
```
## Seed Data Review: Changes Requested

**Feedback:** [summary]

### Next Steps
1. **Regenerate seed data**: `/wire:dp-seed_data-generate <project>`
2. Then re-validate: `/wire:dp-seed_data-validate <project>`
3. Then re-review: `/wire:dp-seed_data-review <project>`
```

## Output

This command updates `status.md` with the review outcome. No files are created.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

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
| YYYY-MM-DD HH:MM | /wire:dp-<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:dp-*` command that was invoked (e.g., `/wire:dp-requirements-generate`, `/wire:dp-new`, `/wire:dp-dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:dp-new` created a new project
  - `archived` — `/wire:dp-archive` archived a project
  - `removed` — `/wire:dp-remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

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
| 2026-02-22 14:35 | /wire:dp-new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:dp-requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:dp-requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:dp-requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:dp-conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:dp-conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:dp-conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:dp-conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:dp-conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:dp-conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:dp-conceptual_model-review | approved | Reviewed by John Doe |
```
