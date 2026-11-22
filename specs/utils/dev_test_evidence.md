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
      description: "Environment the change was tested in (default: the only environment in deploy.allowed)"
description: Check that each file a branch changed was tested in dev. The deployed dev copy is the PR head, it parsed, and it ran successfully after the upload, every mapped task included; verdict yes, partially or no. Read only
argument-hint: <release-folder> [--target <env>]

---

# Utils: Tested-in-dev Evidence

## Purpose

Answer "was this change tested in dev?" with evidence, before a pull request is raised and when a reviewer asks. For each file the branch changed:

1. The copy deployed to dev is the PR-head copy (line endings normalised).
2. It parsed, with no import error, after the upload.
3. It ran successfully after the upload, every mapped task instance included.

The verdict per file and overall is `yes`, `partially` or `no`, with the reasons. The command is read only: it fetches copies and reads logs, and changes nothing in dev or in the repo. Run it next to `/wire:utils-ci-parity` before a PR is raised; `/wire:work` Step 6 and the review specs read its result.

Airflow is the first tool. The verdict shape (per file: yes, partially or no, with evidence) is the same one dbt and LookML will use later.

## Inputs

- `.wire/engagement/airflow_environments.yml` (schema in `wire/schemas/airflow-environments-schema.md`): the target's project, bucket, `dags_prefix` and `repo_root`. Stop if it is missing.
- `.wire/engagement/review_profile.yml` (schema in `wire/schemas/review-profile-schema.md`): `tested_in_dev` (`off` means do not run; say so and stop).

## Workflow

### Step 1: Changed files

The files the branch changed against its base, under the target's `repo_root`:

```bash
git diff --name-only --diff-filter=ACMR <base>...HEAD -- <repo_root>
```

Classify each: `dag` when it defines a DAG (read with `ast`, as `airflow_deploy.py` does), else `support` (helpers, SQL, config). For a support file, name the DAGs that read it (`used_by`) from the imports and file references in the changed DAGs; if none can be named, leave it empty and the verdict says so.

### Step 2: Copies

Into a scratch folder under `.wire/local/` (git-ignored):

- `head/<path>`: `git show HEAD:<path>`.
- `dev/<path>`: `gcloud storage cp gs://<bucket>/<dags_prefix><path relative to repo_root> dev/<path>`. A missing object is recorded as `dev_path: null`.
- `uploaded_at`: the object's update time, from `gcloud storage objects describe gs://<bucket>/<object> --format="value(update_time)"`.

### Step 3: Parse and run records

From Cloud Logging, with the queries in the Airflow skill's "Run and task checks" section (`skills/airflow/SKILL.md`), for the target's project and environment:

- per DAG file: the last parse time after the upload, and any import error logged for the file after the upload;
- per DAG id: the runs that started after the earliest upload, with run id, state, start time, and each task instance's task id, map index and state.

Teams that can run the Airflow command line or call the Airflow REST API may read the same facts there. Whichever source is used is named in the report.

### Step 4: Verdict

Write the inputs to `.wire/local/dev_test_evidence/<branch>/input.json` in the shape `wire/scripts/dev_test_evidence.py` documents and run:

```bash
python3 <wire>/scripts/dev_test_evidence.py .wire/local/dev_test_evidence/<branch>/input.json --format markdown
```

The script decides; this spec does not re-judge its verdict. Rules, in short:

| Verdict | When |
|---|---|
| `no` | dev copy missing or not the PR head; import error; latest run after the upload failed, or a task in it failed |
| `partially` | no parse or no run after the upload; a run still going; a task instance skipped or not run; a support file with no DAG that uses it |
| `yes` | the dev copy is the PR head, it parsed after the upload, and the latest run after the upload succeeded with every task instance in success |

Overall: `no` if any file is `no`, `partially` if any file is `partially`, else `yes`.

### Step 5: Report

Show the markdown table. Under `/wire:work`, add it to the PR body (Step 6) at the top when the verdict is not `yes`. The verdict never blocks a PR; it tells the reviewer what was and was not shown.

### Step 6: Update status

```yaml
artifacts:
  utils_dev_test_evidence:
    last_run_date: "{{TODAY}}"
    target: dev
    verdict: yes | partially | no
    files_yes: <n>
    files_partially: <n>
    files_no: <n>
```

Under `/wire:work` with ticket delivery, write it to the ticket record's front matter, not `status.md`.

## Gemini CLI

The same steps, with `gcloud logging read` for Step 3. Gemini reads `skills/airflow/SKILL.md` as a file.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `utils_dev_test_evidence` as artifact, `run` as action.
