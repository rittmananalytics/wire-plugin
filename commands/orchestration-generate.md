---
description: Generate orchestration layer (Dagster or dbt Cloud)
argument-hint: <project-folder>
---

# Generate orchestration layer (Dagster or dbt Cloud)

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.9\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"orchestration-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.9\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate orchestration layer — choose Dagster or dbt Cloud to schedule and run the data pipeline
argument-hint: <project-folder>
---

# Orchestration Generate Command

## Purpose

Generate the orchestration layer for the data platform. This step determines how dbt models and data pipeline code are scheduled and executed in production. Supports two approaches:

- **Dagster** — open-source, Python-native, assets-first orchestrator; wraps dbt models as Dagster assets and ingestion scripts as software-defined assets
- **dbt Cloud** — managed service for scheduling dbt jobs; simpler setup, best when the project is dbt-only or already committed to dbt Cloud

## Prerequisites

**Required artifacts (must be approved)**:
- `pipeline_design` — defines run cadences, source systems, and data flow
- `dbt_warehouse` (or `dbt`) — dbt models must exist before orchestration can reference them

**Optional**:
- `pipeline` — if Dagster is chosen, pipeline ingestion code is wrapped as Dagster assets

## Workflow

### Step 1: Read Inputs

1. Read `.wire/<project_id>/design/pipeline_design.md` and extract:
   - Source systems and ingestion approach (batch, streaming, API)
   - Run cadences (daily, hourly, event-driven, etc.)
   - Data dependencies between pipeline stages
   - Any stated orchestration preferences or constraints
2. Read `.wire/<project_id>/status.md`:
   - Check `artifacts.orchestration.orchestration_tool` — if already set (from a previous run or project creation), use it and skip Step 2
   - Note `project_type` to understand scope
3. Locate the dbt project root (search for `dbt_project.yml` in the repository)

### Step 2: Choose Orchestration Tool

If `orchestration_tool` is not already set in status.md, ask the user:

```
Which orchestration tool should be used for this project?

1. Dagster — Python-native orchestrator, wraps dbt + pipeline code as software-defined assets.
   Best for: projects with custom ingestion code, complex dependencies, or teams already using Python.

2. dbt Cloud — Managed dbt scheduling service. No additional infrastructure required.
   Best for: dbt-only or dbt-heavy projects where the team already uses dbt Cloud, or wants minimal ops overhead.
```

Wait for the user's selection. Store the choice:
1. Write `orchestration_tool: "dagster"` or `orchestration_tool: "dbt_cloud"` into the `artifacts.orchestration` section of status.md immediately, before generating any files.

### Step 3a: Generate Dagster Orchestration (if Dagster chosen)

Load the Dagster skill from `skills/dagster/SKILL.md` for Dagster-specific patterns and conventions.

#### 3a.1 — Scaffold Dagster project

If no `dagster_orchestration/` directory exists at the repo root, scaffold it:

```bash
uvx create-dagster project dagster_orchestration
```

This creates:
```
dagster_orchestration/
├── dagster_orchestration/
│   ├── __init__.py
│   ├── assets/
│   ├── resources/
│   └── schedules/
├── dagster_orchestration_tests/
├── pyproject.toml
└── dagster.yaml
```

If a `dagster_orchestration/` directory already exists, skip scaffolding and work within it.

#### 3a.2 — Add dagster-dbt integration

Add `dagster-dbt` to the project dependencies:

```bash
cd dagster_orchestration
uv add dagster-dbt
```

Create a `DbtProjectComponent` YAML configuration. Locate the dbt project root (directory containing `dbt_project.yml`) and create:

**`dagster_orchestration/dagster_orchestration/components/dbt_project.yaml`**:
```yaml
type: dagster_dbt.DbtProjectComponent

params:
  dbt_project_dir: ../../  # relative path to dbt project root
  select: "*"
  exclude: ""
  node_info_to_asset_check_specs:
    - data_tests: true
      model_schema_checks: true
```

This automatically generates one Dagster asset per dbt model, preserving the dbt dependency graph.

#### 3a.3 — Generate source ingestion assets

For each source system identified in `pipeline_design.md`, generate a Dagster asset definition in `dagster_orchestration/dagster_orchestration/assets/`:

**Pattern for each source** (`assets/<source_name>_ingestion.py`):

```python
import dagster as dg
from dagster import asset, AssetExecutionContext


@dg.asset(
    group_name="<source_group>",
    description="Ingest <source_name> data from <source_description>",
    compute_kind="python",
    tags={"layer": "ingestion", "source": "<source_name>"},
)
def <source_name>_raw(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Ingest raw <source_name> data.

    Source: <source_system>
    Cadence: <run_cadence>
    Target: <target_table>
    """
    # TODO: Implement ingestion logic
    # Reference: development/pipeline/ for existing pipeline code
    context.log.info("Ingesting <source_name> data")

    return dg.MaterializeResult(
        metadata={
            "cadence": dg.MetadataValue.text("<run_cadence>"),
            "source": dg.MetadataValue.text("<source_system>"),
        }
    )
```

Use the pipeline design's source system list to generate one asset per source. If `pipeline/` code already exists, reference it from the asset rather than duplicating logic.

#### 3a.4 — Generate schedules and sensors

For each distinct run cadence in the pipeline design, generate a schedule in `dagster_orchestration/dagster_orchestration/schedules/`:

**`schedules/pipeline_schedules.py`**:
```python
import dagster as dg
from dagster import ScheduleDefinition, define_asset_job, AssetSelection

# Job: all ingestion + dbt assets
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Full pipeline: ingestion → dbt staging → integration → warehouse",
)

# Schedule: <primary cadence from pipeline_design>
<cadence_name>_schedule = ScheduleDefinition(
    name="<cadence_name>_schedule",
    cron_schedule="<cron_expression>",
    job=full_pipeline_job,
    execution_timezone="<timezone>",  # from pipeline_design or default UTC
    default_status=dg.DefaultScheduleStatus.RUNNING,
)
```

For any event-driven triggers identified in pipeline_design (e.g. "run when new files arrive"), generate an asset sensor instead:

```python
@dg.asset_sensor(asset_key=dg.AssetKey("<upstream_asset>"), job=full_pipeline_job)
def <trigger_name>_sensor(context: dg.SensorEvaluationContext, asset_event):
    yield dg.RunRequest(run_key=context.cursor)
```

#### 3a.5 — Update `__init__.py`

Ensure all assets, schedules, and sensors are imported and registered in `dagster_orchestration/__init__.py`:

```python
import dagster as dg
from dagster_orchestration.assets import *
from dagster_orchestration.schedules.pipeline_schedules import *

defs = dg.Definitions(
    assets=dg.load_assets_from_modules([assets]),
    schedules=[<schedule_list>],
    sensors=[<sensor_list>],
)
```

#### 3a.6 — Generate setup documentation

Write `.wire/<project_id>/development/orchestration/dagster_setup.md`:

```markdown
# Dagster Orchestration Setup

**Project**: <project_name>
**Generated**: <date>
**Approach**: Dagster software-defined assets

## Overview

[Summary of the orchestration approach based on pipeline_design]

## Project Structure

[dagster_orchestration/ directory tree]

## Assets

| Asset | Group | Cadence | Description |
|-------|-------|---------|-------------|
[one row per generated asset]

## Schedules

| Schedule | Cron | Timezone | Assets |
|----------|------|----------|--------|
[one row per schedule]

## Local Development

```bash
cd dagster_orchestration
uv sync
dg dev                    # Start Dagster UI at http://localhost:3000
dg launch --assets "*"    # Materialize all assets
```

## Production Deployment

[Deployment notes based on project infrastructure from pipeline_design]
```

### Step 3b: Generate dbt Cloud Orchestration (if dbt Cloud chosen)

#### 3b.1 — Read pipeline design for run cadences

Extract from `pipeline_design.md`:
- Number of distinct run cadences (e.g. hourly refresh, daily full load)
- Source systems (to determine if custom steps needed beyond dbt)
- Environment names (dev, staging, prod)

#### 3b.2 — Generate environment configurations

Write `.wire/<project_id>/development/orchestration/dbt_cloud_config.md`:

```markdown
# dbt Cloud Configuration

**Project**: <project_name>
**Generated**: <date>

## Environments

### Development
- Connection: <warehouse_type> (dev credentials)
- Target schema: <project_name>_dev
- dbt version: 1.8+
- Threads: 4

### Production
- Connection: <warehouse_type> (prod service account)
- Target schema: <project_name>_prod
- dbt version: 1.8+
- Threads: 8

## Jobs

<for each cadence from pipeline_design>

### Job: <cadence_name> Refresh
- Environment: Production
- Commands:
  - `dbt source freshness`
  - `dbt run --select <scope>`
  - `dbt test --select <scope>`
- Schedule: <cron_expression>  (<human cadence>)
- Notifications: on failure → [team email / Slack channel]

### Job: CI — Pull Request
- Environment: Development
- Trigger: Pull request opened/updated
- Commands:
  - `dbt run --select state:modified+`
  - `dbt test --select state:modified+`
- Run on: slim CI (uses defer to production state)

## API Configuration (Terraform / IaC)

If managing dbt Cloud via Terraform (`dbt Cloud provider`):

```hcl
resource "dbtcloud_environment" "production" {
  name           = "Production"
  project_id     = var.dbt_cloud_project_id
  dbt_version    = "1.8.0-latest"
  type           = "deployment"
  credential_id  = dbtcloud_bigquery_credential.prod.credential_id
}

resource "dbtcloud_job" "<job_name>" {
  name           = "<cadence_name> Refresh"
  project_id     = var.dbt_cloud_project_id
  environment_id = dbtcloud_environment.production.id
  execute_steps  = ["dbt run", "dbt test"]
  schedule_type  = "cron"
  cron_schedule  = "<cron_expression>"
  num_threads    = 8
}
```
```

#### 3b.3 — Generate .env template

Write `.wire/<project_id>/development/orchestration/dbt_cloud.env.template`:

```
DBT_CLOUD_ACCOUNT_ID=
DBT_CLOUD_PROJECT_ID=
DBT_CLOUD_TOKEN=
DBT_CLOUD_ENVIRONMENT_ID_PROD=
DBT_CLOUD_ENVIRONMENT_ID_DEV=
```

### Step 4: Update Status

Read `.wire/<project_id>/status.md` and update the `orchestration` artifact section:

```yaml
orchestration:
  orchestration_tool: "dagster"  # or "dbt_cloud"
  generate: complete
  validate: not_started
  review: not_started
  generated_date: <today>
  generated_files:
    - development/orchestration/dagster_setup.md   # or dbt_cloud_config.md
    - dagster_orchestration/  # (Dagster only)
  revision_history:
    - date: <today>
      action: generate
      notes: "Initial orchestration scaffold using <tool>"
```

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `orchestration`
- Action: `generate`
- Status: `complete`

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `orchestration`
- `artifact_name`: `Orchestration Layer`
- `file_path`: `.wire/releases/[release_folder]/dev/orchestration.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 7: Confirm and Suggest Next Steps

```
## Orchestration Generated Successfully

**Tool**: <Dagster | dbt Cloud>
**Generated files**:
  [list files]

### Next Steps

1. **Validate orchestration**: `/wire:orchestration:validate <project>`
   - Dagster: runs `dg check defs` and verifies all dbt models have corresponding assets
   - dbt Cloud: validates job configs reference correct environments and model selectors

2. Review and customise generated asset/job definitions to match your infrastructure

3. After validation, review with the team: `/wire:orchestration:review <project>`
```

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

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
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

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
