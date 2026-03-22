---
description: Create a new data platform project with interactive setup
argument-hint: (no arguments - interactive)
---

# Create a new data platform project with interactive setup

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
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"new\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.3.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Create a new data platform project with interactive setup
---

# DP New Project Command

## Purpose

Interactive workflow to create a new data platform project. Handles folder creation, status file setup, and artifact scope determination based on SOW deliverables.

## Project Types

| Type | Description | Typical Artifacts |
|------|-------------|------------------|
| `full_platform` | Complete data platform (pipelines + dbt + BI + enablement) | All artifacts |
| `pipeline_only` | Data pipeline development only | pipeline_design, pipeline, data_quality, deployment |
| `dbt_development` | dbt models and semantic layer | data_model, dbt, semantic_layer, data_quality |
| `dashboard_extension` | Extends existing platform with new dashboards | requirements, mockups, dashboards, training |
| `dashboard_first` | Interactive mocks drive data model, dbt with seed data first | mockups, viz_catalog, data_model, seed_data, dbt, semantic_layer, dashboards, data_refactor |
| `enablement` | Training and documentation only | training, documentation |

## Workflow

### Step 1: Determine Project ID from Date

**Process**:
1. Use today's date formatted as `YYYYMMDD` (e.g., `20260210`) as the `project_id`
2. Use Glob to check if a folder with this date prefix already exists: `.wire/[0-9]*_*/`
3. If a folder starting with the same `YYYYMMDD_` prefix already exists, append a letter suffix: `20260210a_`, `20260210b_`, etc.
4. `project_id` = the date string (e.g., `20260210`)

### Step 2: Ask for Project Type

Use `AskUserQuestion` to determine the project type:

```json
{
  "questions": [{
    "question": "What type of data platform project is this?",
    "header": "Project Type",
    "options": [
      {"label": "Full platform", "description": "Complete implementation (pipelines, dbt, BI, enablement)"},
      {"label": "Pipeline only", "description": "Data pipeline development"},
      {"label": "dbt development", "description": "dbt models and semantic layer"},
      {"label": "Dashboard extension", "description": "New dashboards on existing platform"},
      {"label": "Dashboard-first rapid dev", "description": "Interactive mocks drive data model, dbt with seed data first"},
      {"label": "Enablement", "description": "Training and documentation"}
    ],
    "multiSelect": false
  }]
}
```

Map selection to `project_type`:
- "Full platform" → `full_platform`
- "Pipeline only" → `pipeline_only`
- "dbt development" → `dbt_development`
- "Dashboard extension" → `dashboard_extension`
- "Dashboard-first rapid dev" → `dashboard_first`
- "Enablement" → `enablement`

### Step 3: Gather Project Details

**Ask directly in chat** (do NOT use AskUserQuestion for free-text input):

```
What is the project name? (e.g., "acme_marketing_analytics", "client_data_pipeline")
```

Wait for user response.

**Then ask:**

```
What is the client name for this project?
```

Wait for user response.

**After receiving inputs**, derive:
- `client_name`: The display name as provided (e.g., "Acme Corporation")
- `project_name`: Lowercase, underscores for spaces, no special chars (e.g., "acme_marketing_analytics")
- `folder_name`: `{project_id}_{project_name}` (e.g., "20260210_acme_marketing_analytics")

### Step 4: Ask About SOW

**Ask directly in chat:**

```
Do you have a Statement of Work (SOW) or proposal document for this project?
- If yes, please specify the file path (e.g., "path/to/SOW.pdf")
- If no, type "no" and I'll help you create requirements from scratch
```

Wait for user response.

If user provides a path, verify the file exists. If not found, prompt again or offer to continue without SOW.

### Step 5: Confirm Settings

Show the derived values:

```
I'll create the project with these settings:
- Project ID: {project_id}
- Project Type: {project_type}
- Client Name: {client_name}
- Project Name: {project_name}
- Folder: .wire/{folder_name}/
- SOW: {sow_path} (if provided)
```

Use `AskUserQuestion` to confirm:

```json
{
  "questions": [{
    "question": "Create this project?",
    "header": "Confirm",
    "options": [
      {"label": "Yes, create it", "description": "Create the project with these settings"},
      {"label": "Change settings", "description": "Let me provide different settings"}
    ],
    "multiSelect": false
  }]
}
```

If user selects "Change settings", go back to Step 2.

### Step 5.5: Git Branch Check (Mandatory)

**Process**:
1. Run `git rev-parse --abbrev-ref HEAD` via Bash to get the current branch name
2. If the command fails (not a git repo), skip this step silently and proceed to Step 5.6
3. If the branch is `HEAD` (detached HEAD state), skip this step silently
4. If the branch is `main` or `master`:
   - Derive a suggested branch name: `feature/{folder_name}` (e.g., `feature/20260210_acme_marketing_analytics`)
   - Use `AskUserQuestion`:
     ```json
     {
       "questions": [{
         "question": "You're on the [main/master] branch. A feature branch is required for project work. What branch name would you like?",
         "header": "Git Branch",
         "options": [
           {"label": "Use suggested name", "description": "Create and switch to feature/[folder_name]"},
           {"label": "Use project name only", "description": "Create and switch to feature/[project_name]"}
         ],
         "multiSelect": false
       }]
     }
     ```
   - Determine the branch name from the user's selection (or their custom "Other" input)
   - Sanitize the branch name: replace spaces with hyphens, remove characters not in `[a-zA-Z0-9/_-]`
   - Create and switch to the branch via Bash: `git checkout -b [branch_name]`
   - If `git checkout -b` fails because the branch already exists:
     - Ask the user: switch to the existing branch (`git checkout [branch_name]`) or provide a different name
   - Confirm: `Switched to branch: [branch_name]`
   - Store the `branch_name` for display in Step 10
5. If the branch is NOT `main` or `master`:
   - No action needed — the user is already on a feature branch
   - Store the current branch name as `branch_name` for display in Step 10
   - Proceed silently to Step 5.6

### Step 5.6: Jira Integration (Optional)

**Use AskUserQuestion**:

```json
{
  "questions": [{
    "question": "Would you like to track this project in Jira?",
    "header": "Jira Tracking",
    "options": [
      {"label": "Create new Jira issues", "description": "Create Epic, Tasks, and Sub-tasks in Jira"},
      {"label": "Link to existing Jira issues", "description": "Search a Jira project for existing issues and link them"},
      {"label": "No, skip Jira", "description": "Track progress in status.md only"}
    ],
    "multiSelect": false
  }]
}
```

**If "Create new Jira issues"**:

Ask directly in chat:
```
What is the Jira project key? (e.g., DP, ACME, PROJ)
```

Wait for user response. Store the `jira_project_key` and `jira_mode: "create"` for use in Step 9.5.

**If "Link to existing Jira issues"**:

Ask directly in chat:
```
What is the Jira project key to search? (e.g., DP, ACME, PROJ)
```

Wait for user response. Store the `jira_project_key` and `jira_mode: "link"` for use in Step 9.5.

**If "No, skip Jira"**: Skip Jira integration and proceed to Step 6.

> **Note**: This was previously Step 5.5. References from Step 9.5 point here.

### Step 6: Create Folder Structure

**Process**:
1. Create main project folder: `.wire/{folder_name}/`
2. Create subdirectories:
   - `artifacts/` - for source materials (SOW, requirements docs)
   - `requirements/` - requirements phase outputs
   - `design/` - design phase outputs
   - `dev/` - development artifacts (code, models, dashboards)
   - `test/` - testing artifacts and results
   - `deploy/` - deployment artifacts and runbooks
   - `enablement/` - training materials and documentation

**Bash command:**
```bash
mkdir -p .wire/{folder_name}/{artifacts,requirements,design,dev,test,deploy,enablement}
touch .wire/{folder_name}/requirements/.gitkeep .wire/{folder_name}/design/.gitkeep .wire/{folder_name}/dev/.gitkeep .wire/{folder_name}/test/.gitkeep .wire/{folder_name}/deploy/.gitkeep .wire/{folder_name}/enablement/.gitkeep
```

### Step 7: Copy SOW to Artifacts

If SOW path was provided:

**Bash command:**
```bash
cp {sow_path} .wire/{folder_name}/artifacts/
```

### Step 8: Determine Artifact Scope

Based on project_type, set which artifacts are in scope:

**full_platform**: All artifacts applicable
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
workshops: {generate: not_started, review: not_started}
pipeline_design: {generate: not_started, validate: not_started, review: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
pipeline: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
uat: {generate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
```

**pipeline_only**: Only pipeline-related artifacts
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
pipeline_design: {generate: not_started, validate: not_started, review: not_started}
pipeline: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

**dbt_development**: dbt and semantic layer
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

**dashboard_extension**: Dashboards and training
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

**enablement**: Training and documentation only
```yaml
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

**dashboard_first**: Interactive mocks drive data model, dbt with seed data first
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
viz_catalog: {generate: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
seed_data: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
data_refactor: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
uat: {generate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
# workshops: not_applicable
# conceptual_model: not_applicable
# pipeline_design: not_applicable
# pipeline: not_applicable
```

### Step 9: Create Status File

**Process**:
1. Read the template: `TEMPLATES/status-template.md` (in the framework root directory)
2. Replace placeholders:
   - `{{PROJECT_ID}}` → project_id
   - `{{PROJECT_NAME}}` → project_name
   - `{{PROJECT_TYPE}}` → project_type
   - `{{CLIENT_NAME}}` → client_name
   - `{{CREATED_DATE}}` → today's date (YYYY-MM-DD)
   - `{{LAST_UPDATED}}` → today's date (YYYY-MM-DD)
   - `{{ARTIFACTS}}` → artifact scope from Step 8
3. Write to `.wire/{folder_name}/status.md`

### Step 9.5: Set Up Jira Tracking (if opted in)

If the user opted for Jira tracking in Step 5.6:

**Process**:
1. Follow the workflow defined in `specs/utils/jira_create.md`
2. Pass: `jira_project_key`, `jira_mode` (`"create"` or `"link"`), `project_name`, `client_name`, `project_type`, `folder_name`, and the list of in-scope artifacts from Step 8
3. If `jira_mode` is `"create"`: the utility creates the Epic → Task → Sub-task hierarchy and updates `status.md` with all issue keys
4. If `jira_mode` is `"link"`: the utility searches existing Jira issues, presents matches for user confirmation, links matched issues, and updates `status.md` with the linked issue keys
5. If Jira is unavailable, note the failure and continue to Step 10

### Step 10: Confirm Creation and Guide Next Steps

Output confirmation:

```
## Project Created Successfully

**Folder:** `.wire/{folder_name}/`
**Type:** {project_type}
**Client:** {client_name}
**Branch:** {branch_name}

### Folder Structure

.wire/{folder_name}/
├── status.md           # Project tracking
├── artifacts/          # Source materials (SOW, requirements docs)
│   └── SOW.pdf        # [if copied]
├── requirements/       # Requirements specifications
├── design/            # Design artifacts
├── dev/               # Development artifacts
├── test/              # Testing artifacts
├── deploy/            # Deployment artifacts
└── enablement/        # Training and documentation

### Jira Tracking (if created)

**Epic**: [EPIC_KEY] — [client_name] - [project_name] Data Platform
**Tasks**: [count] artifact tasks with sub-tasks for generate/validate/review

### Next Steps

1. **Review source materials** in `.wire/{folder_name}/artifacts/`
   - SOW has been copied (if provided)
   - Add any other requirements documents or references

2. **Generate requirements** from the SOW:
   /wire:requirements-generate {folder_name}

3. **Check project status** anytime:
   /wire:status {folder_name}

4. **When ready to merge**, create a pull request:
   /wire:utils-create-pr {folder_name}

### Quick Commands for This Project

| Command | Purpose |
|---------|---------|
| `/wire:status {folder_name}` | View project status and next actions |
| `/wire:requirements-generate {folder_name}` | Extract requirements from SOW |
| `/wire:workshops-generate {folder_name}` | Generate workshop materials |
| `/wire:pipeline_design-generate {folder_name}` | Design data pipeline |
| `/wire:dbt-generate {folder_name}` | Generate dbt models |
| `/wire:training-generate {folder_name}` | Generate training materials |
```

## Edge Cases

### Not a Git Repository

If `git rev-parse --abbrev-ref HEAD` fails (exit code non-zero), skip the git branch check silently. The project can still be created outside of a git repo.

### Detached HEAD State

If the branch name is `HEAD` (detached HEAD), skip the branch check — the user is not on main/master so no action is needed.

### Branch Already Exists

If `git checkout -b [branch_name]` fails because the branch already exists:
1. Inform user: "Branch `[branch_name]` already exists."
2. Ask if they want to:
   - Switch to it (`git checkout [branch_name]`)
   - Provide a different branch name

### Invalid Branch Name

If the user provides a custom branch name via "Other":
- Replace spaces with hyphens
- Remove characters not matching `[a-zA-Z0-9/_-]`
- If the sanitized name is empty, re-prompt

### Project Name Validation

If the user provides an empty or invalid project name:
- Re-prompt with: "Please provide a valid project name (letters, numbers, underscores allowed)"

### Folder Already Exists

If the calculated folder already exists:
1. Inform user: "A folder with this name already exists"
2. Ask if they want to:
   - Use a different name (append letter suffix)
   - View the existing project
   - Overwrite (with confirmation)

### SOW File Not Found

If the SOW path provided doesn't exist:
1. Inform user: "SOW file not found at path: {path}"
2. Ask if they want to:
   - Provide a different path
   - Continue without SOW
   - Cancel project creation

### Permission Errors

If folder creation fails:
1. Report the error
2. Suggest manual creation steps
3. Verify directory permissions

## Output

This command creates files and folders:
- `.wire/{folder_name}/` directory structure
- `.wire/{folder_name}/status.md` file
- Copies SOW to artifacts/ (if provided)

Final output is a confirmation message with next steps.

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
