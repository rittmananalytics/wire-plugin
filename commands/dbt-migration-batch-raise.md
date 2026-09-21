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
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'dbt-migration-batch-raise',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

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
description: Register-driven PR shipping pipeline — derive gate-passing candidates, smoke-build from the client branch, pre-raise comparison, drop-on-defect, raise with an evidence-first body, watch CI
argument-hint: <release-folder> [--wave id | --batch N | --models list] [--max-models N] [--repo-role transformation] [--allow-stack-depth N] [--dry-run]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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

## Stack depth — batches do not stack (v3.11.2)

Independent batches off the client's own base branch, not a chain. A batch branch cut from another branch that has not merged yet is refused by default.

**The rule (deterministic).** Tests mirror it exactly (`wire/tests/platform_migration/validate_batch_raise_stack_depth.py`). Walk the base chain outward from the branch this run would cut its batch branch from, up to but excluding the client's configured base branch (`migration.client_repos[].base_branch`). `stack_depth` is the number of branches in that chain that have not merged into the base branch (`git merge-base --is-ancestor <branch> <base_branch>`, confirmed against `gh pr view` where a PR exists). A branch cut straight from the client's base branch has depth 0. A merged RA branch in the chain contributes nothing: its commits are already in the base.

| Condition | Behaviour |
|---|---|
| `stack_depth <= --allow-stack-depth` (default `0`) | Proceed |
| `stack_depth > --allow-stack-depth` | **Refuse the run.** Reason `stack_depth_exceeded`. Print the chain, branch by branch, with each branch's merge state and PR url |
| Proceeding with `stack_depth > 0` | Allowed only under an explicit `--allow-stack-depth`, and the merge order of the whole chain goes in the PR body **and** in the post to the client. A stack the client cannot see the order of is a stack the client cannot merge |

Both an unmerged RA branch and an unmerged client branch count toward the depth: the review deadlock comes from the dependency, not from who authored it.

**Why refuse rather than warn.** Two engagements a month apart each built a deep chain of dependent PRs, and both ended the same way: client review stalled on the base of the chain, nothing below it could merge, and the chain was consolidated late — one of them closing five PRs unmerged. Stacking looks like it preserves work in progress and instead couples every PR's fate to the slowest review in the chain.

**What to do instead.** Prefer drop-on-defect batches (Step 4). A model that is not ready is dropped from the batch and picked up by the next run, which raises independently off the client's base branch; the surviving models merge on their own review clock. When two batches genuinely touch the same file, raise the first, wait for the merge, and let Step 1 re-derive the second from the register — the register is what carries the state between runs, not a branch chain.

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

Apply the stack-depth rule before cutting the branch: resolve the base chain, compute `stack_depth`, and refuse the run with `stack_depth_exceeded` if it exceeds `--allow-stack-depth` (default `0`). The default path — branch straight from the client's base branch — is depth 0 and needs no flag.

### Step 3 — Smoke-build from the branch's own checkout
Run `dbt-migration-defer-build` against **the branch checkout** (not the delivery tree) for the batch models: refs deferred to prod state, writes to the scratch dataset, cost-screened. A model that fails to build is dropped from the batch (`smoke_build_failed`), never patched in place; the rest proceed.

### Step 4 — Pre-raise comparison
Run `equivalency-validate $ARGUMENTS --run-point pre_raise --models <batch>` over the scratch relations just built. Mandatory under `ship_then_verify`; under `equivalence_before_pr` it re-confirms the standing verdicts against the exact files being shipped. Any model whose pre-raise verdict is `fail` is dropped (`pre_raise_fail`). **Drop-on-defect only**: a dropped model never blocks the surviving batch, and every drop is listed in the PR body and the batch manifest with its reason.

### Step 5 — CI parity
Run `utils-ci-parity` against the branch (`specs/utils/client_ci_parity.md`). Each check runs in a CI-faithful environment (its Step 2b): a clean environment carrying only the variables the pipeline config sets plus `CI=true`, never the operator's, with the repo's own profiles and toolchain, and the check's own working directory and iteration scope from the config. Fix locally and re-run until green; any `fail` blocks the raise. A check that cannot be replicated locally is listed in the PR body as `not_locally_verified`; a check that passed with recorded deviations from the CI definition is `pass_with_env_deltas` and passes the gate with its deltas listed.

### Step 5b — New-project coverage (#219)

Step 5 replicates the client's existing checks; it proves they pass where they already look. When the batch ships models into a **dbt project new to the client repo** (its `dbt_project.yml` is absent from the base branch, the carve-out case), that is not enough: the client's project-scoped gates may simply never look at the new project, and green parity then proves nothing about it. On one carve-out, every project-enumerating gate (DAG presence, PII policy tags, source-yml checks, vars hidden under `tests/generic/`) was blind to the new project, and no DAG built it: 86 models would have merged as dead code.

Both checks below are blocking; tests mirror the classification (`wire/tests/platform_migration/validate_carveout_ship_gates.py`):

1. **Enumerating-gate coverage.** From the Step 5 pipeline parse, identify each client CI gate that **enumerates projects** (a discovery glob such as `*/dbt_project.yml`, a hardcoded project list, a directory loop) and record where each one discovers its projects. Confirm the new project is picked up by every enumerating gate: the glob structurally matches it, or the list/loop is updated on this branch. Any enumerating gate blind to the new project is a blocking finding, `new_project_not_enumerated`, naming the gate and its discovery mechanism.
2. **DAG reachability.** Resolve the orchestration DAGs that build dbt models (from the `orchestration` repo role in `migration.client_repos` where the repos are split, else this repo) and each DAG's selection (selectors, project directories, job commands). Every enabled model in the raise must be reachable from at least one DAG's selection. Each unreachable model is a blocking finding, `model_unreachable_from_dag`, listed per model: a model no DAG builds merges as dead code, whatever its verdict says.

**Operational corollary — grants-first-or-pause.** Where the client's orchestration platform deploys DAGs unpaused on merge, a new project's DAG starts running before anyone touches it. Verify the new project's warehouse grants (the DAG's service account, datasets, write paths) are in place before the raise, or ship the DAG paused and unpause only after grants are verified. Record which of the two applies in the PR body; the cutover runbook carries the same step (`cutover-generate` Step 2).

### Step 6 — Raise
Title standard: `[wire] <release> <wave/batch>: <n> models — <one-line scope>`. Body is **evidence-first**, in order: the batch manifest table (model, file version, verdict, run point); the pre-raise comparison summary with report link; the smoke-build cost line; drops and reasons; the CI parity stage table; only then prose. The CI parity stage table is one row per check, not a summary line: check name, the command as the pipeline defines it, result (`pass` / `pass_with_env_deltas` with its deltas / `not_locally_verified`). A `fail` never reaches the body: Step 5 blocks the raise on it. Any model shipping on a `declared_window_availability` verdict (possible under `ship_then_verify` only) renders its window as structured fields in the manifest table — floor, floor derivation, cap, exclusions with reasons, and the in-window pass — taken verbatim from the verdict row's `window` object (`specs/migration/equivalency/verdict_schema.md`), never re-argued in prose. A new-project raise (Step 5b) additionally carries the coverage summary: each enumerating gate and where it discovers the new project, the DAG-reachability result per model, and the grants-first-or-pause disposition. Raise with `gh pr create` against the configured base branch. When `stack_depth > 0` (an explicit `--allow-stack-depth` run), the body opens with the merge order of the chain, base first, and the same order goes in the post to the client. Never force-push; never rebase an open batch branch (merge the base branch in if it moves).

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
      base_branch: "<branch the batch was cut from>"
      stack_depth: <n>            # 0 for an independent batch
      allow_stack_depth: <n>      # the flag value this run ran under
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
