---
description: Remove a project with confirmation
argument-hint: <project-folder>
---

# Remove a project with confirmation

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
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"remove\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.3.1\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Remove an existing Data Platform project with confirmation
---

# Data Platform Remove Project Command

## Purpose

Interactive workflow to remove an existing Data Platform project. Handles registry cleanup and folder deletion with safety confirmations.

## Workflow

### Step 1: List Existing Projects

**Process**:
1. Use Bash to find all existing project folders:
   ```bash
   ls -d .wire/[0-9]*_*/ 2>/dev/null
   ```
2. If no projects found (empty output), output message and exit:
   ```
   No projects found in `.wire/`. Nothing to remove.
   ```
3. Parse folder names to extract:
   - `project_id`: Everything before the first underscore (e.g., "20260210")
   - `project_name`: Everything after the first underscore (e.g., "acme_corp")
   - `folder_name`: Full folder name (e.g., "20260210_acme_corp")

4. For each project, read `.wire/{folder_name}/status.md` to get the client name (if available)

### Step 2: Ask Which Project to Remove

**Use AskUserQuestion** to present project options:

```json
{
  "questions": [{
    "question": "Which project do you want to remove?",
    "header": "Select",
    "options": [
      {"label": "20260210_acme_corp", "description": "Client: Acme Corp"},
      {"label": "20260115_beta_inc", "description": "Client: Beta Inc"}
    ],
    "multiSelect": false
  }]
}
```

Build options dynamically from discovered projects. Include up to 4 projects as options (AskUserQuestion limit). If more than 4 projects exist, list them all in chat first and ask user to specify by name.

### Step 3: Show Deletion Preview & Confirm

**Process**:
1. Use `find .wire/{folder_name}/ -type f` to list all files that will be deleted
2. Count files and subdirectories

**Display preview:**
```
## Deletion Preview

**Project:** {project_id} - {client_name}
**Folder:** .wire/{folder_name}/

### Contents to be deleted:
- status.md
- artifacts/ (X files)
- prep/ (Y files)
- dev/ (Z files)
- prod/ (W files)

**Total:** N files will be permanently deleted
```

**Use AskUserQuestion** for confirmation:

```json
{
  "questions": [{
    "question": "This action is IRREVERSIBLE. All project files will be permanently deleted. Proceed?",
    "header": "Confirm",
    "options": [
      {"label": "Yes, delete it", "description": "Permanently remove this project and all its files"},
      {"label": "Cancel", "description": "Keep the project, do not delete anything"}
    ],
    "multiSelect": false
  }]
}
```

If user selects "Cancel", output:
```
Removal cancelled. No changes were made.
```
And exit.

### Step 4: Delete Folder

**Bash command:**
```bash
rm -rf .wire/{folder_name}/
```

Capture exit code. If non-zero, report error and suggest manual deletion.

### Step 5: Confirm Removal

Output confirmation:

```
## Project Removed Successfully

**Deleted:** .wire/{folder_name}/

### Summary
- Removed {N} files

### Remaining Projects
Run `/wire:status` to see remaining projects.
```

## Edge Cases

### No Projects Exist

If no project folders are found:
```
No projects found in `.wire/`. Nothing to remove.
```
Exit without further prompts.

### More Than 4 Projects

AskUserQuestion supports max 4 options. If more projects exist:
1. List all projects in chat with their IDs and names
2. Ask user to type the folder name directly:
   ```
   You have {N} projects. Please type the folder name of the project to remove (e.g., "20260210_acme_corp"):
   ```
3. Wait for text input, then continue to Step 3

### Permission Errors

If `rm -rf` fails:
1. Report the error message
2. Suggest manual deletion:
   ```
   Could not delete folder. Try manually:
   rm -rf .wire/{folder_name}/
   ```

### User Cancels

If user selects "Cancel" at confirmation:
```
Removal cancelled. No changes were made.
```

## Output

This command:
- Deletes `.wire/{folder_name}/` directory and all contents

Final output is a confirmation message with summary.

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
