---
description: Validate the migration register — schema, coverage, state consistency
argument-hint: <release-folder>
---

# Validate the migration register — schema, coverage, state consistency

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
description: Validate the per-model migration register — schema, uniqueness, coverage, and state consistency
---

# Migration Register — Validate

## Validation Checks

Read `migration/migration_register.csv`, `audit/dbt_audit.csv`, and the latest equivalency report.

**Check 1 — Schema present**
The header carries all fourteen columns: `model, object_type, source_path, source_layer, last_migrated_commit, bq_target, state, snapshot_strategy, last_equivalence_result, last_equivalence_t, last_validated_commit, delivery_stage, pr_url, notes`. A twelve-column register predating v3.11.0 is a FAIL with the fix hint "run /wire:upgrade to add delivery_stage and pr_url".
PASS/FAIL.

**Check 2 — One row per in-scope model and snapshot, unique key**
Every in-scope model from `dbt_audit.csv` has exactly one `object_type = model` row, and every snapshot from `dbt_snapshots.csv` has exactly one `object_type = snapshot` row; `model` is unique across both; no orphan rows except those marked `state = removed`.
PASS/FAIL with missing/duplicate models and snapshots.

**Check 3 — State values valid**
Every `state` is one of `pending | migrated | drifted | failed | removed | deferred`.
PASS/FAIL with offending rows.

**Check 4 — Migrated rows are complete**
Every `state = migrated` row has a non-null `last_migrated_commit` and `bq_target`. A migrated model with no recorded source commit can't be drift-checked.
PASS/FAIL.

**Check 5 — Equivalence fields consistent**
`last_equivalence_result` is one of `pass | pass_qualified | diff_vintage | diff_availability | diff_schema_type | fail | null` (the verdict taxonomy; the legacy value `info` is accepted with a warning and read as `pass_qualified`); when it is non-null, `last_validated_commit` is set. `last_equivalence_t` is a UTC instant or null.
PASS/FAIL.

**Check 6 — Validated-vs-migrated coherence**
No row claims `last_equivalence_result = pass` with a `last_validated_commit` that predates `last_migrated_commit` (would mean it was validated before it was (re)migrated).
PASS/FAIL with offending rows.

**Check 7 — Snapshot strategy valid and signed off**
Every `object_type = snapshot` row has a `snapshot_strategy` of exactly `copy_and_continue` or `rebuild_from_T`; every `object_type = model` row has a blank `snapshot_strategy`. Every `rebuild_from_T` row records a data-owner sign-off in `notes` — a `rebuild_from_T` with no sign-off is a FAIL. A blank `snapshot_strategy` on a snapshot row is also a FAIL (a snapshot must never be left unassigned, which would risk defaulting to a history-discarding rebuild).
PASS: every snapshot row has a valid, signed-off-where-required strategy. FAIL: list offending rows. Note "no snapshot rows" when none exist.

**Check 8 — Delivery stage consistent**
Every `delivery_stage` is blank or one of `in_pr | merged | production_verified`. A non-blank `delivery_stage` requires `state = migrated` or `state = drifted` (delivery progress survives drift; it cannot precede migration). `in_pr` requires a non-blank `pr_url`. `production_verified` requires at least one `run_point = post_merge_prod` row with verdict `pass` or `pass_qualified` for the model in `migration/migration_verdict_log.csv` (skip this sub-check with a warning if the log is absent).
PASS/FAIL with offending rows.

**Check 9 — Verdict log well-formed (when present)**
If `migration/migration_verdict_log.csv` exists: the header carries `model, object_type, run_point, verdict, divergence_mechanism, method_class, mode, baseline_t, file_version, lane_id, report_ref, written_at`; every `run_point` is one of `standard | pre_raise | post_merge_prod`; every `verdict` is a taxonomy value; every verdict other than `pass` has a non-blank `divergence_mechanism`; `written_at` values are non-decreasing down the file (append-only order).
PASS/FAIL with offending rows. Note "no verdict log" when the file does not exist.

### Update status

```yaml
artifacts:
  migration_register:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact_id, `Migration Register` as artifact_name, and the `file` value from `artifacts.migration_register` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_register` as artifact, `validate` as action.

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
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
