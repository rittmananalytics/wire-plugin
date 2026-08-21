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
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Archive a completed release within the current engagement
argument-hint: <release-folder>
---

# Wire Archive Release Command

## Purpose

Move a completed release to an archive location within the current engagement, to keep the active release list small. Archived releases are excluded from `/wire:status` and `/wire:start` scans but remain accessible via `/wire:status --archived`.

Wire is one-engagement-per-repo: there is exactly one client per `.wire/` root, so "archiving" here means archiving one completed **release** (e.g. `01-discovery`) within the current engagement — not switching between sibling client projects, which is not a concept that exists in the current layout.

## Archive Convention

Archived releases move one level deeper, from:
```
.wire/releases/<release_folder>/
```
to:
```
.wire/releases/_archive/<release_folder>/
```

This means a plain `.wire/releases/*/status.md` glob (used by `/wire:status` and `/wire:start`) naturally excludes archived releases without needing an exclude-list, and `/wire:status --archived` globs `.wire/releases/_archive/*/status.md` specifically. `_archive` is not a valid release folder name (release folders are always `NN-name`), so it can never collide with a real release.

## Usage

```bash
/wire:archive 01-discovery
```

## Workflow

### Step 1: List Active Releases

**Process**:
1. Use Glob to find all active release folders: `.wire/releases/*/status.md`
2. Exclude any match under `.wire/releases/_archive/` (shouldn't normally match the glob above, but guard against it anyway)
3. If `$ARGUMENTS` is provided, match against known release folders
4. If no arguments, present selection

**If no releases found**:
```
No active releases found in `.wire/releases/`. Nothing to archive.
```

### Step 2: Select Release to Archive

**If argument provided**: Validate the folder exists under `.wire/releases/`

**If no argument**: Use `AskUserQuestion` to present release options:

```json
{
  "questions": [{
    "question": "Which release do you want to archive?",
    "header": "Archive",
    "options": [
      {"label": "01-discovery", "description": "discovery — Discovery (Shape Up)"},
      {"label": "02-full-platform", "description": "full_platform — Requirements"}
    ],
    "multiSelect": false
  }]
}
```

Build options dynamically from discovered releases (folder name plus `release_type` and `current_phase` from each `status.md`). Include up to 4 releases as options (AskUserQuestion limit). If more than 4 releases exist, list them all in chat first and ask the user to specify by name.

### Step 3: Confirm Archive

**Use AskUserQuestion** for confirmation:

```json
{
  "questions": [{
    "question": "Archive this release? It will be moved to .wire/releases/_archive/ and hidden from /wire:status and /wire:start.",
    "header": "Confirm",
    "options": [
      {"label": "Yes, archive it", "description": "Move release to .wire/releases/_archive/"},
      {"label": "Cancel", "description": "Keep the release active"}
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
   mkdir -p .wire/releases/_archive/
   ```
2. Move the release folder:
   ```bash
   git mv .wire/releases/{release_folder}/ .wire/releases/_archive/{release_folder}/
   ```

### Step 5: Confirm Archive

Output confirmation:

```
## Release Archived

**Moved:** `.wire/releases/{release_folder}/` → `.wire/releases/_archive/{release_folder}/`

The release won't appear in `/wire:status` or `/wire:start`.

To view archived releases: `/wire:status --archived`
```

## Edge Cases

### No Releases Exist

If no release folders are found:
```
No active releases found in `.wire/releases/`. Nothing to archive.
```

### Release Not Found

If the specified release doesn't exist:
```
Release "{release_folder}" not found in `.wire/releases/`.

Active releases:
[list active releases]
```

### Already Archived

If the release is already in `.wire/releases/_archive/`:
```
Release "{release_folder}" is already archived.
```

### Git Not Available

If `git mv` fails, fall back to a regular move:
```bash
mkdir -p .wire/releases/_archive/
mv .wire/releases/{release_folder}/ .wire/releases/_archive/{release_folder}/
```

## Output

This command:
- Moves `.wire/releases/{release_folder}/` to `.wire/releases/_archive/{release_folder}/`

Final output is a confirmation message.

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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
