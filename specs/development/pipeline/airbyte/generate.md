---
description: Create and configure Airbyte connections based on approved pipeline design
argument-hint: <project-folder>
---

# Airbyte Pipeline Generate

Follow `specs/utils/pipeline_engineer_delegate.md` before executing the workflow below.

## Purpose

Create Airbyte connections (sources, destinations, connections) for each source system specified in the approved pipeline architecture.

## Called by

`wire/specs/development/pipeline/generate.md` when `pipeline_tool == airbyte`

## Status

**Not yet implemented.** This spec is a placeholder for future Airbyte support.

When Airbyte support is added (via the Airbyte MCP server or Airbyte API), this spec will:
1. Read source systems and replication strategy from `pipeline_architecture.md`
2. Create Airbyte source connectors per source system
3. Create or reference the destination connector (BigQuery, Snowflake, etc.)
4. Create Airbyte connections linking sources to the destination, with stream-level sync mode config
5. Configure sync schedules per the pipeline design
6. Run connection checks to verify source/destination connectivity
7. Write `pipeline_connections.md` documenting all connections

## Output (when implemented)

- `.wire/<project_id>/development/pipeline/pipeline_connections.md`
