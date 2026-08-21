---
description: Cost-guarded sandbox build: refs deferred to prod state, writes gated to the scratch dataset, exact-name selectors, dry-run cost screen
argument-hint: <release-folder> --models <list> [--allow-graph] [--override-budget] [--dry-run]
---

# Cost-guarded sandbox build: refs deferred to prod state, writes gated to the scratch dataset, exact-name selectors, dry-run cost screen

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
description: Cost-guarded sandbox build of translated models — refs deferred to prod state, writes gated to the scratch dataset, exact-name selectors enforced, dry-run cost screen before every build
argument-hint: <release-folder> --models <name[,name...]> [--project <name>] [--allow-graph] [--override-budget] [--dry-run] [--full-refresh]
---

## Data Safety — Read Before Proceeding

Before running any build, read `data_safety` from status.md and output the standard reminder (`equivalency-validate` shows the format). All writes go to the scratch dataset only (`migration.cost_controls.scratch_dataset`); the source platform and every `data_safety.production_projects` entry are never written to. If a resolved selector would materialise outside the scratch dataset, stop and report the conflict.

---

# dbt Migration — Defer Build

## Purpose

Builds translated models in a sandbox so equivalency lanes and pre-raise smoke checks have relations to compare, without paying for (or risking) a full-graph build. Three guards, all mandatory, promoted into the framework from an engagement-local script after a sandbox build defect caused a four-figure single-day scan cost:

1. **Refs defer to prod state** — the build reads upstream relations from the deployed production state (dbt `--defer --state <prod manifest>`), so building one model never rebuilds its ancestry.
2. **Writes gated to the scratch dataset** — materialisations land only in `migration.cost_controls.scratch_dataset`.
3. **Exact-name selectors, cost-screened** — graph operators are refused by default, and every build is preceded by a dry-run cost estimate charged against the release's budget.

## Selector guard (deterministic)

Tests mirror these rules exactly (`wire/tests/platform_migration/validate_defer_build_guard.py`).

`--models` takes a comma-separated list. Each selector is evaluated independently:

- A selector matching `^[A-Za-z0-9_]+$` is an **exact model name**: allowed.
- Any other selector — graph operators (`+model`, `model+`, `@model`), method selectors (`tag:`, `path:`, `state:`, any `:`), wildcards (`*`), or path separators (`/`) — is a **graph selector**: refused with reason `graph_selector` unless `--allow-graph` was passed, in which case it is allowed and flagged `graph_expansion: true` in the output (the operator chose to pay for the expansion, and the run records that choice).
- An empty `--models` list (or the flag absent) is refused with reason `empty_selector` — this command never builds "everything" implicitly.

## Cost screen (deterministic)

Before building, estimate the run's cost and apply the budget rule (same test file):

| Condition | Action |
|---|---|
| `per_run_budget` is null | `proceed_warn` — build, print the estimate with a "no budget set" warning |
| estimate <= `per_run_budget` | `proceed` |
| estimate > `per_run_budget`, `--override-budget` passed | `proceed_flagged` — build, record the override in the run output |
| estimate > `per_run_budget`, no override | `block` — do not build; print the estimate, the budget, and the per-model breakdown |

The same rule applies against `daily_budget` using the day's cumulative recorded spend (from prior run outputs in `migration/build_runs/`); the stricter of the two outcomes wins. `--dry-run` stops after the screen and prints the estimate without building.

## Warehouse adapters

The estimate and the enforcement mechanics are target-specific; the guard rules above are not.

- **BigQuery (first-class).** Estimate: `bq --dry_run` (or the MCP equivalent via `specs/utils/bigquery_mcp_fallback.md`) over each model's compiled SQL; unit `gb_scanned`. Enforcement: set `maximum_bytes_billed` on the build connection to the remaining budget. After the build, read actual bytes billed per model from `INFORMATION_SCHEMA.JOBS_BY_PROJECT` and record them. External tables dry-run at 0 bytes: flag them `estimate_unreliable` and use object-size metadata as the estimate instead. dbt tests over large relations scan like builds: the screen covers `dbt build`'s test executions too.
- **Snowflake (degraded).** No dry-run pricing exists: estimate from `EXPLAIN` partition/byte counts as an approximation, unit `credits`, and mark every estimate `approximate`. Enforcement is warn-based (no hard equivalent of `maximum_bytes_billed`); record actual credits from `QUERY_HISTORY` after the run.
- **Other targets.** Screen unavailable: print a warning, treat the estimate as unknown, and apply the null-budget rule.

## Tenant carve-out (v3.11.1)

Two adaptations when `migration.scope == tenant_carveout`:

- **Tenant write guard (mechanical).** Every materialisation must land inside `migration.target_project` (the tenant project). A resolved write target in any other project is refused with reason `tenant_write_guard` — no override flag exists for this one; a carve-out that writes outside its tenant project is a data-isolation defect, not a cost decision. Tests mirror the rule (`wire/tests/platform_migration/validate_defer_build_guard.py`, tenant cases).
- **Unresolved-predicate drop (v3.11.3).** Before building, resolve each selected model against `migration/tenant_predicate_registry.csv` (`specs/utils/tenant_predicate_registry.md`). A model whose `mechanism` is `unresolved`, or that has no registry row, is **dropped from the build set** with reason `unresolved_predicate` and reported — the write guard has nothing to check the model's scoping against, and building it materialises an unknown row set into the tenant project. `object_carve` and `inherited` models build normally: their absent filter is a resolved answer. Like the write guard, this drop has no override; unlike it, the fix is cheap — resolve the model's registry row (`dbt-carveout-relocate-generate`'s ladder, or a ruling) and re-run.
- **Defer-state fallback.** Early in a carve-out the tenant project has no production manifest to defer to. Resolve the defer state in order: the tenant project's own prod manifest if one exists; else the parent migration's prod manifest (`migration.parent_target_project`, the `dbt-carveout-relocate` case — upstream refs resolve to the parent's relations, read-only); else stop and report that the run needs `--no-defer` (a full build of the selected models' ancestry into the scratch dataset, cost-screened like everything else).

## Build-slot lock (mechanical)

One dbt build per project at a time (the fleet rule, `specs/utils/migration_fleet.md`). Before building, create `migration/locks/build_{project}.lock` containing the lane id and a UTC timestamp; if the file already exists and is younger than 60 minutes, refuse to start and report who holds it. Remove the lock when the build ends, success or failure. A lock older than 60 minutes is stale: report it, remove it, proceed.

## Workflow

### Step 1 — Resolve scope and screen it
Apply the selector guard to `--models`. Resolve the prod state manifest (the deployed target project's manifest; if none is available, stop and report — defer needs a state to defer to). Compile the in-scope models, run the cost screen, and stop here if it blocks (or if `--dry-run`).

### Step 2 — Acquire the build slot and build
Take the build-slot lock for `--project` (default: the release's single dbt project). Run `dbt build` with `--defer --state <prod manifest>`, `--select` set to the exact resolved names, writes to the scratch dataset, and the warehouse-level cost cap where the adapter supports one. Release the lock.

### Step 3 — Record the run
Append one entry to `migration/build_runs/build_runs.md`: UTC timestamp, lane id, models, estimate, actual cost, budget outcome (`proceed`/`proceed_warn`/`proceed_flagged`), per-model build result. Print the cost line: estimated vs actual vs remaining daily budget.

### Step 4 — Update status

```yaml
artifacts:
  dbt_migration:
    defer_build:
      last_run_date: "{{TODAY}}"
      models_built: <n>
      models_failed: <n>
      run_cost: "<actual, with unit>"
      day_cost_cumulative: "<sum for the day, with unit>"
```

## Notes for the implementer

- This command builds; it never compares. Equivalency lanes and `dbt-migration-batch-raise`'s smoke build invoke it and then run their own checks over the scratch relations.
- The guard exists because graph selectors silently defeat defer: `+model` pulls the ancestry into the build and the scan cost multiplies. Refusing them by default converts an expensive surprise into an explicit choice.
- Keep platform specifics in the adapter section; the guard, the screen rule, and the lock are target-neutral.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `defer_build` as action.

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
