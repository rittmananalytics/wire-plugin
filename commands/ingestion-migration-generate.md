---
description: Generate Fivetran connector migration runbook
argument-hint: <release-folder>
---

# Generate Fivetran connector migration runbook

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.9.7\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ingestion-migration-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.9.7\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Execute ingestion connector migration via MCP server, or generate runbook if MCP unavailable
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

Follow `specs/utils/stale_artifact_check.md` with `artifact_id: ingestion_migration` and `artifact_file_path: migration/ingestion_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before creating any connectors, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT modify, re-point, or delete any existing source connectors.
  Create new connectors pointing at the TARGET destination only.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not create connectors pointing to these):
  [list each production project ID]
```

If a tool call would modify an existing source connector, or create a connector pointing to a production project listed in `data_safety.production_projects`, stop immediately and report the conflict before proceeding.

---

# Ingestion Migration — Generate

## Purpose

Migrates every in-scope connector from the source ingestion platform to the target platform destination. When the relevant ingestion tool's MCP server is available, Wire executes the migration directly — creating new connectors and generating setup/connect card URLs for the user to enter credentials. A runbook is generated as a fallback only when no MCP server is reachable.

**Default behaviour**: always create new connectors for the target destination. Never edit or re-point an existing connector's destination — that risks interrupting the source pipeline during the parallel-run window.

## Ingestion tool connectivity map

A project may use multiple ingestion tools simultaneously. Each tool has its own connectivity method — MCP server, direct API call, or runbook-only. This table covers all tools the ingestion audit can surface:

| Ingestion tool | Connectivity method | Key probe | Fallback |
|---|---|---|---|
| Fivetran | MCP — `mcp__fivetran__` | `mcp__fivetran__get_account_info` | Runbook |
| RudderStack | MCP — `mcp__plugin_wire_rudderstack__` | `mcp__plugin_wire_rudderstack__user_details` | Runbook |
| Coupler.io | MCP — `mcp__claude_ai_Coupler_io__` | `mcp__claude_ai_Coupler_io__list-dataflows` | Runbook |
| Airbyte | API — `AIRBYTE_TOKEN` + `AIRBYTE_BASE` env vars | `GET $AIRBYTE_BASE/workspaces` | Runbook |
| Segment | API — `SEGMENT_TOKEN` + `SEGMENT_BASE` env vars | `GET $SEGMENT_BASE/sources` | Runbook |
| Stitch | *(no MCP or API — runbook only)* | — | Runbook |
| Custom / other | Check available MCP tools for a matching prefix | — | Runbook |

Handle each tool group separately. Never mix-apply one tool's MCP server to another tool's connectors.

## Prerequisites

- `target_setup review: approved`
- Target warehouse schemas exist (target_setup scripts executed)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`

## Workflow

### Step 1: Confirm prerequisites

Confirm `target_setup review: approved`. If not, stop with message.

### Step 2: Pre-flight — identify all in-scope tools and check connectivity

Read `ingestion_audit.md`. Collect every distinct `service_type` or `ingestion_tool` that has at least one connector with `include_in_migration: true`. This is the in-scope tool list for this run.

For each tool in the in-scope list, determine its connectivity status using the table above:

- **MCP tools** (Fivetran, RudderStack, Coupler.io): run the key probe call with a 10-second timeout. Interpret the result:
  - Probe succeeds → `CONNECTED — will execute via MCP`
  - Auth error (401/403) → `AUTH REQUIRED — re-authenticate via /mcp before proceeding`
  - Timeout or tool unavailable → `NOT CONFIGURED — will fall back to runbook`
- **API tools** (Airbyte, Segment): check whether the required env vars are set (`AIRBYTE_TOKEN`/`AIRBYTE_BASE` or `SEGMENT_TOKEN`/`SEGMENT_BASE`). If set, attempt a lightweight API call. Interpret:
  - Call succeeds → `CONNECTED — will execute via API`
  - 401 / missing env var → `NOT CONFIGURED — will fall back to runbook`
- **Runbook-only tools** (Stitch, custom/other): mark as `RUNBOOK ONLY` without probing.

Output the pre-flight table before starting any migration work:

```
Ingestion Pre-flight Check
════════════════════════════════════════════════════════════════

  Tool          Connectors in scope   Connectivity              Migration path
  ──────────    ───────────────────   ──────────────────────    ──────────────
  Fivetran      18                    ✅ Connected (MCP)         Direct execution
  RudderStack   4                     ✅ Connected (MCP)         Direct execution
  Coupler.io    2                     ⚠️  Auth required (MCP)    Blocked — re-auth first
  Segment       3                     ❌ Not configured (API)    Runbook fallback

Total in scope: 27 connectors
MCP/API executable: 22   Runbook fallback: 5   Blocked: 2
```

If any tool shows `AUTH REQUIRED`, stop and instruct the user to re-authenticate that tool (run `/mcp` in Claude Code and re-authenticate, or re-set the env var). Do not proceed past this step until no tool is in a blocked state.

Once all tools are either CONNECTED or RUNBOOK fallback (none blocked), output:

```
Pre-flight complete. Proceeding with migration.
  Direct execution: [tools]
  Runbook fallback: [tools]
```

Then continue to Step 3 for each CONNECTED tool and Step 4 for each fallback tool.

### Step 3: MCP-driven migration (primary path)

For each connector in the ingestion audit with `include_in_migration: true` where an MCP server is available, working in order of ascending complexity (Low first):

1. **Identify the target destination**: use the MCP server's list/group call (e.g. `mcp__fivetran__list_groups`, `mcp__airbyte__list_destinations`) to find the destination that corresponds to the target warehouse, as named in the target setup.

2. **Create a new connector**: call the MCP server's create connection tool (e.g. `mcp__fivetran__create_connection`, `mcp__airbyte__create_connection`) with:
   - The same service/connector type as the source connector
   - The target destination identifier
   - Schema / schema prefix matching the source connector (as mapped in the ingestion audit)
   - Do **not** modify or re-point the source connector — it stays active for the parallel run

3. **Generate a setup link**: call the MCP server's connect card or setup URL tool (e.g. `mcp__fivetran__create_connect_card`). Record the returned URL. For tools without a connect card API, use whatever credential-entry URL the MCP server provides.

4. **Present the setup URL** to the user immediately with clear instructions: "Open this link to enter credentials for `<connector_name>`. Once saved, the initial sync will start automatically."

5. **Track completion**: after the user confirms credentials entered (or after a reasonable wait), call the MCP server's connection state tool to confirm the connector reaches `connected` / `active` state. Note the result.

6. **Credential rotation checklist**: for this connector, note:
   - Service accounts or API keys that need new target-platform credentials
   - IP allowlists that need updating for the target platform

For High-complexity connectors: add a note listing common failure modes and resolution steps specific to that connector type.

Write a per-connector status summary as each one completes.

### Step 4: Runbook fallback (MCP unavailable)

If no MCP server is reachable for a given set of connectors, generate a step-by-step runbook for those connectors.

**Output location**: `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md`

For each connector with `include_in_migration: true`:

1. **Identify destination mapping**: map the source destination schema to its target platform equivalent (from the target setup DDL)
2. **Connector steps**: always document **new connector creation** steps — never "edit destination" on the existing connector
3. **Activation steps**: source connector stays active; new target connector is created, activated, synced, and equivalency-checked
4. **Credential rotation**: list service accounts, API keys, and IP allowlist changes needed

For High-complexity connectors: include an expanded diagnostic section with common failure modes.

Structure:
1. Pre-flight checklist
2. Per-connector migration steps (Low complexity first)
3. Credential rotation checklist
4. Post-migration validation steps
5. Source connector deactivation procedure (deferred to cutover phase)

### Step 5: Update status

```yaml
artifacts:
  ingestion_migration:
    generate: complete
    method: mcp_executed | runbook_generated
    file: migration/ingestion_migration_runbook.md   # runbook path only; omit for MCP path
    generated_date: "{{TODAY}}"
    connectors_migrated: N
    connectors_pending_credentials: N   # connectors with connect card URL not yet confirmed
```

### Step 6: Output next command

```
/wire:ingestion-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md` (runbook fallback only)
- Per-connector connect card URLs and status summary (MCP path, printed to console)
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact_id, `Ingestion Migration` as artifact_name, and the `file` value from `artifacts.ingestion_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_migration` as artifact, `generate` as action.

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
