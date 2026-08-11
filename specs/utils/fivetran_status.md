---
description: Check Fivetran connection health and optionally trigger a sync
argument-hint: <project-folder> [connection-id]
---

# Fivetran Status Utility

## Purpose

Check the health of Fivetran connections documented in `pipeline_connections.md`. Optionally triggers an incremental sync and waits for completion. Returns a structured health result (`healthy` / `degraded` / `unhealthy`) to the calling spec.

## Called by

`wire/specs/utils/pipeline_tool_status.md` when `pipeline_tool == fivetran`

## Workflow

### Step 1: Read Connection IDs

Read `.wire/<project_id>/development/pipeline/pipeline_connections.md` and extract all `connection_id` values.

If the file does not exist, return `unhealthy` with message: "pipeline_connections.md not found — pipeline may not have been generated yet."

### Step 2: Check Each Connection

For each `connection_id`, call `mcp__fivetran__get_connection_details` and evaluate:

| Field | Healthy | Degraded | Unhealthy |
|-------|---------|----------|-----------|
| `status.setup_state` | `"connected"` | — | anything else |
| `paused` | `false` | — | `true` |
| `succeeded_at` vs `failed_at` | `succeeded_at` is more recent | `succeeded_at` is > 24h ago | `failed_at` is more recent than `succeeded_at` |
| `sync_frequency` | matches pipeline design | within 2x of design cadence | — |

### Step 3: Optionally Trigger Sync

If called with `trigger_sync: true` (set by the calling spec when it needs fresh data):

1. For each healthy connection, call `mcp__fivetran__sync_connection` with `{"force": false}`
2. Wait up to 5 minutes: poll `mcp__fivetran__get_connection_state` every 30 seconds
3. If sync completes (`sync_state == "scheduled"` and new `succeeded_at`): mark as synced
4. If sync does not complete within 5 minutes: mark as `sync_in_progress` — do not block the calling spec, but note the sync is still running

Only trigger a sync if explicitly requested — do not auto-trigger on every call.

### Step 4: Return Health Result

Aggregate across all connections:

- **`healthy`**: All connections have `setup_state == connected`, not paused, and `succeeded_at` is within 2× the sync frequency
- **`degraded`**: All connections are connected but one or more have stale syncs or minor warnings
- **`unhealthy`**: One or more connections are broken, paused, or have a more recent `failed_at` than `succeeded_at`

Return a summary block:

```
## Fivetran Pipeline Status

**Overall**: healthy / degraded / unhealthy

| Connection | Setup State | Last Sync | Status |
|-----------|-------------|-----------|--------|
| [schema] (`[id]`) | connected | [date] | ✅ / ⚠️ / ❌ |

[List any issues with connection_id, field, and value]
```
