---
description: Base LookML views from deployed dbt models
argument-hint: <release-folder>
---

# Base LookML views from deployed dbt models

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.9.1\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"droughty-lookml\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.9.1\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate base LookML views, explores, and measures from deployed dbt table schemas
argument-hint: <release-folder>
---

# Droughty LookML Command

## Purpose

Run `droughty lookml` to generate base LookML views, explores, and measures from the deployed warehouse schema. Droughty reads column names and types, applies naming-convention heuristics (PK/FK suffix detection, date field handling, numeric measure inference), and writes view files to `views/generated/` within the LookML project. These files are the base layer that `/wire:semantic_layer-generate` then extends with business logic, calculated dimensions, and Explores.

**Run after `dbt run`** — Droughty reads the deployed tables. Models must be materialised in the warehouse before LookML generation is meaningful.

## Usage

```bash
/wire:droughty-lookml <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete, with `lookml_output_path` configured
- dbt models deployed to the warehouse
- A LookML project directory exists at the configured path

## Workflow

### Step 1: Confirm dbt Models Are Deployed

```
droughty lookml reads column types from the live warehouse — dbt models must be deployed.

Have you run dbt and confirmed models are materialised? (yes/no)
```

If no, prompt to run dbt first.

### Step 2: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete`
3. Extract `lookml_output_path` (should be `[lookml_project_path]/views/generated/`)
4. If `lookml_output_path` is null (no LookML project configured), stop:
   ```
   Error: No LookML project path was configured during droughty-setup.

   Re-run /wire:droughty-setup [release] and provide the LookML project path when prompted.
   ```

### Step 3: Prepare Output Directory

Ensure the output directory exists:
```bash
mkdir -p [lookml_project_path]/views/generated
mkdir -p [lookml_project_path]/views/extended
```

The `views/extended/` directory is where Wire will write LookML refinements and business logic in the `/wire:semantic_layer-generate` phase. Creating it now makes the convention visible to the consultant immediately.

### Step 4: Run droughty lookml

```bash
droughty lookml \
  --profile-dir ~/.droughty \
  --project-dir .
```

Capture stdout and stderr. Surface errors verbatim.

### Step 5: Verify and Catalogue Output

Read the generated view files. For each file:
- Count dimensions and measures
- Flag any columns where Droughty could not determine a type (will default to `type: string`)
- Note any Period-over-Period parameters generated (if configured in `droughty_project.yaml`)

### Step 6: Check for Existing LookML Conflicts

If `.lookml` or `.view.lkml` files already exist in `views/generated/`:
- If they were previously generated by Droughty (check for Droughty header comment), offer to regenerate (overwrite)
- If they were manually authored, warn:
  ```
  ⚠️  Manually-authored files detected in views/generated/:
  [list of files]

  Droughty will overwrite these. Move them to views/extended/ to preserve them.
  Proceed? (yes/no)
  ```

### Step 7: Update status.md

```yaml
droughty:
  lookml:
    status: complete
    views_generated: [n]
    dimensions_generated: [n]
    measures_generated: [n]
    output_path: "[lookml_project_path]/views/generated/"
    completed_date: [today]
```

### Step 8: Confirm Output and LookML Convention

```
## LookML Base Views Generated ✅

[n] views written to [lookml_project_path]/views/generated/
  Dimensions: [n]
  Measures:   [n]
  Period-over-Period parameters: [n or 'none']

LookML project structure:
  views/
  ├── generated/      ← Droughty output (base views, auto-regenerated)
  │   ├── orders.view.lkml
  │   ├── customers.view.lkml
  │   └── ...
  └── extended/       ← Wire extensions (business logic, explores, refinements)
      (empty — populated by /wire:semantic_layer-generate)

Working convention:
  - Never edit files in views/generated/ by hand — they will be overwritten on next
    /wire:droughty-lookml run. Put all business logic in views/extended/ using
    LookML refinements (view: +view_name { ... }).
  - Droughty generates dimensions from every column. Wire's semantic layer command
    will create Explores and add derived fields, filters, and joins on top.

Next steps:
  /wire:droughty-docs [release]              — Add field descriptions to LookML label/description fields
  /wire:semantic_layer-generate [release]    — Extend base views with business logic and Explores
  /wire:semantic_layer-validate [release]    — Validate against source schema
```

## Output

This command creates:
- `[lookml_project_path]/views/generated/[view_name].view.lkml` — one file per dbt model
- `[lookml_project_path]/views/extended/` — empty placeholder directory for Wire extensions
- Updated `droughty.lookml` block in `status.md`

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
