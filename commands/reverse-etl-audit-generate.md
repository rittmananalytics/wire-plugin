---
description: Catalog Hightouch reverse ETL syncs, models, and destinations
argument-hint: <release-folder>
---

# Catalog Hightouch reverse ETL syncs, models, and destinations

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
description: Catalog all Hightouch reverse ETL syncs, models, and destinations with migration approach and warehouse dependency mapping
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: reverse_etl_audit` and `artifact_file_path: audit/reverse_etl_audit.md` before proceeding.

---

# Reverse ETL Audit — Generate

## Purpose

Catalogs every active reverse ETL sync in the Hightouch workspace, capturing the warehouse models each sync reads from, the SaaS destinations each sync writes to, and the migration approach for each sync given the planned warehouse move. The output maps warehouse-to-sync dependencies so the migration inventory can sequence cutover correctly — syncs cannot be re-pointed until their source warehouse objects exist on the target.

Supports Hightouch as the first reverse ETL tool. Future tools (Census, Polytomic) follow the same output shape but use tool-specific API branches.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- `migration.reverse_etl_tool: hightouch` set in `status.md`
- One of the following data sources (in priority order):
  1. `HIGHTOUCH_TOKEN` environment variable set (read-only API key, see `skills/hightouch/SKILL.md` Step 0)
  2. Hightouch Git config directory at `audit/hightouch_git/` (see `skills/hightouch/SKILL.md` Step 0b)
  3. Pre-exported CSV at `audit/hightouch_syncs_input.csv` as final fallback

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- Hightouch REST API (`https://api.hightouch.com/api/v1`) or CSV fallback
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md` (if present — cross-reference dbt model dependencies)

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration` in `status.md`. Read `migration.reverse_etl_tool` — if it is not `hightouch` (or another supported tool), stop and output:

```
reverse_etl_tool is not set or is not a supported value.
Set migration.reverse_etl_tool: hightouch in status.md and re-run.
```

Activate the `hightouch` skill (`skills/hightouch/SKILL.md`) for API connection details and object hierarchy.

If the audit file already exists at `audit/reverse_etl_audit.md`, ask whether to re-generate (overwrite) or update (append new syncs only).

### Step 2: Connect to Hightouch

Check data sources in priority order.

**Option 1 — Hightouch API**:
Attempt to reach the API (Step 0 of the `hightouch` skill). Set a 10-second timeout. If it responds HTTP 200, enumerate the full workspace following `hightouch` skill Step 2: sources → models → destinations → syncs → recent run history. Set `data_source: hightouch_api` and proceed to Step 3.

**Option 2 — Git repository**:
If the API is unreachable or `HIGHTOUCH_TOKEN` is unset, check for `audit/hightouch_git/`. If the directory exists and contains at least a `syncs/` subdirectory, use it as the source. Follow `skills/hightouch/SKILL.md` Step 0b to parse the YAML files. Set `data_source: git`. Note to the user:

```
Auditing from Hightouch Git config files.
Runtime fields (status, last_run_at, last_run_rows) are not available from Git.
These will be marked n/a in the audit report.
Supply a supplementary CSV at audit/hightouch_syncs_input.csv if you need row
volume estimates or sync status to be included.
```

**Option 3 — CSV fallback**:
If neither API nor Git directory is available, check for `audit/hightouch_syncs_input.csv`. If it exists, proceed with CSV data. Set `data_source: csv`.

If none of the three sources are available, stop and output:

```
No Hightouch data source found. Provide one of:

  1. HIGHTOUCH_TOKEN env var — read-only API key from Hightouch Settings → API keys
  2. audit/hightouch_git/ — copy of the client's Hightouch Git config directory
     (see skills/hightouch/SKILL.md Step 0b for setup instructions)
  3. audit/hightouch_syncs_input.csv — manually exported sync list

Required CSV columns:
  sync_id, sync_name, model_id, model_name, model_type, model_sql_summary,
  destination_id, destination_name, destination_type, sync_mode, schedule_type,
  schedule_value, status, last_run_at, last_run_rows, sync_engine,
  include_in_migration, migration_notes

Then re-run: /wire:reverse-etl-audit-generate $ARGUMENTS
```

### Step 3: Build the sync catalog

For each sync, capture:

| Field | Source (API) | Source (Git) | Source (CSV) |
|---|---|---|---|
| `sync_id` | `syncs[].id` | `syncs/<name>.yaml → id` | CSV column |
| `sync_name` | `syncs[].slug` | `syncs/<name>.yaml → name` | CSV column |
| `model_id` | `syncs[].modelId` | `syncs/<name>.yaml → model_id` | CSV column |
| `model_name` | `models[id].name` | `models/<name>.yaml → name` | CSV column |
| `model_type` | `models[id].queryType` (rawSql / dbtModel / table) | `models/<name>.yaml → query_type` | CSV column |
| `model_sql_summary` | First 200 chars of `models[id].sql`, or dbt model name | Full SQL from `models/<name>.yaml → sql` | CSV column |
| `destination_name` | `destinations[id].name` | `destinations/<name>.yaml → name` | CSV column |
| `destination_type` | `destinations[id].type` | `destinations/<name>.yaml → type` | CSV column |
| `sync_mode` | `syncs[].syncMode` | `syncs/<name>.yaml → sync_mode` | CSV column |
| `schedule_type` | `syncs[].schedule.type` | `syncs/<name>.yaml → schedule.type` | CSV column |
| `schedule_value` | Cron expression or interval in minutes | `syncs/<name>.yaml → schedule.interval` or cron | CSV column |
| `status` | `syncs[].status` | **n/a (git source)** | CSV column |
| `last_run_at` | `syncs[].lastRunAt` | **n/a (git source)** | CSV column |
| `last_run_rows` | `syncRuns[0].plannedRows` | **n/a (git source)** | CSV column |
| `sync_engine` | lightning / basic (infer from config or ask user) | Check `syncs/<name>.yaml` for lightning references; otherwise ask | CSV column |
| `warehouse_objects` | Extracted from model SQL | Extracted from full SQL in Git model file | Derive from `model_sql_summary` |
| `complexity` | Assigned in Step 4 | Assigned in Step 4 | Assigned in Step 4 |
| `migration_approach` | Assigned in Step 4 | Assigned in Step 4 | Assigned in Step 4 |
| `include_in_migration` | true (default) unless disabled >90 days | true (default — status unknown from Git; flag for manual review) | CSV column |
| `migration_notes` | Auto-generated | Auto-generated; note where runtime data is absent | CSV column |

**Warehouse object extraction**: For each `rawSql` model, parse the SQL to extract referenced table and view names (schema-qualified where present). Record as `warehouse_objects` — a comma-separated list. Git files provide the full SQL rather than the 200-character truncated version returned by the API, making this extraction more reliable. If the dbt audit exists, cross-reference `dbtModel` references against the dbt model catalog to confirm the model is in scope for migration.

### Step 4: Classify each sync

Follow `skills/hightouch/SKILL.md` Step 3 to assign complexity (Low / Medium / High) and migration approach:

- `repoint` — model SQL is portable; re-point source connection after warehouse migration
- `rewrite_model` — model SQL uses source-platform dialect; translate before re-pointing
- `rebuild` — Customer Studio audience or Journey; full rebuild required
- `decommission` — disabled or unused; exclude from migration

Default: active syncs with simple rawSql and no dialect-specific functions → `repoint` (Low).

### Step 5: Identify Lightning schema dependencies

If any syncs use the Lightning sync engine, flag that the target warehouse must have the following schemas provisioned before those syncs are enabled:

```sql
CREATE SCHEMA IF NOT EXISTS hightouch_planner;
CREATE SCHEMA IF NOT EXISTS hightouch_audit;
```

List the affected syncs and note that Hightouch provisions these schemas automatically on the first sync run, provided the service account has `CREATE SCHEMA` privilege.

### Step 6: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md`

Use the template at `TEMPLATES/migration/reverse_etl_audit.md`. Include:
- Summary table (total syncs, by destination type, by complexity, by migration approach)
- Full sync catalog table
- Warehouse object dependency map (which warehouse tables/views each sync depends on)
- Lightning engine syncs and schema requirements
- dbt model dependencies (syncs that cannot be re-pointed until a dbt migration batch is complete)
- Excluded / decommission candidates

### Step 7: Update status

```yaml
artifacts:
  reverse_etl_audit:
    generate: complete
    file: audit/reverse_etl_audit.md
    generated_date: "{{TODAY}}"
    tool: hightouch
    sync_count: N
    data_source: "hightouch_api" | "git" | "csv"
    lightning_sync_count: N
    decommission_count: N
```

### Step 8: Output summary

Print: total syncs cataloged, breakdown by complexity and migration approach, Lightning sync count, and next command:

```
/wire:reverse-etl-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_audit` as artifact_id, `Reverse ETL Audit` as artifact_name, and the `file` value from `artifacts.reverse_etl_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_audit` as artifact, `generate` as action.

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
