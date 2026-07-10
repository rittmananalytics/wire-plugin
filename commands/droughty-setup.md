---
description: Install Droughty, generate profile.yaml and droughty_project.yaml
argument-hint: <release-folder> [--force]
---

# Install Droughty, generate profile.yaml and droughty_project.yaml

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
description: Install Droughty at the pinned version and generate profile.yaml + droughty_project.yaml from Wire context
argument-hint: <release-folder>
---

# Droughty Setup Command

## Purpose

One-time setup for Droughty in a Wire engagement. Installs the pinned Droughty version, generates `profile.yaml` from Wire context (deriving credentials from MCP config where available), generates `droughty_project.yaml` with output paths aligned to Wire's artifact structure, verifies warehouse connectivity, and records setup state in `status.md`.

Run this before any other `/wire:droughty-*` command.

## Usage

```bash
/wire:droughty-setup <release-folder>
```

Pass `--force` to re-run setup even if already complete (e.g. after a version refresh or credential change).

## Prerequisites

- `.wire/engagement/context.md` exists
- BigQuery Application Default Credentials configured (`gcloud auth application-default login`) **or** Snowflake credentials available
- Python >= 3.9, < 3.12.4 on PATH
- For `droughty docs` and `droughty qa`: an OpenAI API key

## Workflow

### Step 1: Read Wire Context

1. Read `.wire/engagement/context.md` — extract `client_name`, `engagement_name`
2. Read `.wire/releases/<release>/status.md` — check `droughty.setup.status`
3. If `droughty.setup.status == complete` and `--force` was not passed:
   ```
   Droughty is already configured for this release.
   Run with --force to overwrite the existing setup.
   ```
   Stop here.

### Step 2: Locate Pinned Version

1. Check for `wire/droughty/pinned_version.txt` in the repo root (dev mode)
2. If not found, check `~/.claude/plugins/wire/droughty/pinned_version.txt` (plugin mode)
3. If neither found, default to the latest published version and warn:
   ```
   ⚠️  pinned_version.txt not found — installing latest Droughty. Pin a version by creating wire/droughty/pinned_version.txt.
   ```

Read `PINNED_VERSION` from the file.

### Step 3: Install Droughty

Check if the correct version is already installed:
```bash
pip show droughty 2>/dev/null | grep "^Version:" | awk '{print $2}'
```

If not installed or wrong version:
```bash
pip install "droughty==[PINNED_VERSION]"
```

If the install fails, surface the error verbatim and stop. Common causes:
- Python version outside 3.9–3.12.3 range
- No internet access or pip not available

### Step 4: Determine Warehouse Type

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Which warehouse should Droughty connect to?",
    "header": "Warehouse",
    "options": [
      {"label": "BigQuery", "description": "Google BigQuery — uses Application Default Credentials or a service account key"},
      {"label": "Snowflake", "description": "Snowflake — requires account ID, username, password, and warehouse name"}
    ],
    "multiSelect": false
  }]
}
```

Store `warehouse_type` as `bigquery` or `snowflake`.

### Step 5: Generate profile.yaml

Profile name: `[engagement_name]` (snake_case, from `context.md`).

Check whether `~/.droughty/profile.yaml` already exists with a profile of that name. If it does, ask:
```
A Droughty profile named '[engagement_name]' already exists. Overwrite it? (yes/no)
```

**For BigQuery:**

Check for existing ADC:
```bash
gcloud auth application-default print-access-token 2>/dev/null | head -c 10
```

If ADC is present, note it in the output. Ask directly in chat (one at a time):

1. "GCP project ID (e.g. `acme-analytics-prod`):"
2. "Default dataset name (e.g. `analytics`):"
3. "Which datasets/schemas should Droughty scan? List all that are in scope, comma-separated (e.g. `analytics,staging,raw`):"
4. "OpenAI API key? (required for `/wire:droughty-docs` and `/wire:droughty-qa` — press Enter to skip for now):"

Write `~/.droughty/profile.yaml` (append or create):

```yaml
[engagement_name]:
  type: bigquery
  project: [gcp_project_id]
  dataset: [dataset]
  schemas:
    - [schema1]
    - [schema2]
  openai_api_key: [openai_key]   # present only if provided
```

**For Snowflake:**

Ask directly in chat (one at a time):

1. "Snowflake account identifier (e.g. `xy12345.us-east-1`):"
2. "Username:"
3. "Password:"
4. "Virtual warehouse name (e.g. `COMPUTE_WH`):"
5. "Database name:"
6. "Default schema:"
7. "Role (e.g. `ANALYST` — press Enter to use default role):"
8. "Which schemas should Droughty scan? Comma-separated (e.g. `PUBLIC,STAGING`):"
9. "OpenAI API key? (required for `/wire:droughty-docs` and `/wire:droughty-qa` — press Enter to skip):"

Write `~/.droughty/profile.yaml`:

```yaml
[engagement_name]:
  type: snowflake
  account: [account_id]
  username: [username]
  password: [password]
  warehouse: [warehouse_name]
  database: [database]
  schema: [schema]
  role: [role]   # omit if not provided
  schemas:
    - [schema1]
    - [schema2]
  openai_api_key: [openai_key]   # present only if provided
```

### Step 6: Generate droughty_project.yaml

Ask in chat:

```
Where is your LookML project directory? (e.g. ./lookml — press Enter to skip if not using Looker)
```

```
Where is your dbt project directory? (default: ./ — press Enter for default)
```

Store `lookml_project_path` (or null) and `dbt_project_path`.

Create artifact directories:
```bash
mkdir -p .wire/releases/[release]/artifacts/droughty
mkdir -p .wire/releases/[release]/artifacts/droughty/field_descriptions
```

Write `droughty_project.yaml` at the git root:

```yaml
profile_name: [engagement_name]

# Output paths — Wire artifact structure
dbml_path: .wire/releases/[release]/artifacts/droughty/
field_description_path: .wire/releases/[release]/artifacts/droughty/field_descriptions/

# dbt output (if dbt project present)
dbt_path: [dbt_project_path]/models/
stage_path: [dbt_project_path]/models/staging/

# LookML output (if LookML project present)
# Droughty-generated base views land in views/generated/
# Wire-extended explores and refinements go in views/extended/
lookml_path: [lookml_project_path]/views/generated/
```

If `lookml_project_path` is null, omit the `lookml_path` line.

### Step 7: Verify Connectivity

Run a lightweight test to confirm warehouse access:

```bash
droughty dbml --profile-dir ~/.droughty --project-dir . 2>&1 | head -20
```

Interpret the result:
- If it produces output or a file, connectivity is confirmed. Extract table count from output if available.
- If it fails with an authentication error, surface the error and suggest credential fixes.
- If it connects but finds no tables, warn:
  ```
  ⚠️  Connected to [warehouse] but found no tables in: [schemas]

  If dbt models have not been deployed yet, run dbt first, then re-run this command.
  Check that the schemas listed in profile.yaml match what is in the warehouse.
  ```
  Do not treat this as a failure — setup is still complete.

### Step 8: Update status.md

Update in `.wire/releases/[release]/status.md`:

```yaml
droughty:
  setup:
    status: complete
    pinned_version: "[PINNED_VERSION]"
    warehouse: "[bigquery|snowflake]"
    profile_name: "[engagement_name]"
    schemas: [[list of schemas]]
    lookml_output_path: "[lookml_project_path]/views/generated/"   # or null
    dbt_project_path: "[dbt_project_path]"
    completed_date: "[today]"
```

### Step 9: Confirm and Guide Next Steps

```
## Droughty Setup Complete ✅

**Version**: [PINNED_VERSION]
**Warehouse**: [warehouse_type]
**Profile**: [engagement_name]
**Schemas in scope**: [comma-separated list]
**Artifact output**: .wire/releases/[release]/artifacts/droughty/

### Next Steps

Discovery commands (any warehouse, any time):

  /wire:droughty-introspect [release]   — Schema inventory report (tables, columns, PK/FK coverage)
  /wire:droughty-dbml [release]         — DBML entity-relationship diagram
  /wire:droughty-docs [release]         — AI-generated field descriptions
  /wire:droughty-qa [release]           — Data quality validation report

Post-dbt deploy commands (run after dbt models are deployed):

  /wire:droughty-dbt-tests [release]    — Pattern-based schema tests for deployed tables
  /wire:droughty-stage [release]        — Staging SQL + sources.yml (BigQuery)
  /wire:droughty-lookml [release]       — Base LookML views from dbt-created tables

Or run everything in sequence:
  /wire:droughty-generate [release]
```

## Refreshing the Pinned Version

Wire repo owners can update the pin to the latest published Droughty release with the bundled refresh script:

```bash
bash wire/droughty/refresh_version.sh
# or, to also commit the change automatically:
bash wire/droughty/refresh_version.sh --commit
```

The script queries PyPI, updates `wire/droughty/pinned_version.txt`, and prints the commit command. Once pushed, all subsequent `/wire:droughty-setup` runs install the new version.

Consultants on existing engagements should re-run `/wire:droughty-setup --force` after pulling the updated repo.

## Output

This command creates or updates:
- `~/.droughty/profile.yaml` (warehouse credentials — not committed to git)
- `droughty_project.yaml` at the git root
- `.wire/releases/[release]/artifacts/droughty/` artifact directory
- `droughty.setup` block in `.wire/releases/[release]/status.md`

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
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
