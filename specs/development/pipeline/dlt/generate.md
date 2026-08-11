---
description: Create dlt pipeline scripts based on approved pipeline design
argument-hint: <project-folder>
---

# dlt Pipeline Generate

Follow `specs/utils/pipeline_engineer_delegate.md` before executing the workflow below.

## Purpose

Generate dlt (data load tool) pipeline scripts for each source system specified in the approved pipeline architecture.

## Called by

`wire/specs/development/pipeline/generate.md` when `pipeline_tool == dlt`

## Status

**Not yet implemented.** This spec is a placeholder for future dlt support.

When dlt support is added, this spec will:
1. Read source systems and replication strategy from `pipeline_architecture.md`
2. Generate Python dlt pipeline scripts using verified sources (`dlt.sources`) where available, or custom REST API sources
3. Configure destination (BigQuery, Snowflake, etc.) via dlt secrets
4. Set up incremental loading strategies (append, merge, replace) per source
5. Write pipeline scripts to `.wire/<project_id>/development/pipeline/dlt/`
6. Write `pipeline_connections.md` documenting all pipelines

## Output (when implemented)

- `.wire/<project_id>/development/pipeline/dlt/<source>_pipeline.py` per source
- `.wire/<project_id>/development/pipeline/dlt/requirements.txt`
- `.wire/<project_id>/development/pipeline/pipeline_connections.md`
