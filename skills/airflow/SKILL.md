---
name: airflow
description: Proactive skill for Apache Airflow 2.x and Cloud Composer work in a client's existing Airflow repo. Auto-activates when writing or changing a DAG file, a DAG helper, or the config a DAG reads; when deploying DAG files to a dev environment; when checking whether a DAG parsed or a run succeeded; when tasks are stuck in queued; and when the pipeline or orchestration artifact uses Airflow. Covers the Airflow rule set (lint_conventions.py --domain airflow), safe dev deploy through airflow_deploy.py, sync and parse checks, run and task checks through Cloud Logging, causes of queued tasks and a list of known faults. Every environment value comes from .wire/engagement/airflow_environments.yml.
---

# Airflow Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | airflow | activated | Airflow DAG work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

## Purpose

Write, deploy and check Airflow code in an estate a client already runs: Cloud Composer 2 or 3, or a self-managed Airflow 2.x. The skill carries Wire's general Airflow practice. The client's own rules, helper names and environment values live in the client's repo, in files this skill reads:

| File | Holds | Schema |
|---|---|---|
| `.wire/conventions/airflow.yml` | The client's extra rules and helper names, with `extends: wire` | `wire/schemas/convention-schema.md` |
| `.wire/engagement/airflow_environments.yml` | Environments, buckets, branches, deploy allow and forbid lists, protected paths and DAGs | `wire/schemas/airflow-environments-schema.md` |
| `.wire/engagement/review_profile.yml` | PR template, tracker, review mode | `wire/schemas/review-profile-schema.md` |

**Stop if `.wire/engagement/airflow_environments.yml` is missing** whenever a step needs an environment value (deploy, logs, caps). Say: "No Airflow environment file. Run `/wire:adopt` to propose one, or write it from `wire/schemas/airflow-environments-schema.md`." Never write a project, bucket, environment name or region from memory or from an example.

## When This Skill Activates

- A Python file imports `airflow`, or sits in the repo's DAG folder.
- The user asks to write, change, deploy, run or debug a DAG, or asks why a task is queued.
- `status.md` shows `pipeline_tool: airflow` or `orchestration_tool: airflow`.
- `/wire:pipeline-generate`, `/wire:orchestration-generate` (existing Airflow estate mode), `/wire:utils-dev-deploy` or `/wire:utils-dev-test-evidence` runs.

**Keywords**: "airflow", "composer", "DAG", "dag_id", "operator", "sensor", ".expand", "mapped task", "default_args", "queued", "gcs-syncd", "dag processor", "Broken DAG".

---

## Step 0: Resolve the rules and lint before trusting your own read

1. Rule file: `.wire/conventions/airflow.yml` if present, else Wire's `conventions/airflow.yml`. A client file with `extends: wire` keeps Wire's rules and adds its own; one without `extends` replaces Wire's.
2. Run the lint on the files you are about to change, and again after:

```bash
python3 <wire>/scripts/lint_conventions.py --domain airflow \
  --convention <resolved airflow.yml> --path <dag folder> --changed-from <base branch>
```

Without `--changed-from`, every finding in the folder is listed as a warning: that is the list of what to fix in an existing estate, not a reason to change files the task does not touch.

3. Report the rules the client disabled (the lint prints them with their reasons). Do not apply a disabled rule.

| Id | Rule | Checked by script |
|---|---|---|
| AF-001 | Use the repo's shared helpers before writing new ones | no |
| AF-002 | No project id or bucket written into Python | yes |
| AF-003 | Schedules and targets from per-environment config | no |
| AF-004 | One DAG per job, mapped tasks over the varying inputs, not copied DAGs | no |
| AF-005 | Every `.expand()` capped (`max_active_tis_per_dag`, a pool, or `max_active_tasks` on the DAG), cap from config | yes |
| AF-006 | A DAG file contains the words `airflow` and `dag` (safe mode skips it otherwise, with no error) | yes |
| AF-007 | DAG arguments (`catchup`, `schedule`, `max_active_runs`, `tags`, ...) on the DAG, never in `default_args` | yes |
| AF-101 | No `Variable.get()` at module level | yes |
| AF-102 | Fixed `start_date`, never `now()` or `days_ago()` | yes |
| AF-103 | Sensors reschedule or defer, or time out within the limit | yes |
| AF-104 | No network, process or warehouse calls at module level | yes |
| AF-105 | `schedule=`, not `schedule_interval=` | yes |
| AF-106 | No imports removed in Airflow 3 (`airflow.contrib`, `*_operator` modules, `DummyOperator`, `days_ago`) | yes |

Judgement calls that no script checks are in `references/general_practice.md`. Read it before writing a new DAG.

## Writing DAGs

1. **Search first.** Find the DAG that already does this job, and the helpers it uses. Change or extend it; add a mapped input before adding a file (AF-001, AF-004). List the client's `helpers:` from its rule file if it has one.
2. **Config, not literals.** Projects, buckets, datasets, schedules and caps come from the repo's per-environment config, keyed by the environment the code runs in. Jinja (`{{ var.value.x }}`, `{{ ds }}`) is fine.
3. **DAG arguments on the DAG.** `default_args` holds task arguments only: `owner`, `retries`, `retry_delay`, callbacks, `start_date` if the repo does it that way.
4. **Nothing at module level** but imports, config reads from local files, and DAG and task definitions.
5. **Mapped tasks.** Cap every `.expand()` from the environment's `max_mapped_tasks` or a pool. Remember the scheduler's own limit on map length (`max_map_length`, 1024 by default).
6. **Idempotent tasks.** A re-run of the same logical date writes the same result: partition overwrite or merge on a key, never a bare append.
7. Lint again (Step 0) and fix every error on the changed files. Give each remaining finding a disposition for the PR: `fixed`, `justified` with a reason, or `acknowledged`. Findings never block.

## Safe dev deploy

Deploy only through `/wire:utils-dev-deploy`, which runs `wire/scripts/airflow_deploy.py`. Never copy with your own `gcloud storage`, `gsutil` or `rsync` command.

- One file at a time, repo-relative paths only.
- Never sync a folder, never delete, never overwrite another person's file: the script refuses protected paths and DAGs from the environment file.
- Only environments in `deploy.allowed` and not in `deploy.forbidden`. Refuse staging and production even if the user asks; say that the client's CI deploys there.
- Only files git tracks. Commit first, so the deployed copy is the PR-head copy.

## Confirm sync and parse before a run

Do not tell the user to trigger a run until both hold for each deployed DAG file:

1. **Synced.** Composer copies the bucket to the scheduler and workers (the `gcs-syncd` container); this takes up to a few minutes. Self-managed Airflow uses its own sync (git-sync, a volume); ask how it works if the environment file does not say.
2. **Parsed after the upload, with no import error.** Compare the upload time (from the deploy output, or `gcloud storage objects describe gs://<bucket>/<object> --format="value(update_time)"`) with the DAG processor's last parse of the file.

Cloud Logging queries (`gcloud logging read '<filter>' --project <project> --freshness 1h --format json`). The environment's `project` and `composer_environment` come from the environment file. Composer's log names and label keys have changed between versions: read one entry with `--limit 1` first and adjust the filter to what is there.

```text
# Sync of one file to the environment
resource.type="cloud_composer_environment"
resource.labels.environment_name="<composer_environment>"
log_id("gcs-syncd")
textPayload:"<file name>"

# Parse of one file (DAG processor)
resource.type="cloud_composer_environment"
resource.labels.environment_name="<composer_environment>"
(log_id("dag-processor-manager") OR log_id("airflow-dag-processor-manager") OR log_id("airflow-scheduler"))
textPayload:"<file name>"

# Import errors for one file
resource.type="cloud_composer_environment"
resource.labels.environment_name="<composer_environment>"
(textPayload:"Broken DAG" OR textPayload:"ImportError" OR textPayload:"Traceback")
textPayload:"<file name>"
```

Report per file: `parsed` (with the time), `import error` (with the message), or `not parsed yet`.

## Run and task checks through Cloud Logging

For teams that cannot run the Airflow command line or reach the REST API. Airflow 2 workers log one line per finished task instance, `Marking task as SUCCESS.` or `Marking task as FAILED.`, with `dag_id`, `task_id`, `run_id` and `map_index`:

```text
# Task outcomes for one DAG since the upload
resource.type="cloud_composer_environment"
resource.labels.environment_name="<composer_environment>"
log_id("airflow-worker")
textPayload:"Marking task as"
textPayload:"dag_id=<dag_id>"
timestamp>="<upload time, RFC 3339>"

# Everything one task instance logged
resource.type="cloud_composer_environment"
resource.labels.environment_name="<composer_environment>"
log_id("airflow-worker")
labels.workflow="<dag_id>"
labels."task-id"="<task_id>"
```

A run succeeded only when every task instance in it, each mapped index included, reached success. Count the mapped indexes you expected (the length of the mapped input) against the indexes logged. For the tested-in-dev verdict, give these records to `/wire:utils-dev-test-evidence`; do not judge it by hand.

## Tasks stuck in queued

Check in this order. Each cause names what to read:

| Cause | How to tell |
|---|---|
| Workers at capacity | Running tasks equal workers times `celery.worker_concurrency`. Composer autoscaling adds workers after a delay; check the worker count in the environment's monitoring. |
| Pool full | The task's pool has no open slots (`default_pool` is 128 slots by default). Other DAGs' tasks may hold them. |
| DAG or task limits | `max_active_tasks` on the DAG, `max_active_tis_per_dag` on the task, `max_active_runs`, or `core.parallelism` for the whole environment, reached. |
| Long sensors in poke mode | Sensors hold worker slots while they wait (rule AF-103). Count running sensors. |
| Workers restarting | Worker pods evicted or out of memory: look for `OOMKilled`, eviction or restarts in the worker logs; queued tasks wait for a new worker. |
| Scheduler unhealthy | No scheduler heartbeat in the scheduler logs, or the DAG processor timing out on slow files (rule AF-104). |
| Queue name mismatch | The task sets a `queue` no worker listens on. |
| Task stuck after a worker died | A task queued in Celery whose worker has gone. Airflow re-queues it after `scheduler.task_queued_timeout` (10 minutes by default in 2.6 and later). |

## Known faults

| Symptom | Usual cause | Fix |
|---|---|---|
| DAG never appears, no error | File lacks the words `airflow` and `dag` (AF-006), or is in `.airflowignore` | Add the words; check `.airflowignore` |
| DAG appears, never runs | `start_date` moves (AF-102), DAG paused, or `catchup=False` with a start date after the only interval | Fixed start date; unpause |
| `catchup` set but ignored | Put in `default_args` (AF-007) | Move to the DAG |
| Parse slow, scheduler lags | Module-level work: `Variable.get`, network or warehouse calls (AF-101, AF-104) | Move into tasks or Jinja |
| Mapped task floods workers | `.expand()` with no cap (AF-005) | `max_active_tis_per_dag` or a pool from config |
| Works in dev, fails in prod | A literal project or bucket (AF-002) | Read from per-environment config |
| Different results on re-run | Task uses the wall clock (`datetime.now()`) instead of the logical date | Use `{{ ds }}`, `data_interval_start` |
| Large XCom fails or slows the database | Data passed through XCom | Pass a path or table name, not the data |
| Task killed with no error | Worker out of memory | Smaller batches, more memory, or a pod per task |
| Imports fail after an upgrade | Imports removed in Airflow 3 (AF-106) | Use the providers' current paths |

## Gemini CLI

Gemini CLI has no skills. The Airflow specs tell it to read this file and follow it. Every step here runs the same there: the scripts are plain Python and the queries run with `gcloud logging read`.
