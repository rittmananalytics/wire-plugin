---
description: DBML entity-relationship diagram from warehouse schema
argument-hint: <release-folder>
---

# DBML entity-relationship diagram from warehouse schema

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
description: Generate a DBML entity-relationship diagram from the live warehouse schema
argument-hint: <release-folder>
---

# Droughty DBML Command

## Purpose

Run `droughty dbml` to produce a DBML entity-relationship diagram from the live warehouse schema. Infers relationships from `_pk` and `_fk` column-naming conventions. The resulting `.dbml` file can be rendered at dbdocs.io or dbdiagram.io and is stored in Wire's artifact directory for reference in subsequent phases.

## Usage

```bash
/wire:droughty-dbml <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete for this release
- Warehouse accessible

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete`
3. Extract `warehouse`, `schemas`, `profile_name`

### Step 2: Run droughty dbml

```bash
droughty dbml \
  --profile-dir ~/.droughty \
  --project-dir .
```

This writes a `.dbml` file to `droughty_project.yaml → dbml_path`, which is `.wire/releases/[release]/artifacts/droughty/`.

Capture stdout and stderr. If the command exits non-zero, surface the full error output and stop.

### Step 3: Verify Output

Check that a `.dbml` file was written to the artifact directory. If the file is empty or absent:
```
⚠️  droughty dbml ran but produced no output.

Possible causes:
- No tables found in the configured schemas
- All tables were excluded in droughty_project.yaml
- A silent connection error occurred

Check the schemas listed in ~/.droughty/profile.yaml and re-run.
```

### Step 4: Summarise the ERD

Read the generated `.dbml` file and produce a brief summary for the consultant:
- Number of tables in the diagram
- Number of relationships inferred
- Any tables with no inferred relationships (isolated nodes)

### Step 5: Update status.md

```yaml
droughty:
  dbml:
    status: complete
    tables_in_diagram: [n]
    relationships_inferred: [n]
    artifact: .wire/releases/[release]/artifacts/droughty/[filename].dbml
    completed_date: [today]
```

### Step 6: Confirm Output

```
## DBML Diagram Generated ✅

[n] tables, [n] relationships inferred from naming conventions

Artifact: .wire/releases/[release]/artifacts/droughty/[filename].dbml

To render the diagram:
  1. Visit https://dbdiagram.io or https://dbdocs.io
  2. Paste or upload the .dbml file
  3. Share the rendered link with stakeholders

This DBML artifact is available to:
  /wire:problem-definition-generate   — embeds the ERD as supporting evidence
  /wire:requirements-generate         — references the entity structure
```

**Note on relationship inference**: `droughty dbml` infers relationships from `_pk` / `_fk` column naming conventions — it does not read database constraints. Review the diagram for accuracy, especially on tables with non-standard naming.

## Output

This command creates:
- `.wire/releases/[release]/artifacts/droughty/[schema].dbml`
- Updated `droughty.dbml` block in `status.md`

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
