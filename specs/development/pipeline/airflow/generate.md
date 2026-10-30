---
description: Build or change ingestion DAGs in a client's existing Airflow estate, to the resolved Airflow rules
argument-hint: <project-folder>
---

# Airflow Pipeline Generate

Follow `specs/utils/pipeline_engineer_delegate.md` before executing the workflow below.

## Purpose

Build a new ingestion DAG, or change an existing one, in a client's own Airflow repo (Cloud Composer or self-managed). Airflow is the pipeline tool here: the DAG loads source data into the warehouse. Wire works inside the estate the client already has. It does not create an Airflow environment, and it makes no live Fivetran or Airbyte call.

## Called by

`wire/specs/development/pipeline/generate.md` when `pipeline_tool == airflow`

## Inputs

- `.wire/<project_id>/design/pipeline_architecture.md`: the sources and loads in scope.
- The ticket or iteration file when run from `/wire:work`: the slice (one ingestion load) and whether the schedule changes.
- `.wire/engagement/airflow_environments.yml` (schema in `wire/schemas/airflow-environments-schema.md`). If it is missing, stop and say: "No Airflow environment file. Run `/wire:adopt` to propose one, or write it from the schema, then re-run."
- The resolved Airflow rules: `.wire/conventions/airflow.yml` if present (with `extends: wire` it adds to Wire's rules), else Wire's `conventions/airflow.yml`.

## Workflow

### Step 1: Load the skill

Activate the Airflow skill (`skills/airflow/SKILL.md`). It holds the rules, the general practice list and the environment handling. On Gemini CLI, which has no skills, read the same file and follow it.

### Step 2: Find what exists

1. Find the DAG folder (the `repo_root` of the dev environment in the environment file, default `dags/`).
2. For each load in scope, search for an existing DAG that loads the same source or table. Prefer changing it, or adding a mapped input to it, over a new file (rule AF-004, one DAG per job).
3. List the shared helpers the repo has (operator factories, config loaders, alert callbacks), and the client's `helpers:` list if its rule file has one (rule AF-001).

### Step 3: Write the change

Write or change the DAG and any config it reads:

- Environment values (projects, buckets, schedules, targets, fan-out caps) come from the repo's per-environment config, never from literals in Python (AF-002, AF-003, AF-005).
- DAG arguments on the DAG, not in `default_args` (AF-007). A fixed `start_date` (AF-102).
- No work at module level: no `Variable.get`, network or warehouse calls outside tasks (AF-101, AF-104).
- Sensors in `reschedule` mode or deferrable (AF-103).
- The file names both `airflow` and `dag` (AF-006).

### Step 4: Lint before trusting the change

```bash
python3 <wire>/scripts/lint_conventions.py --domain airflow \
  --convention <resolved airflow.yml> --path <dag folder> --changed-from <base branch>
```

Fix every error on the changed files. List each remaining warning with a disposition (`fixed`, `justified` with a reason, or `acknowledged`) for the PR. Findings on files the change did not touch are listed, not fixed.

### Step 5: Write the record

Write `.wire/<project_id>/development/pipeline/pipeline_connections.md`:

```markdown
# Pipeline: Airflow

| Load | DAG file | DAG id | New or changed | Schedule source | Helpers used |
|---|---|---|---|---|---|

## Lint
<the lint summary line, and each remaining finding with its disposition>

## Not done here
- Deploy to dev: `/wire:utils-dev-deploy <project_id>`
- Tested-in-dev evidence: `/wire:utils-dev-test-evidence <project_id>`
- Schedule changes in another DAG: `/wire:orchestration-generate <project_id>` (existing Airflow estate mode)
```

Update `status.md`: `artifacts.pipeline.generate: complete`, `pipeline_tool: airflow`, `generated_date`.

## Output

- Changed or new files under the DAG folder and its config folder.
- `.wire/<project_id>/development/pipeline/pipeline_connections.md`
