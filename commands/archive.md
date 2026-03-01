---
description: Archive a completed project
argument-hint: <project-folder>
---

# Archive a completed project

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
description: Archive a completed Data Platform project
argument-hint: <dashboard-folder>
---

# Data Platform Archive Project Command

## Purpose

Move a completed project to the archive folder to keep the active project list small. Archived projects are excluded from `/wire:status` and `/wire:start` scans but remain accessible via `/wire:status --archived`.

## Usage

```bash
/wire:archive 20260210_rowcal
```

## Workflow

### Step 1: List Active Projects

**Process**:
1. Use Glob to find all active project folders: `.wire/[0-9]*_*/status.md`
2. If `$ARGUMENTS` is provided, match against known projects
3. If no arguments, present selection

**If no projects found**:
```
No active projects found in `.wire/`. Nothing to archive.
```

### Step 2: Select Project to Archive

**If argument provided**: Validate the folder exists in `.wire/`

**If no argument**: Use `AskUserQuestion` to present project options:

```json
{
  "questions": [{
    "question": "Which project do you want to archive?",
    "header": "Archive",
    "options": [
      {"label": "20260210_rowcal", "description": "Client: RowCal"},
      {"label": "20260203_b2b_template_tabs", "description": "Client: Internal"}
    ],
    "multiSelect": false
  }]
}
```

Build options dynamically from discovered projects. Include up to 4 projects as options (AskUserQuestion limit). If more than 4 projects exist, list them all in chat first and ask user to specify by name.

### Step 3: Confirm Archive

**Use AskUserQuestion** for confirmation:

```json
{
  "questions": [{
    "question": "Archive this project? It will be moved to .wire/archive/ and hidden from /wire:status and /wire:start.",
    "header": "Confirm",
    "options": [
      {"label": "Yes, archive it", "description": "Move project to .wire/archive/"},
      {"label": "Cancel", "description": "Keep the project active"}
    ],
    "multiSelect": false
  }]
}
```

If user selects "Cancel":
```
Archive cancelled. No changes were made.
```
And exit.

### Step 4: Move to Archive

**Process**:
1. Create archive directory if it doesn't exist:
   ```bash
   mkdir -p .wire/archive/
   ```
2. Move the project folder:
   ```bash
   git mv .wire/{folder_name}/ .wire/archive/{folder_name}/
   ```

### Step 5: Confirm Archive

Output confirmation:

```
## Project Archived

**Moved:** `.wire/{folder_name}/` → `.wire/archive/{folder_name}/`

The project won't appear in `/wire:status` or `/wire:start`.

To view archived projects: `/wire:status --archived`
```

## Edge Cases

### No Projects Exist

If no project folders are found:
```
No active projects found in `.wire/`. Nothing to archive.
```

### Project Not Found

If the specified project doesn't exist:
```
Project "{folder_name}" not found in `.wire/`.

Active projects:
[list active projects]
```

### Already Archived

If the project is already in `.wire/archive/`:
```
Project "{folder_name}" is already archived.
```

### Git Not Available

If `git mv` fails, fall back to regular move:
```bash
mv .wire/{folder_name}/ .wire/archive/{folder_name}/
```

## Output

This command:
- Moves `.wire/{folder_name}/` to `.wire/archive/{folder_name}/`

Final output is a confirmation message.

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
