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
  optional:
    - name: target
      description: "Environment to deploy to (default: the only environment in deploy.allowed)"
    - name: files
      description: "Repo-relative files to deploy (default: the files this branch changed under the environment's repo_root)"
description: Deploy a branch's changed Airflow files to the dev environment, one file at a time, after the deploy target check allows every file and the user confirms
argument-hint: <release-folder> [--target <env>] [--files <path>...] [--dry-run]

---

# Utils: Dev Deploy (Airflow)

## Purpose

Put a branch's changed DAG files into the dev Airflow environment so they can be run before a pull request is raised. The copy is safe by construction: `wire/scripts/airflow_deploy.py` checks every file against the client's environment file first, copies one file at a time, never syncs a folder and never deletes. Production and staging are refused by the environment file's `deploy.forbidden`, whatever is asked.

## Inputs

- `.wire/engagement/airflow_environments.yml` (schema in `wire/schemas/airflow-environments-schema.md`). If it is missing, stop: "No Airflow environment file. Run `/wire:adopt` to propose one, or write it from the schema, then re-run." Never guess a bucket.
- The current branch and its base: the release branch, or the branch named in the iteration file under `/wire:work`.

## Workflow

### Step 1: Resolve the target

`--target` if given. Otherwise the only name in `deploy.allowed`; if there are several, ask which. Never default to a name in `deploy.forbidden`.

### Step 2: Resolve the files

`--files` if given. Otherwise the files this branch changed against its base, under the target's `repo_root`:

```bash
git diff --name-only --diff-filter=ACMR <base>...HEAD -- <repo_root>
```

Deleted files are listed and never deployed: a deploy never deletes. Uncommitted changes are listed and left out; the user commits them first, so the deployed copy is the PR-head copy that `/wire:utils-dev-test-evidence` will compare.

### Step 3: Check

```bash
python3 <wire>/scripts/airflow_deploy.py check \
  .wire/engagement/airflow_environments.yml <target> <files...>
```

Show the result as it is: one ALLOW or REFUSE line per file, with the reason. If any file is refused, stop. Say what would make it allowed (commit it, move it under `repo_root`, or drop it from the list), and that a protected path or DAG is the client team's call, not Wire's.

### Step 4: Plan and confirm

```bash
python3 <wire>/scripts/airflow_deploy.py plan \
  .wire/engagement/airflow_environments.yml <target> <files...>
```

Show the copy commands and ask: **Deploy / Cancel**. With `--dry-run`, stop here.

### Step 5: Run

On Deploy:

```bash
python3 <wire>/scripts/airflow_deploy.py run \
  .wire/engagement/airflow_environments.yml <target> <files...>
```

The run stops on the first failed copy and says which files were not copied. Record the upload time of each copied file (the time the command reports it copied).

### Step 6: Confirm sync and parse

Do not tell the user to trigger a run until each DAG file is synced and parsed. Follow the Airflow skill's "Confirm sync and parse" step (`skills/airflow/SKILL.md`): compare each file's upload time with the DAG's last parse time in Cloud Logging, and check for an import error after the upload. Report per file: `parsed`, `import error` (with the message), or `not parsed yet` (wait and check again; Composer syncs the bucket to the workers within a few minutes).

### Step 7: Update status

```yaml
artifacts:
  utils_dev_deploy:
    last_run_date: "{{TODAY}}"
    target: dev
    files_deployed: <n>
    files_refused: <n>
    parsed: <n>
    import_errors: <n>
```

Under `/wire:work` with ticket delivery, write the same to the ticket record's front matter, not `status.md`.

## Gemini CLI

The same steps. Step 6 runs the Cloud Logging queries from the skill file with `gcloud logging read`; Gemini reads `skills/airflow/SKILL.md` as a file.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `utils_dev_deploy` as artifact, `run` as action.
