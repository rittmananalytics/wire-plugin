---
description: Build the review summary for Airflow ingestion DAGs, with non-blocking rule findings, a requirements table and the tested-in-dev verdict
argument-hint: <project-folder>
---

# Airflow Pipeline Review

## Purpose

Build the summary a reviewer reads for Airflow ingestion work: what changed, the rule findings and their dispositions, the requirements table, and whether the change was tested in dev.

## Called by

`wire/specs/development/pipeline/review.md` when `pipeline_tool == airflow`

## Workflow

1. Read `pipeline_connections.md` and `pipeline_validation.md` for the loads, DAGs and check results.
2. Read `.wire/engagement/review_profile.yml` (schema in `wire/schemas/review-profile-schema.md`) for `review_mode`. Lead with the requirements table for `new_functionality`, with the rule findings and failure paths for `bug_hunt`.
3. Build the two review tables with `wire/scripts/review_rules.py` (review rules C6):
   - Rule findings: each `fixed`, `justified` (reason required) or `acknowledged`. Findings never block the review. A finding with no disposition is listed as `open`.
   - Requirements: each `met`, `not met` or `can't tell`, with evidence. A `not met` requirement is raised as a question to the ticket owner; the review does not decide it.
4. If `/wire:utils-dev-test-evidence` has run for this branch, include its verdict table. If it has not, say so in one line; do not run it from here.
5. Present the summary to the pipeline review session.
