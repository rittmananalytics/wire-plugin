---
description: Validate ingestion migration runbook
argument-hint: <release-folder>
---

# Validate ingestion migration runbook

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
description: Validate ingestion migration — MCP-executed connectors or runbook
---

# Ingestion Migration — Validate

## Validation Checks

Read `status.md` to determine `method: mcp_executed | runbook_generated` before running checks. Also read the ingestion audit to identify which MCP server prefix applies (Fivetran → `mcp__fivetran__`, Airbyte → `mcp__airbyte__`, etc.) — use the correct prefix for all MCP calls below.

### MCP-executed path

**Check 1 — All in-scope connectors created**
For each connector with `include_in_migration: true` in the ingestion audit, use the ingestion tool's MCP list call (e.g. `mcp__fivetran__list_connections_in_group`, `mcp__airbyte__list_connections`) on the target destination and confirm a matching new connector exists.
PASS/FAIL with missing connectors listed.

**Check 2 — Connectors reached connected/active state**
Use the MCP server's state/status call (e.g. `mcp__fivetran__get_connection_state`, `mcp__airbyte__get_connection`) for each migrated connector. All should show `connected` or `active` (or `syncing` for an in-progress initial sync). Any in a broken or unconfigured state are flagged.
PASS/FAIL with broken connectors listed.

**Check 3 — Source connectors still active**
Use the MCP state call for each source connector. All should still be active — none paused or deleted.
PASS/FAIL.

**Check 4 — Schema mapping correct**
For each new connector, confirm the schema / schema prefix matches the expected target schema from the ingestion audit destination mapping.
PASS/FAIL with mismatches listed.

**Check 5 — Source deactivation deferred to cutover**
Confirm no source connectors were paused or deleted during migration.
PASS/FAIL.

### Runbook fallback path

**Check 1 — All in-scope connectors in runbook**
The count of connectors in the runbook matches the count of `include_in_migration: true` connectors in the ingestion audit.
PASS/FAIL.

**Check 2 — Each connector has destination mapping**
Every connector step includes the source destination schema and its target platform equivalent.
PASS/FAIL with gaps.

**Check 3 — All connector steps describe new connector creation (not destination editing)**
No connector step instructs the user to edit or re-point an existing connector's destination.
PASS/FAIL.

**Check 4 — High-complexity connectors have expanded diagnostic sections**
Every High-complexity connector has a diagnostic section in the runbook.
PASS/FAIL.

**Check 5 — Credential rotation checklist present**
The runbook includes a credential rotation section listing all service accounts and API keys.
PASS/FAIL.

**Check 6 — Source deactivation deferred to cutover**
The runbook explicitly notes that source connectors are NOT deactivated during ingestion migration — only during the cutover phase.
PASS: Note present.
FAIL: Deactivation steps found in ingestion runbook (should be moved to cutover).

**Check 7 — Post-migration validation steps present**
The runbook includes equivalency check steps to run after each connector's initial sync completes.
PASS/FAIL.

### Update status

```yaml
artifacts:
  ingestion_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_migration` as artifact_id, `Ingestion Migration` as artifact_name, and the `file` value from `artifacts.ingestion_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_migration` as artifact, `validate` as action.

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
