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

## Workflow Specification

---
description: Remove an existing release from the current engagement, with confirmation
argument-hint: <release-folder>
---

# Wire Remove Release Command

## Purpose

Interactive workflow to remove an existing release from the current engagement. Handles issue-tracker cleanup notes and folder deletion with safety confirmations.

Wire is one-engagement-per-repo: there is exactly one client per `.wire/` root, so this command removes one **release folder** (e.g. `01-discovery`) under `.wire/releases/` — active or archived — not a whole client project.

## Workflow

### Step 1: List Existing Releases

**Process**:
1. Use Bash to find all existing release folders (active and archived):
   ```bash
   ls -d .wire/releases/*/ 2>/dev/null | grep -v '/_archive/$'
   ls -d .wire/releases/_archive/*/ 2>/dev/null
   ```
2. If no releases found (both empty), output message and exit:
   ```
   No releases found in `.wire/releases/`. Nothing to remove.
   ```
3. For each release folder found, note:
   - `release_folder`: the folder name (e.g. `01-discovery`)
   - whether it's active or under `_archive/`

4. For each release, read `.wire/releases/{release_folder}/status.md` (or `.wire/releases/_archive/{release_folder}/status.md` if archived) to get `release_type` and `current_phase`

### Step 2: Ask Which Release to Remove

**Use AskUserQuestion** to present release options:

```json
{
  "questions": [{
    "question": "Which release do you want to remove?",
    "header": "Select",
    "options": [
      {"label": "01-discovery", "description": "discovery — Discovery (Shape Up)"},
      {"label": "02-full-platform", "description": "full_platform — Requirements (archived)"}
    ],
    "multiSelect": false
  }]
}
```

Build options dynamically from discovered releases. Include up to 4 releases as options (AskUserQuestion limit). If more than 4 releases exist, list them all in chat first and ask the user to specify by name.

### Step 3: Show Deletion Preview & Confirm

**Process**:
1. Use `find .wire/releases/{release_folder}/ -type f` (or the `_archive/` path if archived) to list all files that will be deleted
2. Count files and subdirectories

**Display preview:**
```
## Deletion Preview

**Release:** {release_folder} ({release_type})
**Folder:** .wire/releases/{release_folder}/

### Contents to be deleted:
- status.md
- artifacts/ (X files)
- requirements/ (Y files)
- design/ (Z files)
- dev/ (W files)
- test/ (V files)
- deploy/ (U files)
- enablement/ (T files)

**Total:** N files will be permanently deleted
```

(List only the subfolders that actually exist for this release type — e.g. discovery releases have `artifacts/` and `planning/`, not `dev/`/`test/`/`deploy/`.)

**Use AskUserQuestion** for confirmation:

```json
{
  "questions": [{
    "question": "This action is IRREVERSIBLE. All release files will be permanently deleted. Proceed?",
    "header": "Confirm",
    "options": [
      {"label": "Yes, delete it", "description": "Permanently remove this release and all its files"},
      {"label": "Cancel", "description": "Keep the release, do not delete anything"}
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
rm -rf .wire/releases/{release_folder}/
```
(or `.wire/releases/_archive/{release_folder}/` if the release was archived)

Capture exit code. If non-zero, report error and suggest manual deletion.

### Step 5: Confirm Removal

Output confirmation:

```
## Release Removed Successfully

**Deleted:** .wire/releases/{release_folder}/

### Summary
- Removed {N} files

### Remaining Releases
Run `/wire:status` to see remaining releases in this engagement.
```

## Edge Cases

### No Releases Exist

If no release folders are found (active or archived):
```
No releases found in `.wire/releases/`. Nothing to remove.
```
Exit without further prompts.

### More Than 4 Releases

AskUserQuestion supports max 4 options. If more releases exist:
1. List all releases in chat with their folder names and types
2. Ask user to type the folder name directly:
   ```
   You have {N} releases. Please type the folder name of the release to remove (e.g., "01-discovery"):
   ```
3. Wait for text input, then continue to Step 3

### Removing the Only Release in the Engagement

If this is the last release under `.wire/releases/`, removing it leaves the engagement with no releases at all (`.wire/engagement/context.md` is untouched). Note this in the confirmation preview:
```
Note: this is the only release in this engagement. After removal, run /wire:new to add a new release.
```

### Permission Errors

If `rm -rf` fails:
1. Report the error message
2. Suggest manual deletion:
   ```
   Could not delete folder. Try manually:
   rm -rf .wire/releases/{release_folder}/
   ```

### User Cancels

If user selects "Cancel" at confirmation:
```
Removal cancelled. No changes were made.
```

## Output

This command:
- Deletes `.wire/releases/{release_folder}/` (or `.wire/releases/_archive/{release_folder}/`) directory and all contents

Final output is a confirmation message with summary.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
