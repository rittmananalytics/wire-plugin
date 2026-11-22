---
wire_schema: "1.0"
command: utility
artifact: dbt_migration
domain: migration
release_types:
  - platform_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: ingestion_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Cost-guarded sandbox build of translated models — refs deferred to prod state, writes gated to the scratch dataset, exact-name selectors enforced, dry-run cost screen before every build
argument-hint: <release-folder> --models <name[,name...]> [--project <name>] [--allow-graph] [--override-budget] [--dry-run] [--full-refresh]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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

One dbt build per project at a time (the fleet rule, `specs/utils/migration_fleet.md`). On Claude Code the Wire mod holds the slot in its own state for any lane's `dbt build`, `run`, `snapshot` or `seed` (wire#270), so a second lane's build on the same project is refused before the command runs; the file lock below is the Gemini CLI path and the backstop where the mod is off. Before building, create `migration/locks/build_{project}.lock` containing the lane id and a UTC timestamp; if the file already exists and is younger than 60 minutes, refuse to start and report who holds it. Remove the lock when the build ends, success or failure. A lock older than 60 minutes is stale: report it, remove it, proceed.

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
