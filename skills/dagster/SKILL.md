---
name: dagster
description: Proactive skill for building Dagster orchestration layers. Auto-activates when creating or modifying Dagster assets, schedules, sensors, or components, or when working on the orchestration artifact in a Wire project. Covers the assets-first pattern, dagster-dbt integration, automation (schedules, sensors, declarative automation), the component framework, and CLI usage (dg dev, dg launch, dg check, dg scaffold).
---

# Dagster Skill

## Purpose

This skill activates when working with Dagster to ensure correct patterns, avoid common anti-patterns, and produce production-quality orchestration code. It is tailored for Wire projects where Dagster orchestrates dbt-based data pipelines.

## When This Skill Activates

### User-Triggered Activation

- Creating Dagster asset definitions, schedules, sensors, or jobs
- Scaffolding a Dagster project or component
- Integrating Dagster with dbt (`dagster-dbt`)
- Questions about Dagster CLI (`dg dev`, `dg launch`, `dg check`, `dg scaffold`)
- Debugging asset materialisation failures
- Designing partition strategies for incremental models
- Setting up declarative automation or asset sensors

**Keywords**: "dagster", "dg dev", "dg launch", "@asset", "@multi_asset", "materialize", "MaterializeResult", "dagster-dbt", "DbtProjectComponent", "ScheduleDefinition", "SensorDefinition", "AutomationCondition", "dg scaffold", "software-defined assets", "asset graph"

### Self-Triggered Activation (Proactive)

Activate before generating any Dagster code when:
- The user asks to set up orchestration for a Wire project
- You detect `dagster.yaml`, `dagster_orchestration/`, or imports of `dagster` in Python files
- The orchestration artifact in status.md shows `orchestration_tool: dagster`

---

## Core Patterns

### NEVER answer Dagster questions from memory — always use these patterns

### Asset definition

Always use the `@dg.asset` decorator. Prefer the `dg.` namespace prefix:

```python
import dagster as dg

@dg.asset(
    group_name="ingestion",
    description="Brief description of what this asset produces",
    compute_kind="python",   # or "dbt", "sql", "spark"
    tags={"layer": "ingestion", "source": "salesforce"},
)
def salesforce_contacts(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    context.log.info("Running salesforce_contacts ingestion")
    # ... logic ...
    return dg.MaterializeResult(
        metadata={"row_count": dg.MetadataValue.int(rows_written)}
    )
```

**Anti-patterns to avoid:**
- ❌ `@asset` without `dg.` prefix (old style)
- ❌ Raising exceptions for expected "nothing to do" cases — use `SkipReason` in sensors, `MaterializeResult` with metadata in assets
- ❌ `print()` instead of `context.log.info()`
- ❌ Hardcoded credentials in asset code — always use `EnvVar` in resources

### Multi-asset (multiple outputs from one computation)

```python
@dg.multi_asset(
    specs=[
        dg.AssetSpec("orders_raw", group_name="ingestion"),
        dg.AssetSpec("order_items_raw", group_name="ingestion"),
    ],
    compute_kind="python",
)
def ingest_orders(context: dg.AssetExecutionContext):
    context.log.info("Ingesting orders and order_items together")
    # ... logic ...
    yield dg.Output(value=None, output_name="orders_raw")
    yield dg.Output(value=None, output_name="order_items_raw")
```

Use when a single API call or database query naturally produces multiple related tables.

### dagster-dbt integration

Always use the `DbtProjectComponent` YAML configuration approach in new projects:

**`components/dbt_project.yaml`**:
```yaml
type: dagster_dbt.DbtProjectComponent

params:
  dbt_project_dir: ../../       # path to directory containing dbt_project.yml
  select: "*"
  exclude: ""
```

This automatically generates one Dagster asset per dbt model, maintaining the dbt dependency graph. Dagster resolves `ref()` calls as asset dependencies.

For more control, use `@dbt_assets` directly:

```python
from dagster_dbt import DbtProject, dbt_assets

dbt_project = DbtProject(project_dir=Path(__file__).parent.parent.parent)

@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["run"], context=context).stream()
```

**Asset key convention**: Dagster-dbt creates keys as `AssetKey(["<model_name>"])`. To set a custom key prefix (e.g., matching a schema): use `key_prefix` in `@dbt_assets` or `DbtProjectComponent.asset_attributes`.

### Schedules

```python
from dagster import ScheduleDefinition, define_asset_job, AssetSelection

daily_refresh_job = define_asset_job(
    name="daily_refresh",
    selection=AssetSelection.all(),
)

daily_schedule = ScheduleDefinition(
    name="daily_refresh_schedule",
    cron_schedule="0 3 * * *",   # 3am UTC daily
    job=daily_refresh_job,
    execution_timezone="UTC",
    default_status=dg.DefaultScheduleStatus.RUNNING,
)
```

**Cron reference** (common patterns):
| Expression | Meaning |
|-----------|---------|
| `0 * * * *` | Every hour |
| `0 3 * * *` | Daily at 3am UTC |
| `0 3 * * 1` | Weekly Monday 3am UTC |
| `0 3 1 * *` | Monthly 1st at 3am UTC |
| `*/15 * * * *` | Every 15 minutes |

### Asset sensors

Use when pipeline should trigger on an event (upstream asset materialization, file arrival):

```python
@dg.asset_sensor(
    asset_key=dg.AssetKey("source_asset_name"),
    job=downstream_job,
    minimum_interval_seconds=60,
)
def source_ready_sensor(
    context: dg.SensorEvaluationContext,
    asset_event: dg.EventLogEntry,
):
    yield dg.RunRequest(run_key=context.cursor)
```

### Declarative automation

Prefer `AutomationCondition` over explicit sensors for standard scheduling patterns:

```python
@dg.asset(
    automation_condition=dg.AutomationCondition.eager(),  # run as soon as upstream is ready
)
def downstream_asset(): ...

@dg.asset(
    automation_condition=dg.AutomationCondition.on_cron("0 3 * * *"),  # daily at 3am
)
def daily_asset(): ...
```

Use `eager()` for streaming/event-driven pipelines. Use `on_cron()` for batch pipelines.

### Resources (credentials and connections)

```python
@dg.resource
def bigquery_resource(context):
    return bigquery.Client(project=dg.EnvVar("GCP_PROJECT_ID").get_value())
```

Always inject credentials via `EnvVar`, never hardcode. Use `{{ env.VAR_NAME }}` in YAML component configs.

### CLI reference

| Command | Purpose |
|---------|---------|
| `uvx create-dagster project <name>` | Scaffold new project — NEVER create manually |
| `dg dev` | Start local Dagster UI at localhost:3000 |
| `dg launch --assets "*"` | Materialize all assets |
| `dg launch --assets "group:ingestion"` | Materialize assets in group |
| `dg launch --assets "tag:layer=ingestion"` | Materialize assets by tag |
| `dg check defs` | Validate definitions load without errors |
| `dg list defs` | List all registered assets, schedules, sensors |
| `dg list defs --select "kind:dbt"` | List dbt assets only |
| `dg scaffold defs AssetSpec` | Add a new asset definition |

### Definitions registration

Always register everything in `__init__.py`:

```python
import dagster as dg
from . import assets, schedules

defs = dg.Definitions(
    assets=dg.load_assets_from_modules([assets]),
    schedules=[schedules.daily_schedule],
    sensors=[],
    resources={},
)
```

`load_assets_from_modules()` automatically discovers all `@dg.asset` and `@dg.multi_asset` decorated functions in the module.

---

## Wire-Specific Patterns

### Asset key alignment with dbt model names

In Wire projects, dbt models follow the naming convention: `stg_<source>__<entity>`, `int_<entity>`, `<entity>_dim`/`<entity>_fct`. Dagster-dbt exposes these as asset keys — use these keys when creating downstream assets:

```python
@dg.asset(deps=[dg.AssetKey("orders_fct")])
def orders_report(): ...
```

### Group naming convention

Use groups to mirror Wire's dbt layering:

| Group name | Contents |
|-----------|----------|
| `ingestion` | Source system assets (raw data landing) |
| `staging` | Maps to dbt staging layer |
| `integration` | Maps to dbt integration layer |
| `warehouse` | Maps to dbt warehouse layer |
| `reporting` | BI / semantic layer downstream assets |

### Environment variables

Standard env vars for Wire + Dagster projects:

```
ANTHROPIC_API_KEY=          # for Wire commands
DBT_PROFILES_DIR=           # path to dbt profiles.yml
DAGSTER_HOME=~/.dagster     # Dagster storage directory
<SOURCE>_API_KEY=           # per source system
```
