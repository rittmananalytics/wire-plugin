---
description: Validate requirements completeness
argument-hint: <project-folder>
---

# Validate requirements completeness

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.agent_v2` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.agent_v2/` in specs refers to the `.agent_v2/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Validate requirements specification for completeness and clarity
argument-hint: <project-folder>
---

# Requirements Validation Command

## Purpose

Validate a generated requirements specification against completeness criteria. Checks for required sections, clear acceptance criteria, and feasibility.

## Usage

```bash
/dp:requirements:validate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must exist at `<project>/requirements/requirements_specification.md`

## Workflow

### Step 1: Locate Project & Requirements

**Process**:
1. Parse `$ARGUMENTS` for project identifier
2. Search `.agent_v2/` for matching folder
3. Verify `requirements/requirements_specification.md` exists

**If requirements not found**:
```
Error: No requirements found for project "[folder]"

Run `/dp:requirements:generate [folder]` first to generate requirements.
```

### Step 2: Run Validation Checks

**Validation Checklist**:

| Check | Criteria | Severity |
|-------|----------|----------|
| Executive Summary | Present and non-empty | Critical |
| Functional Requirements | At least 3 requirements with acceptance criteria | Critical |
| Non-Functional Requirements | Performance, security, availability defined | Major |
| Data Sources | All data sources identified with owners | Critical |
| Deliverables | All SOW deliverables documented | Critical |
| Acceptance Criteria | Each deliverable has clear acceptance criteria | Critical |
| Timeline | Milestones with dates | Major |
| Stakeholders | Roles and responsibilities defined | Major |
| Out of Scope | Explicitly documented | Major |
| Assumptions | Dependencies documented | Major |

**Severity Levels**:
- **Critical**: Must pass for validation to succeed
- **Major**: Should pass, will be flagged
- **Info**: Advisory only

### Step 3: Generate Validation Report

**Output Format**:

```
## Requirements Validation: [PROJECT_NAME]

**Status:** PASS | FAIL
**File:** .agent_v2/[folder]/requirements/requirements_specification.md

### Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Executive Summary | ✅ | |
| Functional Requirements | ✅ | 12 requirements defined |
| Non-Functional Requirements | ✅ | |
| Data Sources | ✅ | 3 sources identified |
| Deliverables | ✅ | 5 deliverables (D1-D5) |
| Acceptance Criteria | ✅ | All deliverables have criteria |
| Timeline | ✅ | 2-week timeline with milestones |
| Stakeholders | ✅ | All roles defined |
| Out of Scope | ✅ | Documented |
| Assumptions | ⚠️ | Only 2 assumptions - consider adding more |

### Issues to Address

None - requirements are complete and ready for review.

### Next Steps

1. **Review requirements with stakeholders**: `/dp:requirements:review [folder]`
2. After approval, proceed to design: `/dp:pipeline_design:generate [folder]`
```

**If FAIL**:
```
### Issues to Address

**Critical Issues:**
- [ ] Missing data source owners
- [ ] Deliverable D3 lacks acceptance criteria

**Major Issues:**
- [ ] Performance requirements not quantified
- [ ] No timeline milestones defined

Fix these issues and re-run validation.
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.requirements section:
   ```yaml
   requirements:
     generate: complete
     validate: pass | fail
     review: not_started
     validated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Requirements Not Generated

If requirements file doesn't exist:
```
Error: Requirements not found

Generate requirements first: /dp:requirements:generate [folder]
```

### Partially Complete

If some critical checks fail:
- Set validate status to `fail`
- List all issues
- Suggest fixes
- User must regenerate or manually fix, then re-validate

## Output

This command:
- Validates requirements completeness
- Updates `status.md` with validation results
- Provides actionable feedback if issues found

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
| YYYY-MM-DD HH:MM | /dp:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/dp:*` command that was invoked (e.g., `/dp:requirements:generate`, `/dp:new`, `/dp:dbt:validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/dp:new` created a new project
  - `archived` — `/dp:archive` archived a project
  - `removed` — `/dp:remove` deleted a project
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
| 2026-02-22 14:35 | /dp:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /dp:requirements:generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /dp:requirements:validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /dp:requirements:review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /dp:conceptual_model:generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /dp:conceptual_model:validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /dp:conceptual_model:generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /dp:conceptual_model:validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /dp:conceptual_model:review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /dp:conceptual_model:generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /dp:conceptual_model:validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /dp:conceptual_model:review | approved | Reviewed by John Doe |
```
