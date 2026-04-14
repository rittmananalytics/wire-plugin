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

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.8\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"requirements-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.8\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

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
/wire:requirements-validate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must exist at `<project>/requirements/requirements_specification.md`

## Workflow

### Step 1: Locate Project & Requirements

**Process**:
1. Parse `$ARGUMENTS` for project identifier
2. Search `.wire/` for matching folder
3. Verify `requirements/requirements_specification.md` exists

**If requirements not found**:
```
Error: No requirements found for project "[folder]"

Run `/wire:requirements-generate [folder]` first to generate requirements.
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
**File:** .wire/[folder]/requirements/requirements_specification.md

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

1. **Review requirements with stakeholders**: `/wire:requirements-review [folder]`
2. After approval, proceed to design: `/wire:pipeline_design-generate [folder]`
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

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Requirements Not Generated

If requirements file doesn't exist:
```
Error: Requirements not found

Generate requirements first: /wire:requirements-generate [folder]
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
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
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
