---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Client CI parity gate — detect the client repo's CI system, replicate its locally-runnable checks against a branch before anything is raised, report pass/fail per check
argument-hint: <release-folder> [--repo <path-or-role>] [--branch <name>]

---

# Utils — Client CI Parity

## Purpose

Client CI rejections are discovered post-raise unless the same checks run locally first. On a live engagement, two PRs bounced off the client's CI for causes that were replicable locally (SQL linting config, DAG validators, a policy-tag validator); a local runner built the same day made the next six raises first-time green on five. This command is that runner as a framework gate: detect what CI the client repo runs, replicate the locally-runnable steps against the branch, and report per-check results before `gh pr create` is ever invoked.

## CI system detection (deterministic)

Tests mirror this mapping exactly (`wire/tests/platform_migration/validate_ci_parity_detection.py`). Detection is by file presence at the repo root, checked in this fixed precedence order; every match is reported (a repo can run more than one system):

| Order | Present | System |
|---|---|---|
| 1 | `.circleci/config.yml` | `circleci` |
| 2 | any `*.yml`/`*.yaml` under `.github/workflows/` | `github_actions` |
| 3 | `.gitlab-ci.yml` | `gitlab_ci` |
| 4 | `Jenkinsfile` | `jenkins` |
| 5 | `azure-pipelines.yml` | `azure_pipelines` |
| 6 | `bitbucket-pipelines.yml` | `bitbucket` |

No match: detection result is `none` — report "no CI detected" as a warning and pass the gate vacuously (there is nothing to be rejected by). Never hardcode a provider anywhere downstream of this table.

## Scaffold mode (v3.11.1)

`--scaffold-from <path-or-role>`: when the target repo has no CI yet (the common case for a tenant carve-out shipping into a brand-new repo), detect and parse the **referenced** repo's pipeline instead, run its locally-runnable checks against the target branch, and write the extracted check list to `migration/ci_parity_scaffold.md` as the starting point for the new repo's own pipeline. Detection on the target repo still runs first; if it finds a CI system, that wins and `--scaffold-from` is ignored with a note — a repo that has grown its own CI is checked against its own CI.

## Workflow

### Step 1 — Resolve the repo and branch
`--repo` accepts a local path or a `migration.client_repos` role (`transformation`/`orchestration`/`reverse_etl`); default role `transformation`. `--branch` defaults to the current branch of that checkout.

### Step 2 — Detect and parse
Apply the detection table. For each detected system, parse the pipeline definition and extract the job steps. Classify each step:

- **Locally runnable** — linters (sqlfluff, ruff, yamllint), compile/parse steps (`dbt parse`, `dbt compile`), custom validator scripts committed to the repo, unit tests with no external service. Run these.
- **Not locally runnable** — steps needing the CI vendor's context (deploy credentials, vendor-hosted caches, approval jobs). List them as `not_locally_verified`; never guess their outcome.

Run each runnable step with the repo's own config files (the client's `.sqlfluff`, not ours), from the branch checkout, in the order the pipeline declares.

### Step 2b — Replicate the CI execution environment (#202)

The repo's own config files are not enough: the run must also replicate the environment CI runs the check in, or it is a different check. The trap is concrete. A local gate naturally runs `dbt parse` in the operator's environment: credentials and profile variables set, warnings tolerated, scoped to the directories the wave touched. Client CI runs `dbt --warn-error parse` with `CI=true`, none of the operator's variables, the repo's own profiles, over every `*/dbt_project.yml` in the repo. Field evidence: on a live engagement, a `dbt_bq_parse` job failed post-raise on an otherwise fully evidenced PR, because the local gate had run the operator-environment version of the check.

Tests mirror the extraction, scope, and result rules exactly (`wire/tests/platform_migration/validate_ci_parity_env_replication.py`). For each runnable check:

1. **Extract the environment.** Take the variables the pipeline config sets for the check's job: the job-level block, the pipeline/workflow-level block (job wins on a clash), plus `CI=true` (every provider in the detection table sets it; an explicit config value for `CI` wins). The extracted set is the whole set: an operator variable the config does not set is not in it.
2. **Run clean.** Run the check in a clean environment carrying only the extracted variables plus the minimum the tool needs to execute (`PATH`, and `HOME` where the tool requires it), never the operator's environment variables. `env -i PATH=... HOME=... CI=true <extracted vars> <command>` is the shape.
3. **Use the repo's own toolchain.** The repo's own profiles, and the tool versions the CI config or the repo's lockfiles pin (image tags, version fields, `requirements.txt`/`packages.yml` pins) where stated. A version that cannot be pinned locally is a recorded delta (Step 3), not a silent substitution.
4. **Honour the check's working directory and iteration scope.** Both come from the config, not from the wave. A CI job that loops every `*/dbt_project.yml` is replicated over every project directory in the repo, including projects the wave never touched, not just the directories the wave changed.

### Step 3 — Report
Per check: `pass` / `pass_with_env_deltas` / `fail` (with the failing step's captured output, verbatim) / `not_locally_verified`.

A bare `pass` asserts CI-faithful replication: the check ran in a clean environment with the extracted variables, the repo's own toolchain, and the config's declared working directory and iteration scope. When the check passes but the local run deviated from the CI definition in any of those dimensions (the environment could not be fully extracted, a tool version could not be pinned), the result is `pass_with_env_deltas` with each delta named, never a bare `pass`.

Exit summary: green only when every locally-runnable check is `pass` or `pass_with_env_deltas`; any `fail` is red. This is the final pre-raise gate — `dbt-migration-batch-raise` Step 5 consumes it and does not raise over a red result; a `pass_with_env_deltas` passes the gate with its deltas carried into the PR body's stage table.

### Step 4 — Update status

```yaml
artifacts:
  utils_ci_parity:
    last_run_date: "{{TODAY}}"
    repo: "<url-or-path>"
    systems_detected: [circleci]
    checks_pass: <n>
    checks_pass_with_env_deltas: <n>
    checks_fail: <n>
    checks_not_locally_verified: <n>
```

## Notes for the implementer

- Parity means the client's checks with the client's config. Do not substitute Wire's lint config, and do not "fix" the client's config to make a check pass; a disagreement between our output and their config is a finding to resolve in the models, or a question for the client.
- New failure classes caught here feed the defect-class flywheel (`dbt-migration-lint`): a client CI rejection that was not locally replicated means this command's step extraction missed a step — extend it before the next raise.
- Engagement-agnostic by design: nothing here reads migration-specific inputs beyond the optional `client_repos` role lookup, so any release type raising PRs into a client repo can use it.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `utils_ci_parity` as artifact, `run` as action.
