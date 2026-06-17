---
description: Upgrade a release folder's status.md to the current plugin version schema — adds missing sections, surfaces new commands, never overwrites existing values
argument-hint: [release-folder] [--dry-run]
---

# Upgrade a release folder's status.md to the current plugin version schema — adds missing sections, surfaces new commands, never overwrites existing values

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
description: Upgrade a release folder's status.md and Wire files to the current plugin version schema — adds missing sections, surfaces new commands, never overwrites existing values
argument-hint: [release-folder]
---

# Wire Upgrade Command

## Purpose

Bring an existing release folder up to date with the schema introduced by the currently installed Wire plugin. Safe to re-run at any time.

What it does:
- Reads `status.md` and detects the release type
- Compares the current status.md against the canonical template for that release type
- Adds any top-level sections and nested keys that are missing, using `not_started` / `null` defaults
- Stamps `wire_plugin_version` and `last_upgraded_at` into the frontmatter
- Reports what was added and surfaces new commands that weren't available when the release was created
- Never overwrites values that already exist

What it does not do:
- Modify artifact files (requirements.md, data_model.md, etc.)
- Re-generate any artifacts
- Change existing status values
- Alter engagement-level files (`.wire/engagement/context.md`)

## Usage

```bash
/wire:upgrade 20260210_acme_analytics   # upgrade a specific release folder
/wire:upgrade                            # auto-detect the most recently modified release
/wire:upgrade --dry-run 20260210_acme   # show what would change without modifying anything
```

`--dry-run` prints the diff as a YAML patch and exits without writing.

## Prerequisites

- `.wire/` directory exists in the current repo
- The named release folder exists under `.wire/releases/`

---

## Workflow

### Step 1: Resolve the Release Folder

If a `<release-folder>` argument is provided:
1. Look for `.wire/releases/<release-folder>/status.md`
2. If not found, try `.wire/<release-folder>/status.md` (pre-v3.4 flat layout — redirect the user to `/wire:migrate` first)

If no argument is provided:
1. Glob `.wire/releases/*/status.md`
2. Sort by `last_modified` descending — take the first result
3. Confirm with the user:
   ```
   No release folder specified. Found: <folder-name> (last modified <date>)
   Upgrade this release? (yes/no)
   ```

Set `release_folder` and `status_path`.

---

### Step 2: Read Current Status

Read and parse the YAML frontmatter of `status_path`.

Extract:
- `release_type` — the release type identifier (e.g. `full_platform`, `droughty`, `platform_migration`)
- `wire_plugin_version` — the version when this release was last upgraded (may be absent on older releases)
- `created_date`
- `project_name` / `project_id` / `client_name` for the summary header

If `release_type` is absent or unrecognised, ask:
```
What is the release type for this release? (e.g. full_platform, dbt_development, platform_migration, droughty, discovery, agentic_commerce, agentic_data_stack, custom)
```

---

### Step 3: Detect Current Plugin Version

Check in order:

1. Plugin-installed mode: `~/.claude/plugins/wire/.claude-plugin/plugin.json` — read `version`
2. Dev mode: `wire/packaging/claude-plugin/.claude-plugin/plugin.json` — read `version`
3. Fallback: set `current_version` to `"unknown"` and note that version stamping will be skipped

Store as `current_version`.

---

### Step 4: Load the Canonical Template

Map `release_type` to its template file. Resolve relative to the plugin root (plugin mode: `~/.claude/plugins/wire/`, dev mode: the repo root):

| `release_type` | Template path |
|---|---|
| `full_platform`, `dbt_development` | `wire/TEMPLATES/status-template.md` |
| `platform_migration`, `data_warehouse_migration` | `wire/TEMPLATES/migration/status_migration.md` |
| `droughty` | `wire/TEMPLATES/droughty-status-template.md` |
| `agentic_commerce` | `wire/TEMPLATES/agentic-commerce-status-template.md` |
| `agentic_data_stack` | `wire/TEMPLATES/agentic_data_stack/status_agentic_data_stack.md` |
| `discovery`, `shape_up_discovery` | `wire/TEMPLATES/discovery-status-template.md` |
| `sop_discovery` | `wire/TEMPLATES/sop-discovery-status-template.md` |
| `custom` | `wire/TEMPLATES/custom-status-template.md` |

If the template file cannot be found, surface a clear error:
```
Template not found for release_type: <type>
Expected: <path>

If this is a custom release type, run /wire:custom/define <release-folder> to update it.
```

Read and parse the template YAML frontmatter as `template_schema`.

---

### Step 5: Compute the Schema Diff

Compare `current_status` (the release's existing YAML) against `template_schema` (the canonical template).

**Rules:**

1. **Top-level keys**: for each key present in `template_schema` but absent from `current_status`, mark it as `MISSING — add with template default`.
2. **Nested keys within existing sections**: for each key present in `template_schema[section]` but absent from `current_status[section]`, mark it as `MISSING — add with template default`. Only descend one level — do not recurse deeper into already-present structures.
3. **Never touch**: keys present in `current_status` with non-null/non-`not_started` values. Do not flag as needing update.
4. **Template placeholders**: strip `{{...}}` placeholders from template defaults — replace with `null` or `not_started` as appropriate for the field type.
5. **Jira/Linear/docstore blocks**: if the current status already has `jira: null` or `linear: null`, treat the block as intentionally configured (not missing) — do not expand it. Only add the block if it is entirely absent.

If there are no differences, skip to Step 7 (summary).

---

### Step 6: Apply the Upgrade (unless `--dry-run`)

**If `--dry-run`**:

Print the proposed YAML patch:

```
## Dry-run: changes that would be applied to .wire/releases/<folder>/status.md

### New top-level sections
droughty: (entire section — 9 keys)

### New keys within existing sections
artifacts.droughty:
  generate: not_started
  validate: not_started
  review: not_started

### Frontmatter stamps
wire_plugin_version: 3.8.2
last_upgraded_at: 2026-06-11

No files were modified. Remove --dry-run to apply.
```

**Otherwise:**

1. Parse the full `status.md` content (frontmatter + body)
2. Merge missing sections and keys into the YAML frontmatter using a recursive merge that preserves existing values
3. Add or update two frontmatter fields:
   ```yaml
   wire_plugin_version: "<current_version>"
   last_upgraded_at: "<today>"
   ```
4. Write the updated content back to `status_path`, preserving the document body (non-frontmatter content) unchanged

If the write fails, surface the error and leave the original file unchanged.

---

### Step 7: Surface New Commands

Based on `release_type` and the detected additions, report any commands that are now available but were not present in the installed version when the release was created. Use the following known command introductions as the reference:

| Added in | Commands | Relevant release types |
|---|---|---|
| v3.9.0 | `/wire:delegate` | all — batch dispatch to specialist local subagents for pending artifact work |
| v3.8.0 | `/wire:droughty-*` (9 commands) | all — can be added to any release as an optional phase |
| v3.8.1 | `/wire:dbt-migration-lint` | `platform_migration`, `data_warehouse_migration`, `dbt_development` |
| v3.7.x | `/wire:utils/delivery-forecast` | all |
| v3.5.x | `/wire:utils/doc-analyze`, `/wire:custom/define` | all |

Only surface commands where the release's `wire_plugin_version` (before this upgrade) is older than the version in which the command was added. If `wire_plugin_version` was absent (first upgrade), surface all commands not already reflected in the status.md structure.

Format:
```
### New commands available for this release

These commands were added since this release was created and are now available:

  /wire:droughty-setup <release-folder>     — install Droughty and configure warehouse profile
  /wire:droughty-generate <release-folder>  — run the full Droughty discovery or post-dbt phase
  /wire:dbt-migration-lint <release-folder> — pre-warehouse equivalence lint (platform_migration only)

Run /wire:help droughty for full documentation on the Droughty commands.
```

---

### Step 8: Confirm and Summarise

```
## Upgrade Complete ✅

Release: <project_name> (<release-folder>)
Type:    <release_type>
Plugin:  <wire_plugin_version_before> → <current_version>

### Changes applied

<list each added section/key, or "No schema changes needed — status.md is already current">

### New commands available
<list, or "None — all commands for this release type were available when this release was created">

### No changes made to
- Artifact files (requirements.md, data_model.md, …)
- Existing status values
- Engagement context (.wire/engagement/context.md)

Run /wire:status <release-folder> to see the updated artifact lifecycle.
```

---

## Re-running Safely

`/wire:upgrade` is idempotent. Running it twice against the same release produces no changes on the second run — all sections already exist, and the `wire_plugin_version` and `last_upgraded_at` stamps are already present. Running it after a future plugin upgrade will add any new sections introduced in that version.

## Relationship to `/wire:migrate`

`/wire:migrate` handles structural layout changes (flat → two-tier directory structure). `/wire:upgrade` handles schema changes within an already-correct layout (missing YAML keys and sections as the framework evolves). If a release folder is on the pre-v3.4 flat layout, `/wire:upgrade` will detect this and redirect:

```
This release appears to be on the pre-v3.4 flat layout.
Run /wire:migrate first, then re-run /wire:upgrade.
```

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
