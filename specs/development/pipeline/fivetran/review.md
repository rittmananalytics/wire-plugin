---
description: Build Fivetran connection summary for stakeholder review
argument-hint: <project-folder>
---

# Fivetran Pipeline Review

## Purpose

Build a human-readable summary of all Fivetran connections for presentation in the pipeline review session. This spec produces the review content; the calling spec (`pipeline/review.md`) handles stakeholder interaction and approval capture.

## Called by

`wire/specs/development/pipeline/review.md` when `pipeline_tool == fivetran`

## Workflow

### Step 1: Read Connection State

1. Read `.wire/<project_id>/development/pipeline/pipeline_connections.md`
2. For each connection, call `mcp__fivetran__get_connection_details` to get current live state (setup_state, succeeded_at, sync_frequency, paused)
3. Call `mcp__fivetran__get_connection_schema_config` for each connection to list enabled tables

### Step 2: Build Review Summary

Present:

```
## Pipeline Review: Fivetran Connections

**Project**: [project_name]
**Destination Group**: [group_name]
**Total connections**: [N]
**All connections healthy**: Yes / No — [N] require attention

---

### Connection Summary

| Source | Service | Schema | Setup | Last Sync | Frequency | Tables Enabled |
|--------|---------|--------|-------|-----------|-----------|----------------|
| [name] | [service] | [schema] | ✅ connected / ❌ [state] | [date or "never"] | [N] min | [N] |

---

### Connection Details

#### [Source System Name]
- **Fivetran dashboard**: [call mcp__fivetran__get_connection_url to get link]
- **Connection ID**: `[id]`
- **Service**: `[service]`
- **Schema (landing in warehouse)**: `[schema]`
- **Setup state**: [state]
- **Last successful sync**: [succeeded_at or "never synced"]
- **Sync frequency**: every [N] minutes
- **Tables being synced**: [list of enabled tables]
- **Tables excluded**: [list of disabled tables]
- **PII columns hashed**: [list or "none"]

[Repeat for each connection]

---

### Design Decisions Implemented

[List each design decision from the pipeline design doc and confirm how it was implemented]

### Outstanding Issues

[List any connections with setup_failed, never-synced, or validation warnings from validate step]
```

Return this summary to the calling spec (`pipeline/review.md`) for presentation to the reviewer.
