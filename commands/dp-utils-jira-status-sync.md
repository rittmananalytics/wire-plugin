---
description: Full Jira reconciliation for all artifacts
argument-hint: <project-folder>
---

# Full Jira reconciliation for all artifacts

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
description: Full Jira reconciliation — sync all artifact states in one pass
argument-hint: <project-folder>
---

# Jira Full Status Sync Utility

## Purpose

Perform a full reconciliation of all artifact lifecycle states between local `status.md` and Jira. Syncs every in-scope artifact's Sub-tasks, Tasks, and Epic in a single pass. Called by `/dp:status` to ensure Jira stays in sync.

## Usage

```bash
/dp:utils:jira-status-sync YYYYMMDD_project_name
```

Typically invoked automatically by `/dp:status` when Jira is configured.

## Prerequisites

- Atlassian MCP server must be configured
- Project must have Jira keys in `status.md`

## Workflow

### Step 1: Check Jira Configuration

**Process**:
1. Read the project's `status.md`
2. Check for `jira` section in YAML frontmatter
3. If no `jira` section exists, skip entirely (return brief note)
4. Extract all issue keys and current artifact states

### Step 2: Build Sync Plan

For each in-scope artifact, compare local state to expected Jira state:

| Artifact | Step | Local State | Expected Jira | Sub-task Key |
|----------|------|-------------|---------------|--------------|
| requirements | generate | complete | Done | PROJ-125 |
| requirements | validate | pass | Done | PROJ-126 |
| requirements | review | approved | Done | PROJ-127 |
| data_model | generate | complete | Done | PROJ-129 |
| data_model | validate | not_started | To Do | PROJ-130 |
| ... | ... | ... | ... | ... |

Use the same state-to-Jira mapping as `jira_sync.md`:
- `complete` / `pass` / `approved` → "Done"
- `fail` / `changes_requested` → "To Do"
- `not_started` → "To Do"
- `pending` → "In Progress"

### Step 3: Execute Sync

For each sub-task that needs transitioning:

1. Get available transitions: `getTransitionsForJiraIssue`
2. If current Jira state differs from expected, transition: `transitionJiraIssue`
3. Track changes made vs already-in-sync

Do NOT add comments during bulk sync (too noisy). Only transition.

### Step 4: Sync Parent Tasks

For each artifact Task:
1. Check if all sub-tasks are in "Done" state (based on local status)
2. If all done, ensure parent Task is also "Done"
3. If not all done, ensure parent Task is NOT "Done" (reopen if needed)

### Step 5: Sync Epic

1. Check if all artifact Tasks are complete
2. If all complete, transition Epic to "Done"
3. If not all complete, ensure Epic is NOT "Done"

### Step 6: Report Sync Results

**Output**:

```markdown
## Jira Sync Summary

**Epic**: [PROJ-123] — [status]
**Synced**: [count] sub-tasks checked

### Sync Results

| Artifact | Step | Local | Jira Before | Jira After | Action |
|----------|------|-------|-------------|------------|--------|
| requirements | generate | complete | Done | Done | In sync |
| requirements | validate | pass | To Do | Done | Transitioned |
| data_model | generate | complete | Done | Done | In sync |
| data_model | validate | not_started | To Do | To Do | In sync |

**Changes made**: [count] transitions
**Already in sync**: [count]
**Errors**: [count] (if any)
```

### Step 7: Handle Edge Cases

**Atlassian MCP not available:**
```
Note: Jira sync skipped (Atlassian MCP server not configured).
```

**Some transitions fail:**
- Report which transitions failed
- Continue syncing remaining items
- Never block the `/dp:status` command

**Issue keys missing from status.md:**
- Skip artifacts without Jira keys
- Report: `Note: [artifact] has no Jira keys — run /dp:utils:jira-create to set up tracking`

**Jira project archived or issues deleted:**
- Report the error for affected issues
- Continue with remaining issues

## Output

This utility:
- Syncs all artifact states from status.md to Jira in one pass
- Reports a sync summary table
- Does NOT modify status.md
- Fails gracefully if Jira is unavailable
- Designed to be run repeatedly without side effects (idempotent)

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
