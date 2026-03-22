---
description: Sync artifact status to Jira
argument-hint: <project-folder> <artifact> <action>
---

# Sync artifact status to Jira

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.3.0\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"utils-jira-sync\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.3.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Sync a single artifact lifecycle state to Jira
argument-hint: <project-folder> <artifact> <action>
---

# Jira Status Sync Utility

## Purpose

Sync a single artifact's lifecycle state change to Jira. Transitions the corresponding Sub-task and adds a detailed comment with file names, revision history, reviewer details, and feedback. Also records the event in the artifact's `revision_history` in `status.md` for audit trail tracking. Called by generate/validate/review commands after they update `status.md`.

## Usage

```bash
/wire:utils-jira-sync YYYYMMDD_project_name requirements generate
```

Typically invoked automatically by lifecycle commands after updating status.md.

## Prerequisites

- Atlassian MCP server must be configured
- Project must have Jira keys in `status.md` (created by `/wire:utils-jira-create`)

## Workflow

### Step 1: Check Jira Configuration

**Process**:
1. Read the project's `status.md`
2. Check for `jira` section in YAML frontmatter
3. If no `jira` section exists, skip silently (no output, no error)
4. Extract `jira.project_key` and the artifact's issue keys

### Step 2: Look Up Issue Key

**Process**:
1. Determine the sub-task key from `jira.artifacts.[artifact].[action]_key`
   - Example: for `requirements` + `generate`, look up `jira.artifacts.requirements.generate_key`
2. If the key is null or missing, skip silently

### Step 3: Determine Target Transition

Map the local status to a Jira transition:

| Action | Local State | Target Jira Status |
|--------|-------------|-------------------|
| generate | `complete` | "Done" |
| validate | `pass` | "Done" |
| validate | `fail` | "To Do" |
| review | `approved` | "Done" |
| review | `changes_requested` | "To Do" |
| review | `pending` | "In Progress" |

### Step 4: Get Available Transitions

```
getTransitionsForJiraIssue:
  issueKey: "[sub_task_key]"
```

Find the transition ID that matches the target status name. Jira transition names vary by project configuration, so match flexibly:
- "Done" matches: "Done", "Resolved", "Closed", "Complete"
- "To Do" matches: "To Do", "Open", "Reopened", "Backlog"
- "In Progress" matches: "In Progress", "In Development", "Active"

### Step 5: Transition the Sub-task

```
transitionJiraIssue:
  issueKey: "[sub_task_key]"
  transitionId: "[matched_transition_id]"
```

### Step 5.5: Discover Generated Files

Before building the comment, identify the files this artifact produced. This provides concrete detail in the Jira comment.

**Process**:
1. Check `artifacts.[artifact].generated_files` in status.md
2. If the list is populated, use it directly
3. If empty or missing, discover files using Glob based on the artifact type. Use the project's subdirectory within `.wire/[folder]/` as the base path:

| Artifact | Glob Pattern |
|----------|-------------|
| requirements | `requirements/*.md` |
| workshops | `requirements/workshop*.md` |
| conceptual_model | `design/conceptual_model*.md` |
| pipeline_design | `design/pipeline*.md` |
| data_model | `design/data_model*.md` |
| mockups | `design/mockup*.md`, `design/dashboard_mockup*.md` |
| pipeline | `dev/pipeline*.*` |
| dbt | Use `models/**/*.sql` and `models/**/*.yml` in the **repository root** (dbt files live outside the project folder) |
| semantic_layer | Use `*.lkml` files in the repository's LookML project directory |
| dashboards | Use `dashboards/*.lkml` or `dev/dashboard*.md` |
| data_quality | `test/data_quality*.md` |
| uat | `test/uat*.md` |
| deployment | `deploy/*.md` |
| training | `enablement/training*.md` |
| documentation | `enablement/doc*.md`, `enablement/*_guide*.md` |

4. Update `artifacts.[artifact].generated_files` in status.md with the discovered list (so subsequent calls don't need to re-discover)

**For large file lists** (more than 10 files, common with dbt and semantic_layer): group by category in the comment rather than listing individually. For example: "12 files: 4 staging models, 3 integration models, 5 warehouse models" or "8 LookML files: 5 views, 2 explores, 1 dashboard".

### Step 5.6: Compute Revision Number

Determine how many times this artifact has been through the generate cycle, to provide context in the comment.

**Process**:
1. Read `artifacts.[artifact].revision_history` from status.md
2. If the list exists, count entries where `action` is `"generate"` — this is the current revision number
3. If revision_history doesn't exist or is empty, this is revision 1
4. If the current action is `generate` and this is a re-generation (revision_history already has a generate entry), the revision number is previous generate count + 1

**For review comments**: also extract the previous review entries from revision_history to show the feedback trail.

### Step 6: Add Comment with Details

Add a comment to the Sub-task with detailed information about the lifecycle event:

```
addCommentToJiraIssue:
  issueKey: "[sub_task_key]"
  body: "[comment_text]"
```

**Comment templates by action**:

**Generate complete:**
```
**[Artifact Display Name] — Generated**

**Revision**: [N] ([if N>1: "revised after feedback from [previous reviewer name from revision_history]"] / [if N=1: "initial generation"])
**Generated**: [generated_date from status.md]

**Files created:**
[For single-file artifacts:]
- [file path relative to project folder]

[For dbt, include:]
- [models_count] models, [tests_count] tests configured
[Then list files, grouped by layer if >10:]
- Staging: [list or count]
- Integration: [list or count]
- Warehouse: [list or count]
- YAML docs: [list or count]

[For multi-file artifacts with <=10 files, list each:]
- [file path 1]
- [file path 2]
- ...

**Next**: Validate → /wire:[artifact]:validate [folder]
```

**Validate pass:**
```
**[Artifact Display Name] — Validation Passed**

**Validated**: [today's date]
**Revision**: [N]

[For dbt, include test results:]
**Test results**: [tests_passed] passed, [tests_failed] failed

**Checks completed**: All validation checks passed.

**Next**: Submit for review → /wire:[artifact]:review [folder]
```

**Validate fail:**
```
**[Artifact Display Name] — Validation Failed**

**Validated**: [today's date]
**Revision**: [N]

[For dbt, include test results:]
**Test results**: [tests_passed] passed, [tests_failed] failed

**Action**: Fix issues and re-validate.
See validation report in status.md for details.
```

**Review approved:**
```
**[Artifact Display Name] — Approved**

**Reviewer**: [reviewed_by from status.md]
**Date**: [reviewed_date from status.md]
**Revision**: [N]

[If N > 1, include revision summary showing the path to approval:]
**Revision history:**
[For each previous entry in revision_history with action "review":]
- [date]: [result] by [reviewer][if feedback present: " — " + first 150 chars of feedback]

[Example:]
- 2026-02-05: Changes requested by Chris Loveday — "Need to add assignment marks model and cross-reference with ProSolution enrolment data"
- 2026-02-08: Approved by Chris Loveday

This artifact is now locked and ready for downstream phases.
```

**Review changes_requested:**
```
**[Artifact Display Name] — Changes Requested**

**Reviewer**: [reviewed_by from status.md]
**Date**: [reviewed_date from status.md]
**Revision**: [N]

**Feedback:**
> [Full feedback text from artifacts.[artifact].feedback in status.md]

[If N > 1, include previous review context:]
**Previous reviews:**
[For each previous entry in revision_history with action "review":]
- [date]: [result] by [reviewer]

**Action**: Address feedback, revise artifact, re-validate, and re-submit for review.
```

**Artifact display name mapping** (use the same mapping as `jira_create.md`):

| Artifact | Display Name |
|----------|-------------|
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

After writing the Jira comment (whether or not the comment succeeded), append an entry to `artifacts.[artifact].revision_history` in status.md. This maintains an audit trail of all lifecycle events for the artifact.

**Process**:
1. Read the current `artifacts.[artifact].revision_history` list from status.md
2. If the list doesn't exist (older status.md without this field), create it as an empty list
3. Append a new entry based on the action:

**For generate:**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "generate"
  files: [list from generated_files]
```

**For validate:**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "validate"
  result: "[pass|fail]"
```

**For review (approved):**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "review"
  result: "approved"
  reviewer: "[reviewed_by from status.md]"
```

**For review (changes_requested):**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "review"
  result: "changes_requested"
  reviewer: "[reviewed_by from status.md]"
  feedback: "[feedback text from status.md]"
```

4. Write the updated `revision_history` list back to status.md

**Edge case**: If Jira sync failed (MCP unavailable, transition error), still record the revision history entry — the audit trail should be maintained regardless of Jira connectivity.

### Step 7: Check Parent Task Completion

After transitioning the Sub-task, check if all Sub-tasks under the parent Task are now "Done":

1. Look up the artifact's `task_key` from `jira.artifacts.[artifact].task_key`
2. Check all sub-task keys for this artifact (`generate_key`, `validate_key`, `review_key`)
3. Read their current states from `status.md`:
   - generate == `complete`
   - validate == `pass` (or artifact has no validate step)
   - review == `approved`
4. If all applicable steps are done, transition the parent Task to "Done"

```
getTransitionsForJiraIssue:
  issueKey: "[task_key]"

transitionJiraIssue:
  issueKey: "[task_key]"
  transitionId: "[done_transition_id]"

addCommentToJiraIssue:
  issueKey: "[task_key]"
  body: "All lifecycle steps complete. Artifact is ready."
```

### Step 8: Check Epic Completion

After transitioning a Task to "Done", check if all artifact Tasks under the Epic are done:

1. Read all artifact task states from `status.md`
2. For each in-scope artifact, check if all steps are complete
3. If ALL artifacts are fully complete, transition the Epic to "Done"

```
addCommentToJiraIssue:
  issueKey: "[epic_key]"
  body: "All project artifacts complete. Project ready for closure."
```

### Step 9: Handle Edge Cases

**Atlassian MCP not available:**
- Skip the Jira transition and comment silently. No output, no error. The lifecycle command continues normally.
- **Still record the revision history entry** in status.md (Step 6.5) — audit trail is maintained even without Jira.

**Sub-task already in target state:**
- Skip the transition (avoid duplicate transitions)
- Still add the comment for audit trail

**Transition not available:**
- Log a brief note: `Note: Could not transition [key] to [target]. Current Jira status may differ from local status.`
- Continue without failing

**API error:**
- Log a brief note: `Note: Jira sync failed for [key]. Local status updated successfully.`
- Continue without failing

**Missing revision_history field:**
- If `artifacts.[artifact].revision_history` doesn't exist in status.md (older projects created before this field was added), create it as an empty list and append the current entry. This provides forward compatibility with older status files.

**Missing generated_files field:**
- If `artifacts.[artifact].generated_files` doesn't exist, create it using the Glob discovery from Step 5.5. This provides forward compatibility with older status files.

In all cases, the calling lifecycle command is never blocked by Jira sync issues.

## Output

This utility:
- Transitions Jira Sub-tasks to match local artifact state
- Adds detailed comments with file lists, revision numbers, reviewer details, and feedback for audit trail
- Records each lifecycle event in `artifacts.[artifact].revision_history` in status.md
- Updates `artifacts.[artifact].generated_files` in status.md (via Glob discovery if not already populated)
- Cascades completion up to parent Task and Epic
- Fails gracefully and silently if Jira is unavailable
- Maintains revision_history even when Jira is unavailable

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
