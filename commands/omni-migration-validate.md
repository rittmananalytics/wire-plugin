---
description: Validate Omni migration runbook completeness
argument-hint: <release-folder>
---

# Validate Omni migration runbook completeness

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Validate Omni migration runbook completeness — raw-SQL tile scope, view translations, branch validation, two-stage repoint with rollback
---

# Omni Migration — Validate

## Purpose

Checks the Omni migration runbook for completeness: the raw-SQL tile count was reconfirmed live before translation, every in-scope view has migration steps, `rewrite_sql` views have verified SQL diffs, raw-SQL tile translations are documented and tested, validation runs on a model branch against a frozen baseline, and the two-stage connection cutover has per-stage rollback. Produces a PASS/FAIL report.

## Prerequisites

- `migration/omni_migration_runbook.md` exists

## Validation Checks

**Check 1 — Raw-SQL tile scope reconfirmed live**
The runbook records that the raw-SQL tile count was recounted live against the Omni instance and matched (or reconciled against) `omni_audit`'s `raw_sql_tile_count` before translation started. `raw_sql_tile_count_reconfirmed: true` is set in status.md.
PASS: reconfirmation recorded. FAIL: no reconfirmation, or a drift was found and not resolved by an audit re-run.

**Check 2 — Topology recorded**
The runbook states the additive topology (target connection added alongside source, model branch created for translation) with rationale, and documents the build steps.
PASS/FAIL.

**Check 3 — All in-scope views covered**
Every view with `include_in_migration` true (or not excluded) in the `omni_audit` catalog has a section in the runbook.
PASS: all present. FAIL: list missing views.

**Check 4 — rewrite_sql views have SQL diffs**
Every `rewrite_sql` view includes a before/after SQL diff (source dialect → target).
PASS: all diffs present. FAIL: list views missing a diff.

**Check 5 — Translated view SQL verified on the branch**
Each `rewrite_sql` view documents the result of running the translated SQL on the model branch against the target connection (row count, result shape) against the frozen baseline.
PASS/FAIL with unverified translations.

**Check 6 — Rebuild plans documented**
Every `rebuild` view has a documented rebuild plan against the target connection.
PASS/FAIL.

**Check 7 — Raw-SQL tile translations documented and tested**
Every raw-SQL tile with an approach other than `inherits_via_model` has a before/after SQL diff and a documented `omni-query` test result against the target connection, held as a pending edit for Stage 2.
PASS/FAIL with untested or undocumented tile translations.

**Check 8 — Validation is branch-based against a frozen baseline**
Validation runs on the model branch, scoped to a pilot/non-production connection scope, and compares results against a frozen source baseline. No production connection is repointed, and no production workbook/tile is edited, to validate.
PASS: branch-based against a baseline, scoped to pilot. FAIL: validation repoints the primary connection, edits production content, or compares against moving production.

**Check 9 — Two-stage cutover with per-stage rollback**
The cutover is two stages — Stage 1 branch validation on a pilot/non-production connection scope, Stage 2 branch promotion plus primary connection repoint (and raw-SQL tile edits) — and each stage has an explicit rollback (Stage 1: abandon/revert the branch; Stage 2: revert the connection details, revert the model to its pre-promotion state, restore raw-SQL tile SQL from diffs).
PASS: both stages and both rollbacks documented. FAIL: single-stage cutover, or a stage missing its rollback.

**Check 10 — Source connection left live until Stage 2**
The runbook does not repoint or delete the source connection during Step 1–6 (branch creation, translation, or Stage 1 validation) — only at Stage 2. The source connection remains the rollback path through Stage 2.
PASS: connection repoint appears only in the Stage 2 section. FAIL: source connection repointed/deleted before Stage 2.

### Write validation report

Append a `## Validation` section to `migration/omni_migration_runbook.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

Update status:
```yaml
artifacts:
  omni_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

If PASS: `/wire:omni-migration-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact_id, `Omni Migration` as artifact_name, and the `file` value from `artifacts.omni_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_migration` as artifact, `validate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
