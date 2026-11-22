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
description: Full Linear reconciliation — sync all artifact states in one pass
argument-hint: <project-folder>

---

# Linear Full Status Sync Utility

## Purpose

Perform a full reconciliation of all artifact lifecycle states between local `status.md` and Linear. Syncs every in-scope artifact's Sub-issues, Issues, and Project in a single pass. Called by `/wire:status` alongside `jira_status_sync.md` when Linear is configured.

## Usage

```bash
/wire:utils-linear-status-sync YYYYMMDD_project_name
```

Typically invoked automatically by `/wire:status` when Linear is configured.

## Prerequisites

- Linear MCP server must be configured (`https://mcp.linear.app/sse`)
- Project must have Linear keys in `status.md` (created by `/wire:utils-linear-create`)

## Workflow

### Step 1: Check Linear Configuration

**Process**:
1. Read the project's `status.md`
2. Check for `linear` section in YAML frontmatter
3. If no `linear` section exists, skip entirely (return brief note)
4. Extract `linear.team_id`, `linear.project_id`, and all artifact issue IDs and current artifact states

### Step 2: Get Available Workflow States

```
list_issue_statuses:
  team: "[linear_team_id]"
```

Build a map of state names for use throughout the sync. Match flexibly:
- Done: "Done", "Completed", "Resolved", "Closed"
- Todo: "Todo", "Backlog", "To Do", "Open"
- In Progress: "In Progress", "In Review", "Active", "Started"

### Step 3: Build Sync Plan

For each in-scope artifact, compare local state to expected Linear state:

| Artifact | Step | Local State | Expected Linear State | Sub-issue ID |
|---|---|---|---|---|
| requirements | generate | complete | Done | ENG-43 |
| requirements | validate | pass | Done | ENG-44 |
| requirements | review | approved | Done | ENG-45 |
| data_model | generate | complete | Done | ENG-51 |
| data_model | validate | not_started | Todo | ENG-52 |
| ... | ... | ... | ... | ... |

Use the same state mapping as `linear_sync.md`:
- `complete` / `pass` / `approved` → Done
- `fail` / `changes_requested` → Todo
- `not_started` → Todo
- `pending` → In Progress

### Step 4: Execute Sync

For each Sub-issue that needs updating:

**IMPORTANT: Only pass `id` and `state`. Do NOT include a `description` field. Issue descriptions are set at creation time and must never be modified during sync. All lifecycle progress belongs in comments, not the description.**

```
save_issue:
  id: "[sub_issue_id]"
  state: "[target_state_name]"
```

Do NOT add comments during bulk sync (too noisy). Only update state.

Track: changes made vs already-in-sync.

### Step 5: Sync Parent Issues

For each artifact Issue:
1. Check if all its Sub-issues should be `Done` (based on local status)
2. If all done, ensure parent Issue is also `Done`
3. If not all done, ensure parent Issue is NOT `Done` (reopen if needed)

```
save_issue:
  id: "[artifact_issue_id]"
  state: "[done_or_todo_state_name]"
```

Only `id` and `state` — do NOT include `description`.

### Step 6: Sync Project Completion

1. Check if all artifact Issues are complete (all steps done in local status.md)
2. If all complete, mark Linear Project as `completed`:

```
save_project:
  id: "[linear_project_id]"
  state: "completed"
```

3. If not all complete, ensure Project is in `started` state.

### Step 7: Report Sync Results

```markdown
## Linear Sync Results — [project_name]

**Project**: [project_url]
**Team**: [team_id]

### Changes Made

| Artifact | Step | Previous State | New State | Issue |
|---|---|---|---|---|
| requirements | generate | Todo | Done | ENG-43 |
| data_model | validate | In Progress | Done | ENG-52 |

### Already In Sync

- [N] sub-issues already matched local state (no changes)

### Summary

- Updated: [N] sub-issues, [N] parent issues
- In sync: [N] sub-issues
- Errors: [N] (if any — see notes below)
```

### Step 8: Handle Edge Cases

**Linear MCP not available:**
- Skip entirely. Log a brief note: `Note: Linear sync skipped (MCP server not reachable).`
- Continue — never block `/wire:status`.

**Missing sub-issue IDs in status.md:**
- Skip that artifact/step with a note: `Note: No Linear sub-issue ID for [artifact].[step] — skipping.`

**State not found in team workflow:**
- Log a brief note and skip that transition.

**Partial failure:**
- Continue with remaining artifacts. Report all failures at the end.

In all cases, the calling command (`/wire:status`) is never blocked by Linear sync issues.

## Output

This utility:
- Updates all Linear Sub-issue states to match local artifact states in a single pass
- Updates parent Issue and Project completion based on aggregate state
- Reports a summary of changes made vs already-in-sync
- Fails gracefully if Linear is unavailable
- Never blocks `/wire:status` — Linear sync is always additive
