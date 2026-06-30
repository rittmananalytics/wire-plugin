---
description: Scheduled drift gate — diff live source vs last-migrated commit, flag downstream syncs and masking changes
argument-hint: <release-folder>
---

# Scheduled drift gate — diff live source vs last-migrated commit, flag downstream syncs and masking changes

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
description: Scheduled drift gate — diff the live source dbt repo against each migrated model's last-migrated commit, classify new/modified/removed, flag downstream Hightouch syncs, and trigger the masking-policy hook
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_drift` and `artifact_file_path: migration/migration_drift_report.md` before proceeding.

---

# Migration Drift — Generate

## Purpose

A **scheduled drift gate**. During a long migration the source platform keeps changing — models are added, edited, and removed while batches are being translated and validated. This command diffs the **live** source dbt repo against the commit each model was last migrated from (recorded in the migration register), classifies what changed, updates register state, and surfaces the blast radius: which migrated models drifted, which downstream Hightouch syncs they feed, and whether a masking-policy change needs the policy tags regenerated.

It is designed to run on a schedule (see "Scheduling" below) and as a CI gate on the BigQuery project, so drift is caught the day it happens rather than during a cutover scramble.

## Prerequisites

- `migration/migration_register.csv` exists (`migration-register generate: complete`)
- `migration_sources.dbt` registered — the live source dbt repo
- A dbt binary available **only** for `dbt ls` state comparison (no warehouse connection needed for `ls`), or the manifest-diff fallback below

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_register.csv` — last-migrated commit per model
- `migration_sources.dbt` (live repo + local snapshot) — the current source state
- `audit/lineage/model_sync_map.json` (from `lineage-generate`) — Gold→Hightouch edges (which syncs read each warehouse model)
- `audit/reverse_etl_audit.md` — the Hightouch sync inventory and config references
- Source model `meta.masking_policy` declarations (schema/properties YAML)

## Workflow

### Step 1: Refresh the live source

Run (or confirm a fresh) `/wire:migration-source-refresh $ARGUMENTS dbt` so the comparison is against the current source HEAD, not a stale snapshot. Record the live HEAD commit as `drift_head`.

### Step 2: Per-model state diff

For each `state = migrated` row in the register, compare its `last_migrated_commit` against `drift_head`. Use dbt's state comparison — **`dbt ls --select state:modified`** against a manifest built at `last_migrated_commit` as the `--state` baseline:

```
dbt ls --select state:modified --state <manifest@last_migrated_commit> --output name
```

`dbt ls` needs no warehouse connection. **Fallback (no dbt binary):** diff the model's `.sql` and its companion YAML between `last_migrated_commit` and `drift_head` with `git diff --name-status`, and parse `ref()`/`source()` + `{{ config() }}` to approximate modified/added/removed.

Classify each model:
- **modified** — the model (or its compiled definition / config / upstream refs) changed since `last_migrated_commit`. Set register `state = drifted`, record `drift_head` and a one-line change summary in `notes`.
- **removed** — the model no longer exists at `drift_head`. Set `state = removed`.
- **new** — a model present at `drift_head` with no register row. Add a row with `state = pending` (it needs migrating).
- **unchanged** — leave `state` as-is.

A model that drifted but whose `last_validated_commit` equals its old `last_migrated_commit` is flagged **"validated, now drifted"** — its prior equivalency pass is stale.

### Step 3: Flag downstream Hightouch syncs (Gold→Hightouch lineage)

For every model classified **modified** or **removed**, resolve its downstream Hightouch syncs from `model_sync_map.json` (emitted by `lineage-generate`). A re-migrated or removed Gold model flags every sync that reads it: those syncs must be re-validated (modified) or re-pointed/retired (removed). List each flagged sync with the model that triggered it.

### Step 4: Hightouch config diff

For each flagged sync, produce a **Hightouch config diff**: compare the sync's current config in the GitHub-Sync repo (model SQL, field mappings, filters) against what `reverse-etl-migration` translated, and show what the upstream drift implies — e.g. a renamed/removed column the sync's model SQL still references. This tells the reverse-ETL owner exactly what to re-translate, rather than just "something upstream changed."

### Step 5: Masking-change hook

For each **modified** model, diff its source `meta.masking_policy` (in the model's schema/properties YAML) between `last_migrated_commit` and `drift_head`. If `meta.masking_policy` was **added, changed, or removed** on any column, flag a **masking change** and trigger the policy-tag generator: re-run the `target-setup` security step (`04_security.sql` policy-tag taxonomy / data policies) for the affected objects so the BigQuery policy tags match the new source masking. Record which columns changed and that the policy-tag regeneration is required (do not silently let masking drift — a dropped masking policy that isn't re-applied is a data-exposure risk; a new one that isn't applied breaks the consuming role).

### Step 6: Write the drift report

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_drift_report.md`

Use `TEMPLATES/migration/migration_drift_report.md`. Include: `drift_head` and the run timestamp; counts (modified / removed / new / unchanged); the per-model drift table (model, classification, change summary, prior equivalence state); the flagged downstream syncs with their config diffs; and the masking changes with the policy-tag regeneration actions. Re-write the affected register rows (Step 2).

### Step 7: Update status

```yaml
artifacts:
  migration_drift:
    generate: complete
    file: migration/migration_drift_report.md
    last_run_date: "{{TODAY}}"
    drift_head: "<commit>"
    modified: N
    removed: N
    new: N
    syncs_flagged: N
    masking_changes: N
```

### Step 8: Output next command

```
/wire:migration-drift-validate $ARGUMENTS
```

If any models drifted: re-migrate them (`/wire:dbt-migration-generate $ARGUMENTS --select <drifted models>`), then re-run equivalency in baseline mode and, where masking changed, re-run `target-setup`.

## Scheduling

This gate is meant to run unattended. Deploy it two ways (templates in `TEMPLATES/migration/ci/`):

- **Scheduled** — `migration-drift-schedule.yml`: a cron GitHub Actions workflow on the delivery repo that refreshes the source and runs this drift check (e.g. nightly), opening/annotating an issue when drift is found.
- **On-change CI** — `migrated-model-ci.yml`: on any change to a migrated model (path filter derived from the register's `source_path` column), re-run compile + the tiered sweep (Tier 1 `dbt-migration-lint` + Tier 3 `equivalency-validate --baseline`).

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_drift_report.md`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact_id, `Migration Drift` as artifact_name, and the `file` value from `artifacts.migration_drift` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_drift` as artifact, `generate` as action.

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
