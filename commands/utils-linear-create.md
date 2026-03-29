---
description: Create Linear Project and issues for a project
argument-hint: <project-folder>
---

# Create Linear Project and issues for a project

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.5\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"utils-linear-create\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.5\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Create or link Linear issues for a data platform project
argument-hint: <project-folder>
---

# Linear Issue Creation and Linking Utility

## Purpose

Set up Linear tracking for a data platform project. Supports two modes:

- **Create mode**: Create a new Linear issue hierarchy (Project → Issues → Sub-issues) from scratch
- **Link mode**: Search an existing Linear team for issues that match framework artifacts and link to them

Can be used in three ways:
- **During project creation**: Called automatically from `/wire:new` (Step 9.5) when the user opts in to Linear tracking
- **Mid-project enablement**: Run standalone on an existing project to retroactively add Linear tracking
- **Linking to existing boards**: When a Linear team already has issues, search and link to the most appropriate existing ones

## Usage

```bash
/wire:utils-linear-create YYYYMMDD_project_name
```

When invoked standalone (not from `/wire:new`), prompt the user for the Linear team key and the desired mode (create or link).

## Prerequisites

- Linear MCP server must be configured (`https://mcp.linear.app/sse`)
- Linear team identifier must be provided (e.g., `ENG`, `DATA`, `ACME`)
- Project must exist with a valid `status.md`

## Linear Data Model

Wire Framework maps to Linear as follows:

| Wire concept | Linear equivalent |
|---|---|
| Engagement / project | Linear **Project** (within a Team) |
| Artifact (e.g. requirements) | Linear **Issue** (child of Project) |
| Lifecycle step (generate/validate/review) | Linear **Sub-issue** (child of artifact Issue) |
| Sprint | Linear **Cycle** |

Linear uses parent–child relationships rather than Epic/Task/Sub-task issue types.

## Workflow

### Step 1: Read Project Context

**Process**:
1. Read the project's `status.md`
2. Extract from YAML frontmatter:
   - `project_name`
   - `client_name`
   - `project_type`
   - `artifacts` section (to determine in-scope artifacts)
3. Accept `linear_team_id` from the calling context (provided by user during `/wire:new`), or if running standalone, ask the user:
   ```
   What is the Linear team identifier? (e.g., ENG, DATA, ACME)
   ```

### Step 1.5: Determine Workflow Mode

Three modes are supported:

| `linear_mode` | Meaning |
|---|---|
| `"create"` | Create a new Linear project, then create all issues and sub-issues inside it |
| `"create_in_existing"` | Use an existing Linear project (provided by URL/ID), but create fresh issues and sub-issues inside it |
| `"link"` | Use an existing Linear project and link to pre-existing issues within it |

**If invoked from `/wire:new` with `linear_mode: "link"`**:
- Proceed to **Step 2A** (Search for Existing Issues)

**If invoked from `/wire:new` with `linear_mode: "create_in_existing"`**:
- Proceed to **Step 2** (Resolve Linear Project) — the `create_in_existing` path verifies the supplied `linear_project_id` and sets `resolved_project_id`.

**If invoked from `/wire:new` with `linear_mode: "create"` (or no mode specified)**:
- Proceed to **Step 2** (Create Linear Project)

**If invoked standalone** (not from `/wire:new`):
Ask the user:
```
How would you like to set up Linear tracking?
1. Create new project + new issues — Create a new project, issues, and sub-issues from scratch
2. Use existing project + create new issues — Paste an existing project URL or ID; Wire will create fresh issues inside it
3. Link to existing project + existing issues — Search for and link to issues that already exist in this Linear team
```

---

## Workflow Path A: Create New Issues

### Step 2: Resolve Linear Project

The goal of this step is to populate `resolved_project_id` and `resolved_project_url` — the canonical project reference used by all subsequent steps.

**When `linear_mode` is `"create"`**:

Optionally offer to customise the name:
```
Project name (press Enter to accept default: "[client_name] — [project_name]"):
```

Create the project:
```
save_project:
  name: "[confirmed_project_name]"
  addTeams: ["[linear_team_id]"]
  description: |
    Data platform project for [client_name].
    Project type: [project_type]
    Created: [date]
    Local tracking: .wire/releases/[folder_name]/status.md
  state: "started"
```

Store the returned `id` as `resolved_project_id` and the project URL as `resolved_project_url`.

**When `linear_mode` is `"create_in_existing"` or `"link"`**:

The user has already provided a `linear_project_id` (URL or raw ID). Verify it:
```
list_projects:
  team: "[linear_team_id]"
  query: "[linear_project_id]"
```

If the project is found: store the matching project's `id` as `resolved_project_id` and its URL as `resolved_project_url`.

If not found or inaccessible:
```
Error: Linear project "[linear_project_id]" could not be found or is not accessible.
Please check the project ID/URL and your permissions, then re-run:
/wire:utils-linear-create [folder]
```
Exit — do not proceed without a valid project.

### Step 3: Create Issues for Each In-Scope Artifact

For each artifact where the state is NOT `not_applicable`, create a top-level Issue under the project. Use `resolved_project_id` from Step 2 for all issue creation calls.

**Artifact display names:**

| Artifact | Issue Title | Description |
|---|---|---|
| requirements | Requirements Specification | Extract and validate requirements from SOW |
| workshops | Workshops | Discovery and clarification workshops |
| conceptual_model | Conceptual Model | Entity model and business object relationships |
| pipeline_design | Pipeline Design | Data pipeline architecture and data flow |
| data_model | Data Model Design | dbt model structure (staging/integration/warehouse) |
| mockups | Dashboard Mockups | Dashboard wireframes and UX mockups |
| pipeline | Data Pipeline | Pipeline implementation code |
| dbt | dbt Models | dbt model SQL and configuration |
| semantic_layer | Semantic Layer | LookML views, explores, and measures |
| dashboards | Dashboards | Dashboard implementation |
| data_quality | Data Quality Tests | Data quality validation and testing |
| uat | User Acceptance Testing | UAT plan and execution |
| deployment | Deployment | Production deployment artifacts |
| training | Training Materials | Training sessions and materials |
| documentation | Documentation | Technical and user documentation |

For each in-scope artifact:

```
save_issue:
  team: "[linear_team_id]"
  project: "[resolved_project_id]"
  title: "[Artifact Display Name]: [project_name]"
  description: "[Description from table above]"
```

Record each returned `id` as the artifact's `issue_id` and `identifier` as `issue_identifier` (e.g., `ENG-42`).

### Step 4: Create Sub-issues for Lifecycle Steps

For each artifact Issue, create Sub-issues for the applicable lifecycle steps.

**Lifecycle steps per artifact** (same as Jira — see `jira_create.md` for the full table):
- Most artifacts have: generate, validate, review
- `workshops`, `mockups`, `uat` have: generate, review (no validate)

For each applicable step:

**IMPORTANT: Sub-issues must only have `parentId` — never `project`, never `team`. Passing `project` causes Linear to surface the issue as a standalone project issue rather than a sub-issue. The parent relationship is established solely through `parentId`; team and project are inherited automatically.**

```
save_issue:
  parentId: "[artifact_issue_id]"
  title: "[Step]: [Artifact Display Name]"
  description: "[Step] the [artifact] for [project_name]"
```

Where `[Step]` is `Generate`, `Validate`, or `Review`.

Record each returned `id` as `[step]_id` and `identifier` as `[step]_identifier`.

### Step 4.5: Assign to Cycle (optional)

If the Linear team uses Cycles (equivalent to sprints):

```
linear_getCycles:
  teamId: "[linear_team_id]"
```

If an active Cycle exists, assign all artifact Issues to it:

```
save_issue:
  id: "[artifact_issue_id]"
  cycle: "[active_cycle_id]"
```

If no active Cycle exists, note this to the user — issues will appear in the backlog.

---

## Workflow Path B: Link to Existing Issues

### Step 2A: Search for Existing Issues

Search the Linear team for issues that could map to framework artifacts:

```
list_issues:
  team: "[linear_team_id]"
  filter:
    state: { type: { nin: ["completed", "cancelled"] } }
```

Also search for existing Projects:

```
list_projects:
  team: "[linear_team_id]"
```

### Step 2B: Match Issues to Framework Artifacts

For each in-scope artifact, score existing issues using the same algorithm as `jira_create.md` (keyword matching, display name matching, project/client name matching). Minimum threshold: 5 points.

**Artifact keyword mapping** (same as Jira):

| Artifact | Display Name | Match Keywords |
|---|---|---|
| requirements | Requirements Specification | "requirements", "scope", "SOW" |
| workshops | Workshops | "workshop", "discovery", "kickoff" |
| conceptual_model | Conceptual Model | "entities", "conceptual", "ERD" |
| pipeline_design | Pipeline Design | "pipeline", "architecture", "data flow" |
| data_model | Data Model Design | "dbt", "staging", "warehouse", "data model" |
| mockups | Dashboard Mockups | "mockup", "wireframe", "dashboard design" |
| pipeline | Data Pipeline | "pipeline", "extraction", "ingestion" |
| dbt | dbt Models | "dbt", "models", "transformations" |
| semantic_layer | Semantic Layer | "LookML", "semantic", "metrics", "measures" |
| dashboards | Dashboards | "dashboard", "report", "visualization" |
| data_quality | Data Quality Tests | "data quality", "testing", "dbt test" |
| uat | User Acceptance Testing | "UAT", "user acceptance", "sign-off" |
| deployment | Deployment | "deployment", "go-live", "production" |
| training | Training Materials | "training", "enablement", "onboarding" |
| documentation | Documentation | "documentation", "runbook", "handover" |

**Project matching**: If a Linear Project's name contains the client name or project name, match it as the engagement Project. Present multiple candidates to the user if ambiguous.

**Sub-issue matching**: For each matched Issue, retrieve its children:

```
list_issues:
  filter:
    parent: { id: { eq: "[issue_id]" } }
```

Match Sub-issues to lifecycle steps by keyword in the title:
- **generate**: "Generate", "Create", "Build", "Develop", "Write"
- **validate**: "Validate", "Test", "Check", "Verify", "QA"
- **review**: "Review", "Approve", "Sign-off", "Accept"

### Step 2C: Present Matches for User Confirmation

Display the proposed mapping, then ask:
```
1. Accept all matches — Link matched issues, create new for anything unmatched
2. Accept matches only — Link matched, skip unmatched (no new issues)
3. Let me adjust — Walk through each artifact manually
4. Cancel
```

### Step 2D: Execute Linking

Same logic as `jira_create.md` Step 2D: create new issues for unmatched artifacts, link matched, handle partial matches.

### Step 2E: Add Linking Comments

For each linked Issue, add a comment:

```
save_comment:
  issueId: "[issue_id]"
  body: |
    Linked to Wire Framework project: [project_name]
    Client: [client_name] | Type: [project_type]
    Local tracking: .wire/releases/[folder_name]/status.md

    This issue is now tracked by the Wire Framework.
    Status updates will be synced automatically.
```

---

## Common Steps (Both Paths)

### Step 5: Update status.md with Linear Keys

Update the project's `status.md` YAML frontmatter with all created/linked issue identifiers:

```yaml
linear:
  team_id: "ENG"
  project_id: "[resolved_project_id]"
  project_url: "[resolved_project_url]"
  artifacts:
    requirements:
      issue_id: "ISSUE_UUID"
      issue_identifier: "ENG-42"
      generate_id: "SUBISSUE_UUID"
      generate_identifier: "ENG-43"
      validate_id: "SUBISSUE_UUID"
      validate_identifier: "ENG-44"
      review_id: "SUBISSUE_UUID"
      review_identifier: "ENG-45"
    data_model:
      issue_id: "ISSUE_UUID"
      issue_identifier: "ENG-50"
      # ...
```

For out-of-scope artifacts, omit them from the `linear.artifacts` section entirely.

### Step 5.5: Sync Existing Progress (Mid-Project Only)

If this utility is running on a project that already has progress, call `specs/utils/linear_status_sync.md` to transition all Sub-issues to match the current local artifact states.

### Step 6: Report Results

```markdown
## Linear Issues Created

**Project**: [client_name] — [project_name]
**URL**: [project_url]
**Issues**: [count] artifact issues
**Sub-issues**: [count] lifecycle step sub-issues

### Issue Hierarchy

| Artifact | Issue | Generate | Validate | Review |
|---|---|---|---|---|
| Requirements | ENG-42 | ENG-43 | ENG-44 | ENG-45 |
| Data Model | ENG-50 | ENG-51 | ENG-52 | ENG-53 |
| ... | ... | ... | ... | ... |

All issue identifiers have been recorded in status.md.
```

### Step 7: Handle Edge Cases

**Linear MCP not available:**
```
Note: Could not connect to Linear (Linear MCP server not configured).
Skipping Linear issue creation. You can create issues later by running:
/wire:utils-linear-create [folder]
```

**Linear already configured:**
If `status.md` already has a `linear.project_id`:
```
Linear tracking is already configured for this project.

Project: [project_name] ([project_url])

Do you want to:
1. Keep existing Linear tracking (no changes)
2. Replace with new Linear issues (create from scratch)
3. Re-link to different existing issues (search again)
```

In all cases, project creation continues — Linear tracking is optional and additive.

## Output

This utility:
- **Create mode**: Creates a Linear Project + Issues + Sub-issues for the engagement
- **Link mode**: Searches existing Linear issues, matches to framework artifacts, links to them (creating only what's missing)
- Updates `status.md` with all issue identifiers (same structure regardless of mode)
- If run mid-project, syncs existing artifact progress to linked/created issues
- Fails gracefully if Linear is unavailable

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
