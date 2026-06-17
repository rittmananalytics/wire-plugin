---
description: Sync artifact status to Linear
argument-hint: <project-folder> <artifact> <action>
---

# Sync artifact status to Linear

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
