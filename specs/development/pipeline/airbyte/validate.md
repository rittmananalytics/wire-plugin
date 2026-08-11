---
description: Validate Airbyte connections against the approved pipeline design
argument-hint: <project-folder>
---

# Airbyte Pipeline Validate

## Purpose

Validate that Airbyte connections are correctly configured, healthy, and match the approved pipeline architecture.

## Called by

`wire/specs/development/pipeline/validate.md` when `pipeline_tool == airbyte`

## Status

**Not yet implemented.** Placeholder for future Airbyte support.

When implemented, validation will cover:
- Source and destination connector status
- Connection sync status and last sync result
- Stream selection matches in-scope entities from conceptual model
- Sync mode (full refresh / incremental) matches replication strategy
- Sync schedule matches pipeline design cadence
