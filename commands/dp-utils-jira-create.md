---
description: Create Jira Epic and issues for a project
argument-hint: <project-folder>
---

# Create Jira Epic and issues for a project

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
description: Create or link Jira issues for a data platform project
argument-hint: <project-folder>
---

# Jira Issue Creation and Linking Utility

## Purpose

Set up Jira tracking for a data platform project. Supports two modes:

- **Create mode**: Create a new Jira issue hierarchy (Epic → Tasks → Sub-tasks) from scratch
- **Link mode**: Search an existing Jira project for issues that match framework artifacts and link to them instead of creating duplicates

Can be used in three ways:
- **During project creation**: Called automatically from `/wire:dp-new` (Step 9.5) when the user opts in to Jira tracking
- **Mid-project enablement**: Run standalone on an existing project to retroactively add Jira tracking at any point
- **Linking to existing boards**: When a Jira project already has issues (e.g. in a running sprint), search and link to the most appropriate existing issues

## Usage

```bash
/wire:dp-utils-jira-create YYYYMMDD_project_name
```

When invoked standalone (not from `/wire:dp-new`), prompt the user for the Jira project key and the desired mode (create or link).

## Prerequisites

- Atlassian MCP server must be configured
- Jira project key must be provided
- Project must exist with a valid `status.md`

## Workflow

### Step 1: Read Project Context

**Process**:
1. Read the project's `status.md`
2. Extract from YAML frontmatter:
   - `project_name`
   - `client_name`
   - `project_type`
   - `artifacts` section (to determine in-scope artifacts)
3. Accept `jira_project_key` from the calling context (provided by user during `/wire:dp-new`), or if running standalone, ask the user directly:
   ```
   What is the Jira project key? (e.g., DP, ACME, PROJ)
   ```

### Step 1.5: Determine Workflow Mode

**If invoked from `/wire:dp-new` with `jira_mode: "link"`**:
- Proceed to **Step 2A** (Search for Existing Issues)

**If invoked from `/wire:dp-new` with `jira_mode: "create"` (or no mode specified)**:
- Proceed to **Step 2** (Create Epic) — existing creation workflow

**If invoked standalone** (not from `/wire:dp-new`):
- After getting the Jira project key in Step 1, use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "How would you like to set up Jira tracking?",
    "header": "Jira Mode",
    "options": [
      {"label": "Create new issues", "description": "Create Epic, Tasks, and Sub-tasks from scratch"},
      {"label": "Link to existing issues", "description": "Search for and link to existing issues in this Jira project"}
    ],
    "multiSelect": false
  }]
}
```

- If "Create new issues": proceed to **Step 2**
- If "Link to existing issues": proceed to **Step 2A**

---

## Workflow Path A: Create New Issues (Existing)

### Step 2: Create Epic

Create the top-level Epic for the project:

```
createJiraIssue:
  projectKey: "[jira_project_key]"
  issueType: "Epic"
  summary: "[client_name] - [project_name] Data Platform"
  description: |
    Data Platform project for [client_name].

    **Project Type**: [project_type]
    **Created**: [date]

    ## Artifacts in Scope
    [List of in-scope artifacts]

    ## Tracking
    Local status: .wire/[folder_name]/status.md
```

Record the returned Epic key (e.g., `PROJ-123`).

### Step 3: Create Tasks for Each In-Scope Artifact

For each artifact where the state is NOT `not_applicable`, create a Task under the Epic.

**Artifact display names and descriptions**:

| Artifact | Task Summary | Description |
|----------|-------------|-------------|
| requirements | Requirements Specification | Extract and validate requirements from SOW |
| workshops | Workshops | Discovery and clarification workshops |
| conceptual_model | Conceptual Model | Entity model and business object relationships |
| pipeline_design | Pipeline Design | Data pipeline architecture and data flow diagram |
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
createJiraIssue:
  projectKey: "[jira_project_key]"
  issueType: "Task"
  summary: "[Artifact Display Name]: [project_name]"
  description: "[Description from table above]"
  parentKey: "[epic_key]"
```

Record each returned Task key.

### Step 4: Create Sub-tasks for Lifecycle Steps

For each Task, create Sub-tasks for the applicable lifecycle steps. Not all artifacts have all three steps (e.g., workshops and mockups have no validate step).

**Lifecycle steps per artifact**:

| Artifact | Generate | Validate | Review |
|----------|----------|----------|--------|
| requirements | yes | yes | yes |
| workshops | yes | no | yes |
| conceptual_model | yes | yes | yes |
| pipeline_design | yes | yes | yes |
| data_model | yes | yes | yes |
| mockups | yes | no | yes |
| pipeline | yes | yes | yes |
| dbt | yes | yes | yes |
| semantic_layer | yes | yes | yes |
| dashboards | yes | yes | yes |
| data_quality | yes | yes | yes |
| uat | yes | no | yes |
| deployment | yes | yes | yes |
| training | yes | yes | yes |
| documentation | yes | yes | yes |

For each applicable step:

```
createJiraIssue:
  projectKey: "[jira_project_key]"
  issueType: "Sub-task"
  summary: "[Step]: [Artifact Display Name]"
  description: "[Step] the [artifact] for [project_name]"
  parentKey: "[task_key]"
```

Example Sub-tasks for Requirements:
- `Generate: Requirements Specification`
- `Validate: Requirements Specification`
- `Review: Requirements Specification`

Record each returned Sub-task key.

---

## Workflow Path B: Link to Existing Issues

### Step 2A: Search for Existing Issues

Search the Jira project for issues that could map to framework artifacts. Use `searchJiraIssuesUsingJql` with a tiered strategy:

**Query 1 — Epics in the project:**
```
searchJiraIssuesUsingJql:
  jql: "project = [jira_project_key] AND issuetype = Epic ORDER BY created DESC"
  maxResults: 20
```

**Query 2 — Tasks/Stories in active sprint:**
```
searchJiraIssuesUsingJql:
  jql: "project = [jira_project_key] AND issuetype in (Task, Story) AND sprint in openSprints() ORDER BY created DESC"
  maxResults: 50
```

**Query 3 — Fallback: all open Tasks/Stories (if Query 2 returns no results or project doesn't use sprints):**
```
searchJiraIssuesUsingJql:
  jql: "project = [jira_project_key] AND issuetype in (Task, Story) AND status != Done ORDER BY created DESC"
  maxResults: 50
```

If Query 2 returns results, use those (sprint-scoped). If not, use Query 3 (all open issues). This handles Scrum, Kanban, and no-sprint projects.

Note to user if falling back:
```
No active sprint found in [KEY]. Searching all open issues.
```

### Step 2B: Match Issues to Framework Artifacts

For each in-scope artifact, find the best matching Jira issue from the search results using a scored matching algorithm.

**Scoring rules:**

| Signal | Score | Description |
|--------|-------|-------------|
| Summary contains artifact display name | +10 | e.g., "Requirements Specification" in issue summary |
| Summary contains artifact keyword | +5 | e.g., "requirements", "dbt", "pipeline" |
| Summary contains project name or client name | +3 | Indicates project relevance |
| Description contains artifact keywords | +2 | Weaker signal from description text |
| Issue type matches expected (Task for artifacts) | +2 | Type alignment |
| Issue is in active sprint | +1 | Recency/relevance bonus |

**Minimum threshold**: 5 points. Issues scoring below 5 are not considered matches.

**Assignment**: Process artifacts in descending order of their best match score. Each Jira issue can only be matched to one artifact (no double-matching). If two artifacts would match the same issue, the higher-scoring match wins and the lower-scoring artifact tries its next-best candidate.

**Artifact keyword mapping:**

| Artifact | Display Name | Match Keywords |
|----------|-------------|----------------|
| requirements | Requirements Specification | "requirements", "scope", "SOW", "deliverables" |
| workshops | Workshops | "workshop", "discovery", "kickoff" |
| conceptual_model | Conceptual Model | "entities", "conceptual", "ERD" |
| pipeline_design | Pipeline Design | "pipeline", "architecture", "data flow" |
| data_model | Data Model Design | "dbt", "staging", "warehouse", "data model" |
| mockups | Dashboard Mockups | "mockup", "wireframe", "dashboard design" |
| pipeline | Data Pipeline | "pipeline", "extraction", "data pipeline" |
| dbt | dbt Models | "dbt", "models", "transformations" |
| semantic_layer | Semantic Layer | "LookML", "semantic", "metrics", "measures" |
| dashboards | Dashboards | "dashboard", "report", "visualization" |
| data_quality | Data Quality Tests | "data quality", "testing", "dbt test" |
| uat | User Acceptance Testing | "UAT", "user acceptance", "sign-off" |
| deployment | Deployment | "deployment", "go-live", "production" |
| training | Training Materials | "training", "enablement", "onboarding" |
| documentation | Documentation | "documentation", "runbook", "handover" |

**Epic matching:**
- If an Epic's summary contains the client name or project name, match it as the project Epic
- If multiple Epics match, present them to the user for selection
- If no Epic matches, mark as "no Epic match" — `epic_key` will be null in status.md

**Sub-task matching** — For each matched Task, retrieve its Sub-tasks:
```
searchJiraIssuesUsingJql:
  jql: "parent = [task_key] AND issuetype = Sub-task ORDER BY created ASC"
  maxResults: 20
```

Match Sub-tasks to lifecycle steps using keyword detection in the Sub-task summary:
- **generate_key**: Summary contains "Generate", "Create", "Build", "Develop", or "Write"
- **validate_key**: Summary contains "Validate", "Test", "Check", "Verify", or "QA"
- **review_key**: Summary contains "Review", "Approve", "Sign-off", or "Accept"

If Sub-task names don't contain recognisable keywords, present them to the user:
```
Sub-tasks found under [PROJ-45] "[Task summary]":
1. [PROJ-46] "Write initial draft" — Map to: Generate? Validate? Review? Skip?
2. [PROJ-47] "QA check" — Map to: Generate? Validate? Review? Skip?
```

**Classify each artifact:**
- **Matched**: Task found (score >= 5) and at least one Sub-task mapped
- **Partial match**: Task found but no or incomplete Sub-task matches
- **No match**: No candidate Task scored above the threshold

### Step 2C: Present Matches for User Confirmation

Display the proposed mapping to the user:

```markdown
## Proposed Jira Issue Mapping

**Epic**: [PROJ-123] "[Epic summary]" → Project Epic
  (or: "No matching Epic found — epic_key will be left empty")

### Artifact Mapping

| Artifact | Jira Issue | Score | Sub-tasks Found | Status |
|----------|-----------|-------|-----------------|--------|
| Requirements | PROJ-45 "Requirements Doc" | 15 | Gen: PROJ-46, Val: PROJ-47, Rev: PROJ-48 | Matched |
| dbt Models | PROJ-50 "dbt Development" | 12 | Gen: PROJ-51, Val: PROJ-52 | Partial (missing Review) |
| Dashboards | PROJ-55 "Build Dashboards" | 8 | — | Partial (no sub-tasks) |
| Data Quality | — | — | — | No match |

### Summary
- **Matched**: [count] artifacts fully matched
- **Partial**: [count] artifacts partially matched
- **Unmatched**: [count] artifacts with no match
```

Then ask the user for confirmation using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "How would you like to proceed with this mapping?",
    "header": "Confirm Linking",
    "options": [
      {"label": "Accept all matches", "description": "Link matched issues and create new issues for anything unmatched or missing"},
      {"label": "Accept matches only", "description": "Link matched issues, skip unmatched artifacts (no new issues created)"},
      {"label": "Let me adjust", "description": "Walk through each artifact and specify which issue to link"},
      {"label": "Cancel", "description": "Don't set up Jira tracking"}
    ],
    "multiSelect": false
  }]
}
```

### Step 2D: Execute Linking

Based on the user's response:

**"Accept all matches":**
1. Record all matched issue keys (Epic, Tasks, Sub-tasks) for status.md
2. For **unmatched artifacts**: create new Tasks and Sub-tasks under the matched Epic (using the same creation logic from Steps 3 and 4). If no Epic was matched, create a new Epic first (using Step 2).
3. For **partial matches** (Task matched but some Sub-tasks missing): create only the missing Sub-tasks under the matched Task

**"Accept matches only":**
1. Record all matched issue keys for status.md
2. Leave unmatched artifacts with null keys in status.md (they can be linked or created later by re-running this utility)
3. For partial matches, record what was found and leave missing Sub-task keys as null

**"Let me adjust":**
For each in-scope artifact, ask the user directly in chat:
```
For [Artifact Display Name]:
- Suggested match: [PROJ-45] "[Summary]" (score: 15)
- Type a different issue key (e.g., PROJ-99) to link to that issue instead
- Type "skip" to leave unlinked
- Type "create" to create a new issue
```
For any manually specified issue key, fetch it with `getJiraIssue` to verify it exists and retrieve its Sub-tasks. Then apply Sub-task matching as in Step 2B.

**"Cancel":**
- Skip Jira integration entirely
- Continue to Step 10 of `/wire:dp-new` (or exit if standalone)

### Step 2E: Add Linking Comments

For each **linked** issue (not newly created ones — those are handled by the creation path), add a comment to provide an audit trail in Jira:

**Comment on linked Epic:**
```
addCommentToJiraIssue:
  issueKey: "[epic_key]"
  body: |
    Linked to Wire Framework project: [project_name]
    Client: [client_name] | Type: [project_type]
    Local tracking: .wire/[folder_name]/status.md

    This Epic is now being tracked by the Wire Framework.
    Status updates will be synced automatically.
```

**Comment on each linked Task:**
```
addCommentToJiraIssue:
  issueKey: "[task_key]"
  body: |
    Linked to Wire Framework artifact: [Artifact Display Name]
    Project: [project_name]

    This task is now tracked by the Wire Framework.
    Sub-task transitions will be synced automatically.
```

Skip comments on newly created issues (they already have descriptions from the creation step).

### Step 2F: Proceed to Common Steps

After the linking workflow completes, proceed to:
- **Step 5** (Update status.md with Jira Keys) — same YAML structure as creation mode
- **Step 5.5** (Sync Existing Progress) — transitions linked issues to match current artifact states
- **Step 6** (Report Results) — uses the linking report format (see below)

**Linking report format** (used instead of the creation report when issues were linked):

```markdown
## Jira Issues Linked

**Epic**: [PROJ-123] "[Epic summary]"
**Linked**: [count] artifact tasks (from existing issues)
**Created**: [count] artifact tasks (new issues for unmatched artifacts)
**Sub-tasks linked**: [count]
**Sub-tasks created**: [count]

### Issue Hierarchy

| Artifact | Task | Source | Generate | Validate | Review |
|----------|------|--------|----------|----------|--------|
| Requirements | PROJ-45 | Linked | PROJ-46 (L) | PROJ-47 (L) | PROJ-48 (L) |
| dbt Models | PROJ-50 | Linked | PROJ-51 (L) | PROJ-52 (L) | PROJ-60 (C) |
| Data Quality | PROJ-61 | Created | PROJ-62 (C) | PROJ-63 (C) | PROJ-64 (C) |

**(L) = Linked to existing issue, (C) = Created new issue**

All issue keys have been recorded in status.md.
```

---

## Common Steps (Both Paths)

### Step 5: Update status.md with Jira Keys

Update the project's `status.md` YAML frontmatter with all created issue keys:

```yaml
jira:
  project_key: "PROJ"
  epic_key: "PROJ-123"
  artifacts:
    requirements:
      task_key: "PROJ-124"
      generate_key: "PROJ-125"
      validate_key: "PROJ-126"
      review_key: "PROJ-127"
    data_model:
      task_key: "PROJ-128"
      generate_key: "PROJ-129"
      validate_key: "PROJ-130"
      review_key: "PROJ-131"
    # ... (all in-scope artifacts)
```

For out-of-scope artifacts, omit them from the jira.artifacts section entirely.

### Step 5.5: Sync Existing Progress (Mid-Project Only)

If this utility is running on a project that already has progress (i.e., some artifacts have `generate: complete`, `validate: pass`, or `review: approved`):

1. After writing Jira keys to status.md, call the full reconciliation workflow in `dp/utils/jira_status_sync.md`
2. This transitions all Sub-tasks to match the existing local artifact states
3. For example, if requirements are already generated and validated, the `Generate: Requirements` and `Validate: Requirements` Sub-tasks will be transitioned to "Done"

This ensures the Jira board immediately reflects the project's actual state rather than showing all Sub-tasks as "To Do".

### Step 6: Report Results

**Output**:

```markdown
## Jira Issues Created

**Epic**: [PROJ-123] [client_name] - [project_name] Data Platform
**Tasks**: [count] artifact tasks
**Sub-tasks**: [count] lifecycle step sub-tasks

### Issue Hierarchy

| Artifact | Task | Generate | Validate | Review |
|----------|------|----------|----------|--------|
| Requirements | PROJ-124 | PROJ-125 | PROJ-126 | PROJ-127 |
| Data Model | PROJ-128 | PROJ-129 | PROJ-130 | PROJ-131 |
| ... | ... | ... | ... | ... |

All issue keys have been recorded in status.md.
```

### Step 7: Handle Edge Cases

**Atlassian MCP not available:**
```
Note: Could not connect to Jira (Atlassian MCP server not configured).
Skipping Jira issue creation. You can create issues later by running:
/wire:dp-utils-jira-create [folder]
```

**Epic creation fails:**
```
Error: Failed to create Jira Epic. Check that:
- Project key "[key]" exists in Jira
- You have permission to create issues
- The Epic issue type is available in this project

Skipping Jira issue creation. Project created without Jira tracking.
```

**Partial creation failure:**
If some Tasks or Sub-tasks fail to create:
1. Record successfully created issue keys in status.md
2. Report which issues failed
3. Suggest manual creation or retry

**Jira already configured:**
If `status.md` already has a `jira.epic_key`:
```
Jira tracking is already configured for this project.

Epic: [PROJ-123] - [project_name]

Do you want to:
1. Keep existing Jira tracking (no changes)
2. Replace with new Jira issues (create from scratch)
3. Re-link to different existing issues (search again)
```

**Linking-specific edge cases:**

**No issues found in project:**
```
No existing issues found in Jira project [KEY].

Would you like to create new issues instead?
```
If yes, switch to the creation workflow (Step 2 onwards).

**No active sprint:**
- Fall back to searching all non-Done issues (Query 3)
- Note: "No active sprint found. Searching all open issues."

**Ambiguous matches (multiple issues score equally for one artifact):**
Present the top 2-3 candidates to the user:
```
Multiple possible matches for [Artifact]:
1. [PROJ-45] "Requirements Document" (score: 12)
2. [PROJ-50] "Project Requirements" (score: 12)
3. None of these — create new

Which one?
```

**Issues already in "Done" state:**
- Matched issues in "Done" status are still linkable
- Show the current Jira status in the confirmation table so the user can decide
- The `jira_status_sync.md` workflow handles state mapping correctly regardless of current issue state

**Jira uses "Story" instead of "Task":**
- The JQL queries search both: `issuetype in (Task, Story)`
- Stories are treated as Task equivalents for matching purposes

In all cases, project creation continues — Jira tracking is optional and additive.

## Output

This utility:
- **Create mode**: Creates Jira Epic + Tasks + Sub-tasks for the project
- **Link mode**: Searches existing Jira issues, matches them to framework artifacts, and links to them (creating only what's missing)
- Updates `status.md` with all issue keys (same format regardless of mode)
- If run mid-project, syncs existing artifact progress to linked/created issues
- Reports the issue hierarchy with linked vs created indicators
- Fails gracefully if Jira is unavailable
- Can be run at any point in the project lifecycle

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
