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
description: Sync a single artifact lifecycle state to Linear
argument-hint: <project-folder> <artifact> <action>

---

# Linear Status Sync Utility

## Purpose

Sync a single artifact's lifecycle state change to Linear. Transitions the corresponding Sub-issue and adds a detailed comment with file names, revision history, reviewer details, and feedback. Called by generate/validate/review commands after they update `status.md` — operates in parallel with `jira_sync.md` when both trackers are configured.

## Usage

```bash
/wire:utils-linear-sync YYYYMMDD_project_name requirements generate
```

Typically invoked automatically by lifecycle commands after updating status.md.

## Prerequisites

- Linear MCP server must be configured (`https://mcp.linear.app/sse`)
- Project must have Linear keys in `status.md` (created by `/wire:utils-linear-create`)

## Workflow

### Step 1: Check Linear Configuration

**Process**:
1. Read the project's `status.md`
2. Check for `linear` section in YAML frontmatter
3. If no `linear` section exists, skip silently (no output, no error)
4. Extract `linear.team_id` and the artifact's issue IDs

### Step 2: Look Up Sub-issue ID

**Process**:
1. Determine the sub-issue ID from `linear.artifacts.[artifact].[action]_id`
   - Example: for `requirements` + `generate`, look up `linear.artifacts.requirements.generate_id`
2. If the ID is null or missing, skip silently

### Step 3: Determine Target State

Map the local status to a Linear workflow state:

| Action | Local State | Target Linear State |
|---|---|---|
| generate | `complete` | `Done` |
| validate | `pass` | `Done` |
| validate | `fail` | `Todo` |
| review | `approved` | `Done` |
| review | `changes_requested` | `Todo` |
| review | `pending` | `In Progress` |

### Step 4: Get Available States

```
list_issue_statuses:
  team: "[linear_team_id]"
```

Find the state name matching the target. Match flexibly:
- `Done` matches: "Done", "Completed", "Resolved", "Closed"
- `Todo` matches: "Todo", "Backlog", "To Do", "Open"
- `In Progress` matches: "In Progress", "In Review", "Active", "Started"

### Step 5: Update Sub-issue State

**IMPORTANT: Only pass `id` and `state`. Do NOT include a `description` field. Issue descriptions are set at creation time and must never be modified by sync operations. All lifecycle progress is recorded as comments (Step 6), never by editing the description.**

```
save_issue:
  id: "[sub_issue_id]"
  state: "[matched_state_name]"
```

### Step 5.5: Discover Generated Files

Before building the comment, identify the files this artifact produced. Check `artifacts.[artifact].generated_files` in status.md. If empty, discover via Glob using the same patterns as `jira_sync.md` Step 5.5.

Update `artifacts.[artifact].generated_files` in status.md with the discovered list.

### Step 5.6: Compute Revision Number

Read `artifacts.[artifact].revision_history` from status.md and count prior generate entries. Same logic as `jira_sync.md` Step 5.6.

### Step 6: Add Comment with Details

```
save_comment:
  issueId: "[sub_issue_id]"
  body: "[comment_text]"
```

Use the same comment templates as `jira_sync.md` Step 6 (Generate complete, Validate pass, Validate fail, Review approved, Review changes_requested). The comment content is identical — only the delivery mechanism differs.

**Artifact display name mapping** (same as `jira_sync.md`):

| Artifact | Display Name |
|---|---|
| requirements | Requirements Specification |
| workshops | Workshops |
| conceptual_model | Conceptual Model |
| pipeline_design | Pipeline Design |
| data_model | Data Model Design |
| mockups | Dashboard Mockups |
| pipeline | Data Pipeline |
| dbt | dbt Models |
| semantic_layer | Semantic Layer |
| dashboards | Dashboards |
| data_quality | Data Quality Tests |
| uat | User Acceptance Testing |
| deployment | Deployment |
| training | Training Materials |
| documentation | Documentation |

### Step 6.5: Record Revision History

Append an entry to `artifacts.[artifact].revision_history` in status.md. Same format and logic as `jira_sync.md` Step 6.5. Revision history is maintained regardless of Linear connectivity.

### Step 7: Check Parent Issue Completion

After updating the Sub-issue, check if all Sub-issues under the parent artifact Issue are now `Done`:

1. Look up `linear.artifacts.[artifact].issue_id`
2. Check all sub-issue states for this artifact (generate, validate, review) from local status.md
3. If all applicable steps are done, update parent Issue to `Done` (state only — do NOT modify the description):

```
save_issue:
  id: "[artifact_issue_id]"
  state: "Done"

save_comment:
  issueId: "[artifact_issue_id]"
  body: "All lifecycle steps complete. Artifact is ready."
```

### Step 8: Check Project Completion

After completing a parent Issue, check if all artifact Issues under the Project are done. If all complete, mark the Linear Project as completed:

```
save_project:
  id: "[linear_project_id]"
  state: "completed"
```

Add a comment to note the completion.

### Step 9: Handle Edge Cases

**Linear MCP not available:**
- Skip the update and comment silently. No output, no error. The lifecycle command continues normally.
- **Still record the revision history entry** in status.md.

**Sub-issue already in target state:**
- Skip the state update. Still add the comment for audit trail.

**State not found:**
- Log a brief note: `Note: Could not find Linear state "[target]" for team [team_id]. Sub-issue state not updated.`
- Continue without failing.

**API error:**
- Log a brief note: `Note: Linear sync failed for [identifier]. Local status updated successfully.`
- Continue without failing.

In all cases, the calling lifecycle command is never blocked by Linear sync issues.

## Output

This utility:
- Updates Linear Sub-issue state to match local artifact state
- Adds detailed comments with file lists, revision numbers, reviewer details, and feedback
- Records each lifecycle event in `artifacts.[artifact].revision_history` in status.md
- Updates `artifacts.[artifact].generated_files` in status.md
- Cascades completion up to parent Issue and Project
- Fails gracefully and silently if Linear is unavailable
- Maintains revision_history even when Linear is unavailable
