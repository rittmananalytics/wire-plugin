---
wire_schema: "1.0"
command: generate
artifact: orchestration_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
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
