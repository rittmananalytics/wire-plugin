---
description: Build and maintain the per-model migration register (source commit, BQ target, state, last equivalence)
argument-hint: <release-folder>
---

# Build and maintain the per-model migration register (source commit, BQ target, state, last equivalence)

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
description: Build and maintain the per-model migration register — the source-of-truth state store for what has been migrated, from which source commit, to which BigQuery target, and how it last validated
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_register` and `artifact_file_path: migration/migration_register.csv` before proceeding.

---

# Migration Register — Generate

## Purpose

Maintains a **per-model migration register** — one row per in-scope model recording what was migrated, from which source commit, to which BigQuery target, its current state, and how it last validated. This is the queryable source of truth that the drift gate, the equivalency loop, and CI all read; it is distinct from the per-model transformation **log** (`migration.transformation_log_table`), which is an append-only audit trail, not current state.

The register is maintained **incrementally** by the migration commands (see the maintenance contract below). This command initialises it, and rebuilds/reconciles it on demand.

## Register schema

`.wire/releases/$ARGUMENTS/migration/migration_register.csv`:

| Column | Meaning |
|--------|---------|
| `model` | dbt model **or snapshot** name (unique key) |
| `object_type` | `model` (default) or `snapshot` — a snapshot is an SCD-2 history object, tracked here so its migration strategy and state travel with everything else |
| `source_path` | path to the model/snapshot in the source dbt project (e.g. `models/business/orders.sql`, `snapshots/orders_snapshot.sql`) |
| `source_layer` | source-project layer (e.g. `source_project`, `business_project`, `reporting`) |
| `last_migrated_commit` | source repo commit SHA the translated model was built from |
| `bq_target` | the BigQuery target object (`dataset.table`) — for a snapshot, its `target_schema` relation |
| `state` | `pending` \| `migrated` \| `drifted` \| `failed` \| `removed` \| `deferred` |
| `snapshot_strategy` | for `object_type = snapshot`: `copy_and_continue` (default) or `rebuild_from_T` — blank for models. `rebuild_from_T` is valid only with a sign-off recorded in `notes` (see below) |
| `last_equivalence_result` | `pass` \| `fail` \| `info` \| `null` — outcome of the last equivalency run for this object |
| `last_equivalence_t` | the baseline instant `T` of that equivalency run (UTC), or `null` for a live run |
| `last_validated_commit` | source commit at the last equivalency validation (lets the drift gate tell "validated-then-drifted" from "never validated") |
| `notes` | free text (e.g. reason for `deferred`/`failed`; for a `rebuild_from_T` snapshot, the required data-owner sign-off — name + date) |

## Maintenance contract (which command writes which columns)

- **`dbt-migration-generate`** — on a successful per-model migration, upserts the row: `source_path`, `source_layer`, `last_migrated_commit` (the source snapshot SHA, from `migration_sources.dbt.commit`), `bq_target`, `state = migrated` (or `failed` after 5 iterations, `deferred` if its source object isn't built on target). For a **snapshot** (`object_type = snapshot`), it upserts the same way after translating the inner SELECT and running the target `dbt snapshot` adopt-and-continue, leaving `snapshot_strategy` as seeded.
- **`migration-strategy-generate` / this command** — sets each snapshot row's `snapshot_strategy` (`copy_and_continue` default; `rebuild_from_T` only with the sign-off recorded in `notes`).
- **`equivalency-validate`** — on each run, writes `last_equivalence_result`, `last_equivalence_t` (the baseline `T` when in baseline mode, else `null`), and `last_validated_commit` for each model checked.
- **`migration-drift-generate`** — flips `state` to `drifted` (modified upstream) or `removed`, and records the drifting commit in `notes`.

This command does not duplicate that logic — it seeds and reconciles the file.

**Snapshot rows.** Snapshots are seeded here as `object_type = snapshot` rows from `audit/dbt_snapshots.csv`, and their `snapshot_strategy` is set from the migration strategy's "Snapshot migration" section (`copy_and_continue` by default; `rebuild_from_T` only when the strategy records a data-owner sign-off, which this command copies into `notes`). If the strategy doc has not yet assigned a strategy, seed the snapshot `copy_and_continue` and leave a note — never default a snapshot to `rebuild_from_T`, since that silently discards history.

## Prerequisites

- `audit/dbt_audit.csv` exists (the in-scope model list); `audit/dbt_snapshots.csv` too if the project defines snapshots
- `migration_sources.dbt` registered (so `last_migrated_commit` can be resolved)

## Workflow

### Step 1: Seed or reconcile

If the register does not exist, create it from `TEMPLATES/migration/migration_register.csv` and seed one row per in-scope model from `dbt_audit.csv` (`object_type = model`), plus one row per snapshot from `dbt_snapshots.csv` (`object_type = snapshot`, `snapshot_strategy` from the strategy doc as above), all with `state = pending` and all migration/validation columns `null`.

If it exists, **reconcile** rather than overwrite: add rows for any new in-scope models (`state = pending`); never clobber `last_migrated_commit` / `last_equivalence_*` / `last_validated_commit` already recorded; mark rows whose model no longer exists in the dbt audit as `state = removed` (do not delete the row — the history matters).

### Step 2: Backfill from existing artifacts (first run)

On first creation, backfill state from what already happened: read the batch acceptance packs and per-model `.diff.md` files to set `state` (`migrated`/`failed`) and `last_migrated_commit` where derivable; read the latest equivalency report to set `last_equivalence_result` / `last_equivalence_t` / `last_validated_commit`. Leave unknown fields `null` rather than guessing.

### Step 3: Write the register and update status

Write `migration/migration_register.csv`. Update status.md:

```yaml
artifacts:
  migration_register:
    generate: complete
    file: migration/migration_register.csv
    generated_date: "{{TODAY}}"
    models_total: N
    migrated: N
    drifted: N
    pending: N
    failed: N
    snapshots_total: N            # object_type = snapshot rows; 0 if none
    snapshots_rebuild_from_t: N   # snapshots assigned rebuild_from_T (each requires a recorded sign-off)
```

### Step 4: Output next command

```
/wire:migration-register-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_register` as artifact_id, `Migration Register` as artifact_name, and the `file` value from `artifacts.migration_register` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_register` as artifact, `generate` as action.

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
