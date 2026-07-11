---
description: Catalog orchestration jobs, schedules, and dependencies
argument-hint: <release-folder>
---

# Catalog orchestration jobs, schedules, and dependencies

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
description: Catalog orchestration jobs, schedules, and dependencies on the source platform
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: orchestration_audit` and `artifact_file_path: audit/orchestration_audit.md` before proceeding.

---

# Orchestration Audit — Generate

## Purpose

Catalogs every orchestration job, schedule, sensor, and asset dependency on the source orchestration tool. The output drives the orchestration migration runbook and ensures no jobs are lost or misconfigured during platform transition.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- Orchestration tool access (`migration.orchestration_tool` in `status.md`)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — orchestration_tool (dagster / dbt_cloud / airflow / none)

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration`. Read `migration.orchestration_tool`.

If `orchestration_tool: none`, write a minimal audit noting no orchestration is in scope, update status, and output:
```
No orchestration tool configured for this migration — skipping orchestration audit.
Run: /wire:migration-inventory-generate $ARGUMENTS
```

### Step 2: Query the orchestration tool

**If Dagster**:
- List all jobs and their op/asset dependencies
- List all schedules (cron expressions) and sensors
- Identify partitioned assets and their partition definitions
- Note any Dagster Cloud vs OSS differences

**If dbt Cloud**:
- List all jobs: job name, environment, commands, schedule, triggers
- List environments and their target connection profiles
- Note API-triggered jobs vs scheduled jobs
- Capture job dependencies (jobs that trigger other jobs via webhooks or API calls)

**If Airflow**:
- List all DAGs with their schedule intervals
- List tasks per DAG with dependencies (task_id, operator type, upstream/downstream)
- Identify connections and variables used by tasks
- Note any custom operators

For each approach, prefer MCP-based querying if the tool's MCP server is configured. Fall back to asking the user to export a job list if MCP is unavailable.

### Step 3: Classify each job

For each job:

- **Type**: `scheduled`, `sensor_triggered`, `api_triggered`, `manual`
- **Criticality**: `critical` (production data pipeline), `standard` (regular reporting), `low` (ad-hoc / test jobs)
- **Migration approach**:
  - `recreate` — direct equivalent exists on target orchestration tool
  - `translate` — equivalent concept but different syntax/configuration
  - `evaluate` — depends on source-platform-specific features (e.g., BigQuery connection type)
  - `exclude` — dev/test jobs not needed in production

### Step 4: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/orchestration_audit.md`

Use the template at `TEMPLATES/migration/orchestration_audit.md`. Include:
- Job inventory table
- Schedule summary (how many run hourly, daily, weekly, etc.)
- Dependency graph (text-based for complex DAGs)
- Evaluate/exclude flags with reasons
- Connection and credential inventory (names only — not secrets)

### Step 5: Update status

```yaml
artifacts:
  orchestration_audit:
    generate: complete
    file: audit/orchestration_audit.md
    generated_date: "{{TODAY}}"
    job_count: N
    scheduled_job_count: N
    orchestration_tool: "{{TOOL}}"
```

### Step 6: Output next command

```
/wire:orchestration-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/orchestration_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `orchestration_audit` as artifact_id, `Orchestration Audit` as artifact_name, and the `file` value from `artifacts.orchestration_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `orchestration_audit` as artifact, `generate` as action.

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
