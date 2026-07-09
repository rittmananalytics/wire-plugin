---
description: Validate dbt audit completeness and complexity ratings
argument-hint: <release-folder>
---

# Validate dbt audit completeness and complexity ratings

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
description: Validate dbt audit completeness, batch ordering against the manifest graph, disk reconciliation, conditionally-enabled model scope, and the batch-zero macro plan
---

# dbt Audit — Validate

## Purpose

Checks that all models are classified, that batch assignments respect the manifest-derived dependency graph, that the catalogue reconciles with the files actually on disk, that the macro layer is fully classified, that every var-driven `enabled` model is correctly tagged conditional and in scope rather than dropped as disabled, and that the batch-zero macro plan is complete and acyclic.

## Validation Checks

**Check 1 — All models have complexity rating**
Every model in the CSV has a non-null `complexity` value (Simple / Moderate / Complex).
PASS/FAIL with gaps listed.

**Check 2 — All models have batch number**
Every model classified `true` or `conditional:<var_name>` has a non-null `batch_number` — a conditional model is buildable and must carry a real batch number exactly like an unconditionally-enabled one. Every model classified **statically** `false` has a **null** `batch_number` — a non-null `batch_number` on a statically disabled model is also a FAIL.
PASS/FAIL with gaps and violations listed separately.

**Check 3 — Batch ordering respects dependency graph**
Re-run `specs/utils/dbt_manifest_parse.md` independently to get the model dependency graph — do not trust generate's self-report. For any enabled model in batch N with a dependency-graph parent (both enabled) in batch M, M ≤ N must hold. This check replaces any inference from the CSV's `ref_count` column — `ref_count` is a count, not a dependency edge.
PASS: Zero forward references.
FAIL: List every violating (model, parent, batch, parent_batch) tuple and the total forward-reference count.

**Check 4 — Feature tags applied to all models**
Every model has been scanned for platform-specific features (even if the tag list is empty — an empty list is valid, an unscanned model is not).
PASS: All models scanned.
FAIL: List unscanned models.

**Check 5 — CSV row count matches model count in status.md**
The row count in `dbt_audit.csv` (excluding header) matches `model_count` in status.md.
PASS: Counts match.
FAIL: Report discrepancy.

**Check 6 — No models without tests flagged**
Models with `has_tests: false` are noted in the audit. This is informational (not a FAIL on its own) but the count must be reported.
Output: N models have no tests (list them).

**Check 7 — Macros with adapter functions flagged**
Every model whose transitive macro-usage set (from the Check 3 re-parse) intersects the NEEDS-translation set has that intersection recorded, comma-separated, in `platform_macros`. Every macro classified as NEEDS-translation carries an `action` of `translate`, `redesign`, or `manual-review-out-of-scope` — none left unclassified.
PASS: Fully consistent.
FAIL: List models with missing or incomplete `platform_macros` and macros with no recorded `action`.

**Check 8 — Catalogue reconciles with disk**
Independently walk every resolved project's filesystem (per `specs/utils/dbt_manifest_parse.md` Steps 1 and 3) and compare against the CSV. This check exists specifically to catch a stale or substituted catalogue regardless of how it went stale — it must not rely on generate's own report of what it did.
PASS: Every `file_path` in the CSV resolves to a real file, and every `.sql`/`.py` model file on disk under a resolved project appears as a CSV row.
FAIL: List dead `file_path` values (in the CSV, not on disk) and missing models (on disk, not in the CSV), with counts of each.

**Check 9 — Batch-zero macro plan is complete, layered, and acyclic**
Every macro with `action: translate` or `action: redesign` appears in `batch_zero_plan.json` — translate macros with a non-null tier; redesign macros listed in the redesign bucket, no tier required. Tier assignment is internally consistent: no macro's tier is ≤ any NEEDS-macro dependency's tier. Every entry also carries a `layer` of `macro` or `udf` (never absent, never any other value), and the assignment is consistent: `create_udfs`, `fn_*`-prefixed names, and `fn_-UDF`-category entries are `layer: udf`; all other entries are `layer: macro`. This is the field `/wire:dbt-migration-generate --macros` and `/wire:target-setup-generate` route on — a missing or wrong `layer` sends a macro to the wrong lifecycle.
PASS/FAIL with violations listed (including any entry missing `layer` or classified into the wrong lifecycle).

**Check 10 — Conditionally-enabled models are correctly in scope**
Independently re-scan for var-driven `enabled` config per `specs/utils/dbt_manifest_parse.md` Step 3b — in-model config and folder-level `+enabled` in every resolved project's `dbt_project.yml` — do not trust generate's classification or the manifest's resolved `nodes`/`disabled` split alone. For every model whose `enabled` resolution path contains a `var(` call, anywhere, confirm: it is tagged `conditional:<var_name>` in the CSV (never `true` and never `false`), it carries a non-null `batch_number`, and it is not counted toward the statically-disabled exemption in Check 2.
PASS: every var-driven model found by the independent source re-scan is tagged `conditional:*` with a real batch number.
FAIL: list every var-driven model the re-scan found that the CSV instead marks `true`, `false`, or leaves with a null `batch_number` — a model in this list was silently dropped from scope (or silently and permanently marked enabled) by a manifest resolved under one default var-set. This is the check that would have caught a conditionally-enabled model being waved through as "correctly exempt" from Check 2 instead of being flagged.

### Update status

```yaml
artifacts:
  dbt_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_audit` as artifact_id, `dbt Audit` as artifact_name, and the `file` value from `artifacts.dbt_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_audit` as artifact, `validate` as action.

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
