# Proposal: approved names win over the naming convention

For the process registry (`specs/development/dbt_generate.md`, and the same
paragraph in `dbt_staging_generate.md`, `dbt_integration_generate.md`,
`dbt_warehouse_generate.md`). Raised by the Wire CLI concept run, 4 November
2026 (wire#408, roadmap phase 6).

## What the run found

The release's approved data model specification named twelve models with
single-underscore names (`int_developer_activity_events`). Wire's dbt
convention wants `int_<group>__<entity>` and `wh_<group>__<entity>_fact`. The
spec says nothing about which wins, and three model families did three
different things on the same lane:

| Harness and model | What it did |
|---|---|
| Claude Code, Claude | Kept the approved names; accepted the 12 file-name lint errors |
| Codex, OpenAI | Stopped and asked (parked as a decision) |
| Codex, Qwen (local) | Renamed all twelve to the convention; matched nothing by name |

With the director's ruling R-4 ("the approved names stand") in the brief, the
OpenAI lane then matched Claude's result. A rule in the spec would have made
the ruling unnecessary.

## Proposed text (after the "Never rename or move" bullet)

- Names in the release's approved data model specification
  (`data_model.review: approved`) are used as written, even where they do not
  follow the naming rules below. A lint finding on an approved name is
  recorded in the validate report as accepted ("approved in the data model
  specification"), not fixed. Do not rename an approved name, and do not stop
  to ask about it.
- Where the data model specification is not yet approved, use the
  convention's form and list each name that differs from the specification in
  the generate report, for the data model review to settle.
- A new model the specification does not name follows the convention.

## Test

A fixture case for `dbt-validate`'s classification: a finding on an approved
name is `accepted`, on a new name `fail`. And a case in the Wire CLI's eval
suite (`wire/cli/evals/`): given an approved spec name that breaks the
convention, the lane keeps the name.
