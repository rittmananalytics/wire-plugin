---
description: Validate dlt pipeline scripts against the approved pipeline design
argument-hint: <project-folder>
---

# dlt Pipeline Validate

## Purpose

Validate generated dlt pipeline scripts for correctness, coverage of in-scope entities, and destination configuration.

## Called by

`wire/specs/development/pipeline/validate.md` when `pipeline_tool == dlt`

## Status

**Not yet implemented.** Placeholder for future dlt support.

When implemented, validation will cover:
- Script syntax and import correctness
- Source coverage against conceptual model entities
- Destination config matches pipeline design
- Incremental loading strategy matches replication approach
- PII handling (field exclusions or hashing) in place
