---
description: Create and configure Fivetran connections based on approved pipeline design
argument-hint: <project-folder>
---

# Fivetran Pipeline Generate

Follow `specs/utils/pipeline_engineer_delegate.md` before executing the workflow below.

## Purpose

Create Fivetran connections for each source system specified in the approved pipeline architecture, configure schema/table/column sync settings, and produce a `pipeline_connections.md` artifact documenting every connection created.

## Called by

`wire/specs/development/pipeline/generate.md` when `pipeline_tool == fivetran`

## Workflow

### Step 1: Read Pipeline Design

1. Read `.wire/<project_id>/design/pipeline_architecture.md`
2. Extract:
   - All source systems designated for Fivetran replication
   - The target destination/group (from Section 4 or 6 of the design)
   - Sync frequency per source
   - In-scope tables/entities per source (from the conceptual model cross-reference)
   - PII columns flagged for hashing
   - Schema naming conventions (`fivetran_<source>` or as specified)

### Step 2: Resolve Destination Group

1. Call `mcp__fivetran__list_groups` — enumerate all groups
2. Match the group named in the pipeline design. If multiple groups exist and the design is ambiguous, ask:
   ```
   Multiple Fivetran destination groups found:
   [list group names and IDs]

   Which group should the new connections be created in?
   ```
3. Store the resolved `group_id` for use in Step 4.

Also call `mcp__fivetran__run_destination_setup_tests` on the resolved destination — halt with an error if this fails.

### Step 3: Check for Existing Connections (Idempotency)

Call `mcp__fivetran__list_connections_in_group` with the resolved `group_id`.

For each source system in the pipeline design:
- Check whether a connection with a matching `schema` name already exists
- If it does: record its `connection_id`, note it as **existing**, and skip creation in Step 4
- If it does not: mark it for creation

This prevents duplicate connections on re-runs.

### Step 4: Create Connections

For each source system marked for creation:

**4a. Confirm connector config requirements**
Call `mcp__fivetran__get_metadata_connector_config` with the `service` slug from the pipeline design.
- Note which fields go in `config` vs `auth`
- Note any required fields that are not yet known (flag as **blocked** — cannot proceed without them)

If any connection is blocked due to missing credentials, list them all up-front and ask the user to provide them before proceeding. Do not partially create connections.

**4b. Create the connection**
Call `mcp__fivetran__create_connection` with:
- `service`: connector type slug
- `schema`: as specified in the pipeline design (permanent — confirm with user before proceeding)
- `group_id`: resolved in Step 2
- `config`: service-specific config fields
- `auth` (if OAuth-based): leave empty at creation; set in Step 4c

**4c. Set OAuth auth (if required)**
If the connector uses OAuth, call `mcp__fivetran__modify_connection` with:
```json
{"auth": {"access_token": "<token>"}}
```
Prompt the user for the access token if not already provided.

**4d. Verify connection health**
Call `mcp__fivetran__get_connection_details` and check `status.setup_state`:
- `"connected"` → healthy, proceed
- `"broken"` or `"incomplete"` → log the error, mark the connection as `setup_failed`, and continue with remaining connections. Do not halt the whole run.

Optionally, also call `mcp__fivetran__run_connection_setup_tests` as a secondary check. Note: as of 2026-05, this MCP tool may return `400 Request body must not be empty` due to a wrapper bug — if it does, treat it as inconclusive and rely on `get_connection_details` alone. Do not mark the connection as `setup_failed` solely due to this error.

Record each connection: `connection_id`, `schema`, `service`, `setup_state`.

### Step 5: Configure Schema, Table, and Column Sync

For each connection (existing and newly created):

**5a. Reload schema discovery**
Call `mcp__fivetran__reload_connection_schema_config` to discover all available tables from the source.

**5b. Disable out-of-scope tables**
Call `mcp__fivetran__get_connection_schema_config` to get the full table list.

Cross-reference against the in-scope entities from the pipeline design. For every table NOT in scope:
- Call `mcp__fivetran__modify_connection_table_config` with `{"enabled": false}`

This minimises MAR and avoids syncing irrelevant data.

**5c. Hash PII columns**
For each column flagged for hashing in the pipeline design:
- Call `mcp__fivetran__modify_connection_column_config` with `{"hashed": true}`

Confirm with the user before applying hashing — this takes effect on the next sync and cannot be undone for that sync cycle.

### Step 6: Set Sync Frequency

For each connection, call `mcp__fivetran__modify_connection` with the sync frequency from the pipeline design:

| Cadence in design | `sync_frequency` value (minutes) |
|-------------------|----------------------------------|
| Real-time / streaming | 5 |
| Every 15 minutes | 15 |
| Hourly | 60 |
| Every 3 hours | 180 |
| Every 6 hours | 360 |
| Daily | 1440 |

### Step 7: Trigger Initial Sync

For each connection with `setup_state == connected`:
- Call `mcp__fivetran__sync_connection` with `{"force": false}` to start the first incremental sync
- Do not call `resync_connection` — a full historical re-sync is expensive and should only be done on explicit request

### Step 8: Write Pipeline Connections Artifact

Write `.wire/<project_id>/development/pipeline/pipeline_connections.md`:

```markdown
# Pipeline Connections: [Project Name]

**Tool**: Fivetran
**Destination Group**: [group_name] (`[group_id]`)
**Generated**: [date]

## Connections

| Source System | Service | Connection ID | Schema | Setup State | Sync Frequency | Tables In Scope | PII Columns Hashed |
|--------------|---------|--------------|--------|-------------|----------------|-----------------|-------------------|
| [name] | [service] | [id] | [schema] | connected / setup_failed | [freq] | [count] | [count] |

## Connection Details

### [Source System Name]
- **Connection ID**: `[id]`
- **Service**: `[service slug]`
- **Schema**: `[schema]`
- **Group**: `[group_name]`
- **Setup state**: `[state]`
- **Sync frequency**: [N] minutes
- **Tables enabled**: [list]
- **Tables disabled**: [list]
- **PII columns hashed**: [list, or "none"]
- **Notes**: [any setup_failed errors, OAuth pending, etc.]

[Repeat for each connection]

## Setup Issues

[List any connections with setup_failed state and the error message]
[List any blocked connections awaiting credentials]
```

### Step 9: Update Status

```yaml
pipeline:
  generate: complete
  validate: not_started
  review: not_started
  pipeline_tool: fivetran
  connections_file: development/pipeline/pipeline_connections.md
  generated_date: <today>
  connection_count: [N]
  setup_failed_count: [N]
```

If `setup_failed_count > 0`, also print a warning:
```
Warning: [N] connection(s) failed setup tests. Review pipeline_connections.md for details.
Fix and re-run /wire:pipeline-generate to retry failed connections.
```

## Edge Cases

### Missing connector service slug
If the pipeline design names a source system but not the Fivetran service slug (e.g. "Salesforce" but not `salesforce`), call `mcp__fivetran__list_metadata_connectors` and search by name to resolve the correct slug before proceeding.

### Connection already exists with different config
If an existing connection is found with the same schema name but different `service` or `group_id` than the design specifies, halt and report:
```
Conflict: A connection with schema "[schema]" already exists but uses service "[existing_service]"
not "[design_service]" as specified in the pipeline design.
Review the pipeline design or delete the existing connection manually before re-running.
```
Never delete an existing connection automatically.

### Destination group does not exist
If the group named in the pipeline design does not exist in Fivetran, report the available groups and ask whether to use an existing one or create a new one via `mcp__fivetran__create_group`.
