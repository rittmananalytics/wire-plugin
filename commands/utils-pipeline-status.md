---
description: Check configured pipeline tool connection status
argument-hint: <release-folder>
---

# Check configured pipeline tool connection status

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
description: Check pipeline connection health and optionally trigger a sync — tool-agnostic router
argument-hint: <project-folder> [connection-id-or-name]
---

# Pipeline Tool Status Utility

## Purpose

Check the health of pipeline connections and optionally trigger a sync. Routes to the appropriate tool-specific status utility based on `pipeline_tool` in `status.md`. Used by orchestration and deployment specs to verify data freshness before downstream steps.

## Usage

Invoked automatically by:
- `wire/specs/development/orchestration/generate.md` — to verify connections exist before wiring orchestration
- `wire/specs/deployment/validate.md` — pre-flight check that all connections are healthy

Can also be invoked directly:
```bash
/wire:utils-pipeline-status YYYYMMDD_project_name
```

## Workflow

### Step 1: Read Pipeline Tool

1. Read `.wire/<project_id>/status.md`
2. Read `artifacts.pipeline.pipeline_tool`
3. If null: report "No pipeline tool configured — skip pipeline status check"

### Step 2: Route to Tool-Specific Utility

| `pipeline_tool` | Utility |
|----------------|---------|
| `fivetran` | `wire/specs/utils/fivetran_status.md` |
| `dlt` | Not yet implemented — skip with a note |
| `airbyte` | Not yet implemented — skip with a note |
| `custom` | Not yet implemented — skip with a note |

### Step 3: Return Result

The tool-specific utility returns one of:
- `healthy` — all connections connected and last sync succeeded
- `degraded` — some connections have warnings (stale sync, minor issues)
- `unhealthy` — one or more connections have critical failures

Surface this result to the calling spec so it can decide whether to proceed or halt.

Execute the complete workflow as specified above.
