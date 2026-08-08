---
description: Register-driven PR shipping pipeline: derive gate-passing candidates, smoke-build from the client branch, pre-raise comparison, drop-on-defect, raise with evidence-first body
argument-hint: <release-folder> [--wave id 
---

# Register-driven PR shipping pipeline: derive gate-passing candidates, smoke-build from the client branch, pre-raise comparison, drop-on-defect, raise with evidence-first body

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
description: Register-driven PR shipping pipeline — derive gate-passing candidates, smoke-build from the client branch, pre-raise comparison, drop-on-defect, raise with an evidence-first body, watch CI
argument-hint: <release-folder> [--wave id | --batch N | --models list] [--max-models N] [--repo-role transformation] [--dry-run]
---

# dbt Migration — Batch Raise

## Purpose

The pipeline between "migrated in the register" and "in a client PR". Before this command existed the chain ended at `dbt-migration-pre-pr-review` with prose ("do not open the PR until every error is cleared") and the raise itself was free-form every time. This command makes the raise a gate: candidates are derived from the register, the batch is built and compared from the client branch's own checkout, defective models are dropped (never the whole batch), and the PR carries its evidence.

## Configuration

- `migration.gate_policy` — `equivalence_before_pr` (default) or `ship_then_verify`. The second requires a recorded client ruling (`migration.gate_policy_ruling`); refuse to run under `ship_then_verify` with a null ruling.
- `migration.client_repos` — the target repo for `--repo-role` (default `transformation`): url and base branch. If the list is empty, ask the user once for the repo and base branch, write the answer to status.md, then proceed.

## Eligibility (deterministic)

Tests mirror this table exactly (`wire/tests/platform_migration/validate_batch_raise_gating.py`). A model is a candidate when every row applies; the first failing row is the recorded block reason.

| # | Rule | Block reason |
|---|---|---|
| 1 | `state = migrated` and `delivery_stage` blank (not already shipped or in flight) | `not_ready` |
| 2 | `dbt-migration-validate` passed and `dbt-migration-lint` has no open error-severity finding and `dbt-migration-pre-pr-review` has no open error for the model's scope | `gate_incomplete` |
| 3 | **External-output models** (models whose output leaves the warehouse: a reverse-ETL sync source, an extract, a file export — resolve from the reverse-ETL audit and the inventory's consumer column): latest verdict is exactly `pass`. `pass_qualified` is not sufficient when the rows leave the warehouse, under either policy | `external_exactness` |
| 4 | Under `equivalence_before_pr`: latest verdict is `pass` or `pass_qualified` | `verdict_required` |
| 5 | Under `ship_then_verify`: latest verdict is not `fail` (no verdict yet, or any `diff_*`, is eligible — verification follows the merge) | `recorded_fail` |

`--dry-run` prints the candidate list with per-model block reasons and stops.

## Tenant carve-out (v3.11.1)

When `migration.scope == tenant_carveout`:

- **The default gate policy stands, harder.** The carve-out's deliverable is an isolation proof, so `equivalence_before_pr` remains the default; `ship_then_verify` additionally requires that the `region-tagging-review` (adjudication) and `data-residency-assessment-review` (client DPO/legal) gates are complete before any raise — refuse to run otherwise. A residency ruling is not something to ship ahead of.
- **The comparison threads itself.** The pre-raise comparison (Step 4) runs through `equivalency-validate`, which already applies `migration.tenant_predicate` on both sides — and the relocate-mode comparator (parent target vs tenant target) for `origin: relocate` models. Nothing extra to configure here.
- **The target repo may be new.** A carve-out often ships into the tenant's own new repo rather than the parent client's. `migration.client_repos` carries whichever it is; when the repo has no CI yet, `utils-ci-parity --scaffold-from` derives the parity checks from the parent repo's pipeline (Step 5).

## Workflow

### Step 1 — Derive the batch
Read the register, apply the eligibility table over the scope (`--wave`/`--batch`/`--models`, resolved as `dbt-migration-generate` resolves them; no flag = every eligible model), cap at `--max-models` (default 40 — small batches merge faster). Record the batch manifest: models, file versions, verdicts.

### Step 2 — Branch and copy
Clone/fetch the client repo (role from `--repo-role`), branch from its base branch (`wire-migration/<release>-<wave-or-batch>-<seq>`), copy each candidate's translated files (SQL + companion YAML) to their target paths. Copy exactly the file version the verdict binds to; a working-tree file newer than `last_migrated_commit` is a defect, drop the model (`stale_file`).

### Step 3 — Smoke-build from the branch's own checkout
Run `dbt-migration-defer-build` against **the branch checkout** (not the delivery tree) for the batch models: refs deferred to prod state, writes to the scratch dataset, cost-screened. A model that fails to build is dropped from the batch (`smoke_build_failed`), never patched in place; the rest proceed.

### Step 4 — Pre-raise comparison
Run `equivalency-validate $ARGUMENTS --run-point pre_raise --models <batch>` over the scratch relations just built. Mandatory under `ship_then_verify`; under `equivalence_before_pr` it re-confirms the standing verdicts against the exact files being shipped. Any model whose pre-raise verdict is `fail` is dropped (`pre_raise_fail`). **Drop-on-defect only**: a dropped model never blocks the surviving batch, and every drop is listed in the PR body and the batch manifest with its reason.

### Step 5 — CI parity
Run `utils-ci-parity` against the branch (`specs/utils/client_ci_parity.md`). Fix locally and re-run until green; a check that cannot be replicated locally is listed in the PR body as "not locally verified".

### Step 6 — Raise
Title standard: `[wire] <release> <wave/batch>: <n> models — <one-line scope>`. Body is **evidence-first**, in order: the batch manifest table (model, file version, verdict, run point); the pre-raise comparison summary with report link; the smoke-build cost line; drops and reasons; CI parity result; only then prose. Raise with `gh pr create` against the configured base branch. Never force-push; never rebase an open batch branch (merge the base branch in if it moves).

### Step 7 — Update the register and status
For every raised model: `delivery_stage: in_pr`, `pr_url`. On a later run (or when asked to check), detect merges via `gh pr view`: merged PR advances its models to `delivery_stage: merged` and emits the next step; a PR closed unmerged clears `delivery_stage` and `pr_url`.

```yaml
artifacts:
  dbt_migration:
    batch_raise:
      last_run_date: "{{TODAY}}"
      pr_url: "<url>"
      models_raised: <n>
      models_dropped: <n>
      drop_reasons: {smoke_build_failed: n, pre_raise_fail: n, stale_file: n}
      gate_policy: equivalence_before_pr | ship_then_verify
```

### Step 8 — Output next step

```
Raised <n> models: <pr_url>
After the client merges, verify in production:
/wire:equivalency-post-merge-verify $ARGUMENTS
```

## Notes for the implementer

- This command supersedes the prose ending of `dbt-migration-pre-pr-review` — the review clears the diff, this command ships it.
- Batch composition is by **readiness**, not wave membership: a wave id on the models is a reporting label, and a batch may legitimately span waves when `--models` or bare scope is used.
- The client repo is someone else's production. Everything outward-facing (the raise itself, comments) happens once, at Step 6, after every local gate; there is no "raise then fix up" path.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact, `batch_raise` as action.
3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `batch_raise` as action.

Execute the complete workflow as specified above.
