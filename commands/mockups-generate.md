---
description: Generate dashboard mockups
argument-hint: <project-folder>
---

# Generate dashboard mockups

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.3.1\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"mockups-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.3.1\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate mockups from design and requirements
argument-hint: <project-folder>
---

# mockups Generate Command

## Purpose

Generate dashboard mockups based on requirements. Supports two modes:
- **Dashboard-first mode** (`dashboard_first` projects): Guides consultant through creating interactive Lovable mocks via `getmock.rittmananalytics.com`
- **Standard mode** (all other project types): Generates ASCII wireframe mockups directly from requirements

## Usage

```bash
/wire:mockups-generate YYYYMMDD_project_name
```

## Prerequisites

- `requirements.review` must be `approved` in status.md

## Workflow

### Step 0: Determine Mode

**Process**:
1. Read `.wire/<project-folder>/status.md`
2. Parse YAML frontmatter to extract `project_type`
3. If `project_type` is `dashboard_first` → follow **Dashboard-First Mode** (Step 1A onwards)
4. Otherwise → follow **Standard Mode** (Step 1B onwards)

Also verify prerequisites:
- Check `artifacts.requirements.review` is `approved`
- If not, show error and suggest `/wire:requirements-review <project>`

---

## Dashboard-First Mode (for `dashboard_first` projects)

### Step 1A: Read Requirements and Generate Lovable Brief

**Process**:
1. Read `.wire/<project-folder>/requirements/requirements_specification.md`
2. Read `.wire/<project-folder>/artifacts/` for any SOW or supplementary materials
3. From the requirements, extract:
   - The primary use case or domain (e.g., "student retention analytics", "retail sales dashboard")
   - Key questions to be answered / jobs-to-be-done
   - Known data sources and their general nature
   - Target audience and their roles

4. Generate a **Lovable session brief** summarizing what the mock dashboards should demonstrate. Save this to `.wire/<project-folder>/design/lovable_session_brief.md` with this structure:

```markdown
# Lovable Dashboard Mock Brief

## Use Case
[One-line description of the use case]

## Key Questions to Answer
- [Question 1 from requirements]
- [Question 2]
- ...

## Suggested Dashboard Pages
Based on the requirements, the mock should include these dashboard pages:
1. [Page name] — [what it shows]
2. [Page name] — [what it shows]
...

## Data Domain Context
[Brief description of the domain, data sources, and typical metrics for this vertical]

## Target Users
- [Role 1]: needs [what]
- [Role 2]: needs [what]
```

### Step 2A: Present Lovable URL and Instructions

**Process**:
1. URL-encode the use case description (spaces → `%20`, special chars encoded)
2. Construct the URL: `https://getmock.rittmananalytics.com/?usecase=<url_encoded_use_case>`

3. Present to the consultant:

```
## Dashboard Mock Creation — Lovable

### Session Brief
I've generated a session brief at:
**File:** `design/lovable_session_brief.md`

### Create the Mock Dashboard

1. Open this URL in your browser:
   **[getmock URL]**

2. Select the **Rittman Analytics** workspace when prompted

3. Lovable will create an interactive dashboard mock. Once it's ready:
   - Review the dashboard and iterate with Lovable if needed
   - **Publish** the dashboard using the Publish button (give it a descriptive subdomain)

4. Once you're happy with the mock, run this prompt in the Lovable session:

   ```
   create two text files that you should link-to from the help (question-mark icon)
   button in the top-right-hand side of the dashboard app:
   - a csv file-format document called "dashboard_visualization_catalog.csv" that
     details, one-row per dashboard data visualization, the dashboard page name,
     data visualisation name, data visualization chart or table type and the measures
     and dimensions that data visualization would require in-order to produce
   - a specification document in markdown (.md) format called "dashboard_spec.md"
     that details the purpose, design and contents of this dashboard in enough-detail
     that an LLM agent separate to loveable.dev could use this spec to produce a
     Looker LookML dashboard matching its design. The document should exclude any
     details about colours, fonts, headers etc as these will automatically be added
     by Looker, or data model details etc. Just focus on the dashboard data viz
     contents, and make it so that the user doesn't have to login to loveable.dev
     to see these docs
   ```

5. Download both files from Lovable and save them into the project:
   - `design/dashboard_visualization_catalog.csv`
   - `design/dashboard_spec.md`

### When you're done, tell me:
- The published Lovable URL (e.g., https://myproject-demo.lovable.app/)
- Confirm the CSV and MD files are saved in the design/ folder
```

### Step 3A: Validate Files and Record URL

**Process**:
Wait for the consultant to respond. Then:

1. Verify the files exist:
   - Check `.wire/<project-folder>/design/dashboard_visualization_catalog.csv` exists and has content
   - Check `.wire/<project-folder>/design/dashboard_spec.md` exists and has content

2. If either file is missing, inform the consultant and re-prompt them to save the files

3. Once both files are confirmed:
   - Read the CSV to verify it has the expected columns (dashboard page, visualization name, chart type, measures, dimensions)
   - Read the MD to verify it contains dashboard specification content

4. Record the Lovable URL in status.md frontmatter:
   ```yaml
   lovable_url: https://[subdomain].lovable.app/
   ```

### Step 4A: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.mockups section:
   ```yaml
   mockups:
     generate: complete
     review: not_started
     generated_date: [today's date]
     lovable_url: [the published URL]
   ```
3. Write updated status.md

### Step 5A: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `mockups`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 6A: Confirm and Suggest Next Steps

**Output**:
```
## Dashboard Mocks Generated Successfully

**Lovable URL:** [published URL]
**Session Brief:** `design/lovable_session_brief.md`
**Visualization Catalog:** `design/dashboard_visualization_catalog.csv`
**Dashboard Spec:** `design/dashboard_spec.md`

### Next Steps

1. **Share the published mock** with stakeholders for feedback
2. **Review mockups**: `/wire:mockups-review <project>`
3. After review approval, **generate visualization catalog**: `/wire:viz_catalog-generate <project>`
```

---

## Standard Mode (for non-dashboard_first projects)

### Step 1B: Read Inputs

**Process**:
1. Read `.wire/<project-folder>/requirements/requirements_specification.md`
2. Read any design documents in `.wire/<project-folder>/design/`
3. Identify the dashboards, reports, or UI screens that need mockups based on requirements

### Step 2B: Generate Wireframe Mockups

**Process**:
For each dashboard or screen identified in the requirements:

1. Create an ASCII wireframe mockup showing:
   - Dashboard layout with sections and panels
   - Chart/visualization placeholders with type labels (bar chart, line chart, KPI tile, table, etc.)
   - Filter bar with expected filter controls
   - Data labels showing which measures and dimensions power each visualization

2. Format each mockup as a markdown document with:
   - Dashboard title and purpose
   - Target audience
   - ASCII wireframe diagram
   - Data requirements table listing measures and dimensions per visualization
   - Filter specifications
   - Interaction notes (drill-downs, cross-filtering, etc.)

3. Save all mockups to `.wire/<project-folder>/design/mockups/`:
   - One file per dashboard: `mockup_[dashboard_name].md`
   - Summary file: `mockups_index.md` listing all mockups with links

### Step 3B: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.mockups section:
   ```yaml
   mockups:
     generate: complete
     review: not_started
     generated_date: [today's date]
   ```
3. Write updated status.md

### Step 4B: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `mockups`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 5B: Confirm and Suggest Next Steps

**Output**:
```
## Mockups Generated Successfully

**File(s):** [list generated mockup files]
**Index:** `design/mockups/mockups_index.md`

### Next Steps

1. **Review mockups** with stakeholders: `/wire:mockups-review <project>`
2. After approval, proceed with data model design
```

---

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### Lovable Files Not Found (Dashboard-First Mode)

If the consultant says they've saved the files but they can't be found:
1. Check common alternative locations (project root, `design/` subdirectories)
2. Ask the consultant to confirm the exact file paths
3. Offer to help move files to the correct location

### CSV Format Issues (Dashboard-First Mode)

If the CSV doesn't have expected columns:
- Inform the consultant
- Suggest re-running the Lovable prompt with the exact template
- Offer to proceed anyway if the data is usable in a different format

## Output

This command creates:
- **Dashboard-first mode**: `design/lovable_session_brief.md`, `design/dashboard_visualization_catalog.csv`, `design/dashboard_spec.md`
- **Standard mode**: `design/mockups/mockup_*.md`, `design/mockups/mockups_index.md`
- Updates `status.md`

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
