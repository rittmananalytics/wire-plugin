---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Full Jira reconciliation — sync all artifact states in one pass
argument-hint: <project-folder>

---

# Jira Full Status Sync Utility

## Purpose

Perform a full reconciliation of all artifact lifecycle states between local `status.md` and Jira. Syncs every in-scope artifact's Sub-tasks, Tasks, and Epic in a single pass. Called by `/wire:status` to ensure Jira stays in sync.

## Usage

```bash
/wire:utils-jira-status-sync YYYYMMDD_project_name
```

Typically invoked automatically by `/wire:status` when Jira is configured.

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

**Read custom state mapping first**: check `jira.state_mapping` in status.md. If present, use the custom labels in place of the defaults below. For example, if `state_mapping.done = "Internal QA Complete"`, substitute that label wherever "Done" appears in the mapping.

For each in-scope artifact, compare local state to expected Jira state:

| Artifact | Step | Local State | Expected Jira | Sub-task Key |
|----------|------|-------------|---------------|--------------|
| requirements | generate | complete | Done | PROJ-125 |
| requirements | validate | pass | Done | PROJ-126 |
| requirements | review | approved | Done | PROJ-127 |
| data_model | generate | complete | Done | PROJ-129 |
| data_model | validate | not_started | To Do | PROJ-130 |
| ... | ... | ... | ... | ... |

Default state-to-Jira mapping (overridden by `state_mapping` if present):
- `complete` / `pass` / `approved` → "Done"
- `fail` / `changes_requested` → "To Do"
- `not_started` → "To Do"
- `pending` → "In Progress"

### Step 3: Execute Sync

For each sub-task that needs transitioning:

1. Get available transitions: `executeRead` with `name: listJiraIssueTransitions` (see `specs/mcp.md`, "Atlassian v2 tool names")
2. If current Jira state differs from expected, transition: `transitionJiraIssue`
3. Track changes made vs already-in-sync

**IMPORTANT: Do NOT call `editJiraIssue` to modify issue descriptions. Descriptions are set at creation time and must never be modified during sync. Do NOT add comments during bulk sync (too noisy). Only transition.**

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
- Never block the `/wire:status` command

**Issue keys missing from status.md:**
- Skip artifacts without Jira keys
- Report: `Note: [artifact] has no Jira keys — run /wire:utils-jira-create to set up tracking`

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
