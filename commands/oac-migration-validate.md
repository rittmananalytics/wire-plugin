---
description: Validate OAC migration runbook completeness
argument-hint: <release-folder>
---

# Validate OAC migration runbook completeness

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
description: Validate OAC migration runbook completeness — repo reconciliation, physical table translations, branch validation, two-stage repoint with rollback
---

# OAC Migration — Validate

## Purpose

Checks the OAC migration runbook for completeness: the semantic-model repo was reconciled to its latest commit before translation started, every in-scope physical table has migration steps, `rewrite_sql` constructs have verified SQL diffs, `manual-review-out-of-scope` constructs are documented with an owner rather than mechanically translated, validation runs on a Git branch against a frozen baseline via a non-production OAC copy, and the two-stage connection-pool cutover has per-stage rollback. Produces a PASS/FAIL report.

## Prerequisites

- `migration/oac_migration_runbook.md` exists

## Validation Checks

**Check 1 — Semantic-model repo reconciled**
The runbook records that the repo was pulled to its latest commit and its physical table / raw SQL construct counts were compared against `oac_audit`'s recorded counts before translation started. `repo_reconciled: true` is set in status.md.
PASS: reconciliation recorded. FAIL: no reconciliation, or a discrepancy was found and not resolved by an audit re-run.

**Check 2 — Topology recorded**
The runbook states the additive topology (target connection pool added alongside source, Git branch created for translation) with rationale, and documents the build steps — including the `databaseType` verification note for the target platform.
PASS/FAIL.

**Check 3 — Target databaseType confirmed, not guessed**
If the target platform's `databaseType` is not present in `smml-schema.md`'s documented enum, the runbook records how the correct value was confirmed (a live OAC Semantic Modeler dialog, or current Oracle connector documentation) rather than asserting an unverified value. `target_database_type_confirmed: true` is set in status.md.
PASS: confirmed and recorded. FAIL: an unconfirmed value asserted without a verification note.

**Check 4 — All in-scope physical tables covered**
Every physical table with `include_in_migration` true (or not excluded) in the `oac_audit` catalog has a section in the runbook.
PASS: all present. FAIL: list missing physical tables.

**Check 5 — rewrite_sql constructs have SQL diffs**
Every raw SQL construct classified `translate` and attached to a `rewrite_sql` physical table includes a before/after SQL diff (source dialect → target).
PASS: all diffs present. FAIL: list constructs missing a diff.

**Check 6 — Translated constructs verified on the branch**
Each translated construct documents the result of running its owning physical table's query on the Git branch against the target connection pool (row count, result shape) against the frozen baseline.
PASS/FAIL with unverified translations.

**Check 7 — Rebuild plans documented**
Every `rebuild` physical table (and every construct classified `redesign`) has a documented rebuild plan against the target connection pool.
PASS/FAIL.

**Check 8 — manual-review-out-of-scope constructs documented with an owner**
Every construct classified `manual-review-out-of-scope` appears in its own runbook table with the required reauthoring, an owner, and confirmation it was applied and tested at Stage 1 before being carried to Stage 2 — not folded into the `translate`/`rewrite_sql` counts.
PASS/FAIL with an undocumented or unowned construct.

**Check 9 — Validation is branch-based against a frozen baseline, via a non-production OAC copy**
Validation runs on the Git branch, imported into a non-production copy of the OAC environment, and compares results against a frozen source baseline. No production connection pool is repointed, and no production OAC environment is used, to validate.
PASS: branch-based against a baseline, via a non-production copy. FAIL: validation repoints the primary connection pool, uses a production OAC environment, or compares against moving production.

**Check 10 — Two-stage cutover with per-stage rollback**
The cutover is two stages — Stage 1 branch validation on a non-production copy, Stage 2 branch merge plus primary connection-pool repoint (and manual-review reauthoring) — and each stage has an explicit rollback (Stage 1: abandon/delete the branch and non-production import; Stage 2: revert the merge and re-import, revert the connection pool, restore connection-pool scripts).
PASS: both stages and both rollbacks documented. FAIL: single-stage cutover, or a stage missing its rollback.

**Check 11 — Source connection pool left live until Stage 2**
The runbook does not repoint or delete the source connection pool during Step 1–6 (branch creation, translation, or Stage 1 validation) — only at Stage 2. The source connection pool remains the rollback path through Stage 2.
PASS: connection pool repoint appears only in the Stage 2 section. FAIL: source connection pool repointed/deleted before Stage 2.

### Write validation report

Append a `## Validation` section to `migration/oac_migration_runbook.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

Update status:
```yaml
artifacts:
  oac_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

If PASS: `/wire:oac-migration-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_migration` as artifact_id, `OAC Migration` as artifact_name, and the `file` value from `artifacts.oac_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `oac_migration` as artifact, `validate` as action.

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
