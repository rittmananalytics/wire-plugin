---
description: Validate reverse ETL migration runbook completeness
argument-hint: <release-folder>
---

# Validate reverse ETL migration runbook completeness

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
description: Validate reverse ETL migration runbook completeness and sync coverage
---

# Reverse ETL Migration — Validate

## Purpose

Checks the reverse ETL migration runbook for completeness — the migration topology is recorded, every in-scope sync has migration steps, SQL translations are present for rewrite_model syncs, rebuild plans cover all Customer Studio audiences and Journeys, validation is preview-based against a frozen baseline with syncs disabled, sync-level transformation logic is reviewed, and Lightning schema provisioning is documented. Produces a PASS/FAIL report.

## Prerequisites

- `migration/reverse_etl_migration_runbook.md` exists

## Validation Checks

**Check 1 — Topology recorded**
The runbook states the chosen topology (parallel workspace or in-place re-point) with a rationale. For the parallel-workspace path, it documents the repo clone, new workspace, GitHub Sync configuration, and target-warehouse source connection.
PASS: Topology and its setup steps present. FAIL: Topology not stated or build steps missing.

**Check 2 — All in-scope syncs covered**
Every sync with `include_in_migration: true` in the audit has a section in the runbook.
PASS: All syncs present. FAIL: List missing syncs.

**Check 3 — rewrite_model syncs have SQL diffs**
Every `rewrite_model` sync includes a before/after SQL diff showing the original and translated query.
PASS: All diffs present. FAIL: List syncs missing SQL diff.

**Check 4 — Translated SQL verified on target**
Each rewrite_model sync documents the result of running the translated SQL against the target warehouse (row count, primary key check).
PASS: All verifications present. FAIL: List unverified translations.

**Check 5 — Rebuild plans documented**
Every `rebuild` sync has a documented schema mapping and step-by-step rebuild plan.
PASS: All rebuild plans present. FAIL: List missing rebuild plans.

**Check 6 — Validation is preview-based against a frozen baseline, syncs disabled**
The validation procedure compares model outputs and audience sizes against a frozen source baseline (not live production) and uses sync previews / record inspection with destination connections disabled. It does not enable destination syncs to validate.
PASS: Validation is preview-based against a baseline with syncs disabled. FAIL: Validation relies on enabling syncs / live runs, or compares against moving production.

**Check 7 — Sync-level transformation logic reviewed**
The runbook records a per-sync review of sync-level logic — field mappings, computed fields, sync filters, match/identity-resolution rules, and audience inclusion/exclusion — separate from model-output comparison.
PASS: Sync-level review present for all in-scope syncs. FAIL: List syncs missing the review.

**Check 8 — Lightning schema provisioning documented**
If any Lightning syncs are in scope, the runbook includes the `CREATE SCHEMA` and `GRANT` statements.
PASS: Present, or no Lightning syncs. FAIL: Missing.

**Check 9 — Rollback procedures present**
The runbook includes a rollback procedure for the chosen topology and each approach type used (parallel: don't enable / disable new-workspace syncs and re-enable the source workspace; in-place: re-apply original `sourceId`).
PASS: Rollbacks present. FAIL: List missing rollbacks.

**Check 10 — Source left active until cutover**
The runbook does not deactivate the source syncs (or source workspace) during the migration phase — only after cutover, once confidence is established.
PASS: Source deactivation / workspace decommission is in the cutover/sign-off section only. FAIL: It appears in the migration or validation steps.

### Write validation report

Append a `## Validation` section to `migration/reverse_etl_migration_runbook.md` following the standard format.

Update status:
```yaml
artifacts:
  reverse_etl_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

If PASS: `/wire:reverse-etl-migration-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact_id, `Reverse ETL Migration` as artifact_name, and the `file` value from `artifacts.reverse_etl_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_migration` as artifact, `validate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
