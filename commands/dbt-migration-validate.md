---
description: Validate dbt model translations compile on target profile
argument-hint: <release-folder> [--batch N]
---

# Validate dbt model translations compile on target profile

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
description: Validate dbt model translations compile on target profile
---

# dbt Migration — Validate

## Purpose

Validates that translated dbt models compile and pass basic structural checks against the target platform profile. Optionally runs `dbt compile` if the target profile is accessible.

## Flags

- `--batch N` — validate batch N only (default: current_batch in status.md)
- `--macros` — validate the batch-zero macro pass (`/wire:dbt-migration-generate --macros`) instead of a model batch. See **Macro Mode Checks** below.

## Validation Checks

**Check 1 — Translated files exist for all models in batch**
Every model in the batch has a corresponding translated `.sql` file in `migration/dbt/`.
PASS/FAIL with gaps.

**Check 2 — No source-platform-specific functions remain**
Scan translated SQL for functions that exist only on the source platform (using feature_detection patterns). Any remaining source-platform functions that should have been translated are a FAIL.
PASS: No source-platform-only functions found.
FAIL: List functions and models.

**Check 3 — MANUAL REVIEW flags tracked**
Every `-- MANUAL REVIEW` comment in the translated SQL is listed in the batch summary file.
PASS: All flags tracked.
FAIL: Flags found in SQL not in summary.

**Check 4 — Jinja syntax is valid**
Scan translated Jinja for obvious syntax errors (unclosed tags, undefined variables).
PASS: No Jinja syntax errors.
FAIL: List models with errors.

**Check 5 — dbt compile (if target profile available)**
If `~/.dbt/profiles.yml` has a profile matching `migration.target_platform`:
Run `dbt compile --select batch_N_models --profiles-dir ~/.dbt`
PASS: All models in batch compile without errors.
FAIL: List compilation errors per model.
If target profile not available: note as "compile check skipped — target profile not configured" (not a FAIL).

**Check 6 — Diff files exist**
Every model in the batch has a `.diff.md` side-by-side diff file.
PASS/FAIL.

**Check 7 — Companion schema/properties YAML handled**
For every model in the batch that has a companion schema/properties YAML in the source project, the translation covers it:
- `sources.yml` referenced by the batch resolves to the target namespace (parameterised `database`/`schema`, or repointed) — not left pointing at the source platform.
- Singular/custom tests, `where:` filters, and `dbt_utils`/`dbt_expectations` arguments containing source-dialect SQL are translated (no source-platform-only functions remain in test SQL — same scan as Check 2, applied to tests).
- Any column-level `policy_tags` / masking `meta` is either authored into the YAML (dbt-managed) or explicitly recorded in the batch summary as deferred to the security workstream — not silently dropped.
PASS: All companion-YAML items handled or explicitly deferred. FAIL: List models with an un-repointed `sources.yml`, untranslated test SQL, or dropped policy-tag/meta config.

## Macro Mode Checks (`--macros`)

Run these instead of Checks 1–7 when `--macros` is supplied. Ground truth is `audit/batch_zero_plan.json` (the `layer: macro`, `action: translate` entries), re-read here rather than trusted from generate's summary.

**Check M1 — Every macro-layer entry has a translated file**
For every `layer: macro`, `action: translate` entry in `batch_zero_plan.json`, a translated definition exists under `migration/dbt/macros/` at the mirrored relative path. UDF-layer entries are explicitly out of scope (they are validated by `/wire:target-setup-validate`).
PASS/FAIL with gaps.

**Check M2 — No source-platform-specific functions remain in macro bodies**
Same scan as Check 2, applied to the translated macro files.
PASS/FAIL with functions and macros listed.

**Check M3 — Tier order is respected**
No translated macro references the *source-dialect* form of a lower-tier macro it depends on — a tier-N macro must call the already-translated tier-`<N` version. Rebuild the dependency tiers from `batch_zero_plan.json`.
PASS/FAIL with violations listed.

**Check M4 — MANUAL REVIEW flags and deferrals tracked**
Every `-- MANUAL REVIEW` comment in a translated macro, and every `compile: deferred` macro, is listed in `batch_zero_macros_summary.md`.
PASS/FAIL.

**Check M5 — Diff files exist**
Every translated macro has a `.diff.md`.
PASS/FAIL.

### Update status

```yaml
artifacts:
  dbt_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    batch_N_validate: pass | fail
    macros_validate: pass | fail          # set only when run with --macros
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact_id, `dbt Migration` as artifact_name, and the `file` value from `artifacts.dbt_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `validate` as action.

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
