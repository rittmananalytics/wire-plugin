---
wire_schema: "1.0"
command: utility
artifact: equivalency
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
  - artifact: orchestration_migration
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Post-merge production verification — wait for the client pipeline to materialise merged models, compare production tables at the full verdict bar, advance the register to production_verified
argument-hint: <release-folder> [--models list] [--no-wait] [--wait-timeout minutes]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Equivalency — Post-Merge Verify

## Purpose

The assurance state the register's `merged` stage deliberately is not: a merged model has been accepted by the client, but nothing yet proves the production build of that model produces equivalent rows. This command closes that gap per merged model set. It is a **thin orchestrator**: the waiting and the register stage advance live here; every comparison runs through `equivalency-validate --run-point post_merge_prod`, so there is exactly one comparison engine.

## Scope

Default scope: every register row with `delivery_stage = merged` and no `run_point = post_merge_prod` row with verdict `pass`/`pass_qualified` in `migration/migration_verdict_log.csv`. `--models` restricts to named models within that set.

## Workflow

### Step 1 — Resolve physical targets, then wait for materialisation (target metadata, not the scheduler)
First resolve each in-scope model's production relation exactly, per `equivalency-validate` Step 1g (#201): the register row's fully qualified `bq_target`, the manifest for a legacy two-segment row, and an existence check, never a name-equality or single-candidate guess. A model whose target cannot be resolved exactly is reported **`unresolved_target`** immediately: no wait, no comparison, never a `pass`, never a silent skip. Report it with what failed to resolve and the fix (run `/wire:upgrade` to re-resolve a legacy register; re-run `/wire:dbt-migration-generate` for a model with no register path).

Then, for each resolved model, poll the resolved relation's table metadata (BigQuery: `INFORMATION_SCHEMA.TABLES` / `__TABLES__` last-modified; Snowflake: `INFORMATION_SCHEMA.TABLES.LAST_ALTERED`) until the object's last-modified instant is later than its PR merge time (from `gh pr view` on the row's `pr_url`). This is deliberately orchestration-tool-agnostic: no scheduler API, whatever runs the client's DAG. Poll at a low cadence (every 10 minutes, `--wait-timeout` default 240). `--no-wait` skips the wait and compares whatever is materialised now, flagging not-yet-rebuilt models `stale_materialisation` and excluding them from verdicts. On timeout, report the unmaterialised set and proceed with the rest.

### Step 2 — Compare in production
Invoke `equivalency-validate $ARGUMENTS --run-point post_merge_prod --models <materialised set>` (the resolved, materialised models; `unresolved_target` models are already out). The target side is the **production** dataset (the merged models' real relations), not the scratch dataset; the source side and every check, pin, and taxonomy rule are exactly as that command specifies. The full verdict bar applies — this run point exists to catch what a sandbox cannot (production partitioning, prod-only data, the client's own build), so it is never run at a reduced bar.

### Step 3 — Advance the register
The merge step of `equivalency-validate` (rules in `specs/migration/equivalency/verdict_schema.md`) records the `post_merge_prod` verdicts in the verdict log and advances `delivery_stage` to `production_verified` for `pass`/`pass_qualified`. Divergent models keep `delivery_stage: merged`; each divergence is drilled to a named mechanism, and any `fail` (a translation defect that reached production) is escalated immediately: report it, reference `equivalency-investigate`, and flag it for the defect-class flywheel (sweep the estate for the same class).

### Step 4 — Update status and report

```yaml
artifacts:
  equivalency:
    post_merge_verify:
      last_run_date: "{{TODAY}}"
      models_verified: <n>
      models_divergent: <n>
      models_unmaterialised: <n>
      models_unresolved_target: <n>
```

Output: the verified/divergent/unmaterialised/unresolved counts, each divergence with its mechanism, each `unresolved_target` model with what failed to resolve and its fix, and, when divergent, unmaterialised, or unresolved models remain, the re-run line:

```
/wire:equivalency-post-merge-verify $ARGUMENTS
```

## Tenant carve-out (v3.11.1)

Nothing changes structurally — the comparison runs through `equivalency-validate`, which under `tenant_carveout` scope already applies the tenant predicate to the source side (the target side, a single-tenant project, is whole by construction) and the relocate-mode comparator for `origin: relocate` models. Verdict rows carry `scope` and the predicate hash, so a carve-out's production verification is never mistakable for a full-estate one.

## Notes for the implementer

- Keep this command free of comparison logic. If a check needs to differ at this run point, the change belongs in `equivalency-validate`, keyed off `--run-point`, not here.
- A `post_merge_prod` divergence with a benign mechanism (e.g. prod partition filter semantics) is a `diff_*` verdict, not a silent pass — the named-mechanism discipline applies with extra force in production.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact, `post_merge_verify` as action.
3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `equivalency` as artifact, `post_merge_verify` as action.
