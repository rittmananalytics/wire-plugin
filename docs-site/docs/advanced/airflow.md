---
sidebar_position: 14
title: Airflow
---

# Airflow

Wire works in Airflow estates a client already runs: Apache Airflow 2.x, on Cloud Composer 2 or 3 or self-managed. It writes and changes DAGs to a set of rules a script checks, deploys changed files to a dev environment one at a time, and shows whether a change was tested in dev before a pull request is raised. Every environment value (projects, buckets, environment names) comes from a file in the client's repo. Wire ships none.

## What is included

| Part | What it does |
|---|---|
| Airflow skill | Writes DAGs to the rules, deploys to dev through the deploy check, checks sync, parse and runs through Cloud Logging, explains tasks stuck in queued, lists known faults |
| Airflow rules | `conventions/airflow.yml`, checked by `lint_conventions.py --domain airflow` |
| `/wire:utils-dev-deploy` | Copies a branch's changed files to dev after the deploy check allows each one |
| `/wire:utils-dev-test-evidence` | Per changed file: is the dev copy the PR head, did it parse, did it run after the upload. Verdict `yes`, `partially` or `no` |
| Pipeline and orchestration | `pipeline_tool: airflow` for ingestion DAGs; an existing Airflow estate mode for schedule changes |
| Tickets | A build ticket for an `ingestion` slice maps to `/wire:pipeline-generate`, plus `/wire:orchestration-generate` when it changes a schedule |

## Setting it up

You need the Wire plugin installed and Claude Code open in the Airflow repository.

1. Run `/wire:adopt` in the repository. It creates `.wire/`, and from the repo's Cloud Build or CI files, branch rules and pull request template it proposes two files: the environment file and the review profile. Check both with the people who run the environments, then commit them.
2. If your team has its own rules, add them to `.wire/conventions/airflow.yml` with `extends: wire`, so Wire's rules still apply. See [Convention rules](./convention-rules.md).
3. Run the lint on the whole repository once to see where the existing code stands (below). Findings on existing code are warnings; nothing fails.
4. If the team already has its own Claude Code skills for the repository, cut them down to what is specific to you. Keep that in a short project skill in `.claude/skills/`; Claude Code loads it next to Wire's.

From then on you work by ticket with `/wire:work`, or just say what you want; the release director picks the commands.

## The rules

The lint parses Python with the standard library `ast` module, so a comment that mentions a call does not count as the call.

| Id | Rule | Checked |
|---|---|---|
| AF-001 | Use the repo's shared helpers before writing new ones | advice |
| AF-002 | No project id or bucket written into Python | script |
| AF-003 | Schedules and targets from per-environment config | advice |
| AF-004 | One DAG per job, with mapped tasks, not copied DAGs | advice |
| AF-005 | Every `.expand()` capped by `max_active_tis_per_dag`, a pool, or `max_active_tasks` on the DAG | script |
| AF-006 | A DAG file contains the words `airflow` and `dag`; in safe mode Airflow skips a file without both, with no error | script |
| AF-007 | DAG arguments (`catchup`, `schedule`, `max_active_runs`, `tags`) on the DAG, never in `default_args` | script |
| AF-101 | No `Variable.get()` at module level | script |
| AF-102 | A fixed `start_date`, never `now()` or `days_ago()` | script |
| AF-103 | Sensors reschedule or defer, or time out within an hour | script |
| AF-104 | No network, process or warehouse calls at module level | script |
| AF-105 | `schedule=`, not `schedule_interval=` | script |
| AF-106 | No imports removed in Airflow 3 | script |

Run it on a whole folder to list what to fix in an existing estate. Every finding then shows as a warning:

```bash
python3 wire/scripts/lint_conventions.py --domain airflow \
  --convention .wire/conventions/airflow.yml --path dags/
```

Run it with `--changed-from <base branch>` on a pull request. The files the branch changed are then held to each rule's severity, and other files are left alone. A client adds its own rules, and switches Wire's off with a reason, in `.wire/conventions/airflow.yml`; see [Convention rules](./convention-rules.md).

## The environment file

`.wire/engagement/airflow_environments.yml` lists the client's environments and says where Wire may deploy. `/wire:adopt` proposes it from the repo's Cloud Build or CI files; the client's team checks and commits it. The full schema is in `wire/schemas/airflow-environments-schema.md`.

```yaml
schema_version: 1
environments:
  - name: dev
    composer_environment: example-composer-dev
    project: example-data-dev
    region: europe-west1
    bucket: example-composer-dev-bucket
    dags_prefix: dags/
    repo_root: dags/
    branch: develop
    max_mapped_tasks: 8
  - name: prod
    project: example-data-prod
    bucket: example-composer-prod-bucket
    branch: main
deploy:
  allowed: [dev]
  forbidden: [prod]
protected:
  paths:
    - path: dags/live_only/
      reason: "Runs live in dev only; changed by the platform team."
  dag_ids:
    - dag_id: finance_month_end
      reason: "Owned by finance; deployed by their own pipeline."
```

If the file is missing, the skill and both commands stop and say so. They never guess an environment.

## Deploying to dev

`/wire:utils-dev-deploy <release>` finds the files the branch changed, runs the deploy check, shows the copy commands and asks before copying. The check refuses a file when:

- its path is absolute or contains `..`;
- the target is not in `deploy.allowed`, or is in `deploy.forbidden` (forbidden wins);
- it is outside the environment's `repo_root`;
- it matches a protected path, or defines a protected DAG;
- git does not track it, or it does not exist.

If any file is refused, nothing is copied. Each allowed file is copied on its own with `gcloud storage cp`. A deploy never syncs a folder and never deletes. After the copy, the skill checks each file synced and parsed before it suggests a run.

## Tested in dev

`/wire:utils-dev-test-evidence <release>` answers "was this tested in dev?" for each file the branch changed:

| Verdict | When |
|---|---|
| `yes` | The dev copy is the PR head (line endings ignored), it parsed after the upload, and the latest run after the upload succeeded with every task instance, mapped ones included |
| `partially` | No parse or run after the upload, a run still going, a task skipped, or a helper no DAG is named as using |
| `no` | The dev copy is missing or different, an import error, or a failed run or task |

The overall verdict is `no` if any file is `no`, `partially` if any is `partially`, else `yes`. The command is read only. It reads run records from Cloud Logging, for teams that cannot run the Airflow command line. The verdict goes in the pull request body and never blocks it.

## Review

Pull requests from `/wire:work` follow the client's review profile; see [Review profile](./review-profile.md). Rule findings are listed as `fixed`, `justified` or `acknowledged` and never block. Each ticket gets a requirements table, and a requirement that is not met is raised as a question to the ticket owner.

## An Airflow ticket, step by step

A ticket asks for one more file type in an existing CSV ingestion DAG. The repository has been adopted, and the release `01-airflow-dags` is built from tickets.

| You say | Wire does |
|---|---|
| "Pick up OPS-101." | Reads the ticket and the release. Finds the DAG that ingests this source, that it uses mapped tasks with one task per file type, and that the file list lives in per-environment YAML config. Proposes a plan in which every step names its command: `/wire:pipeline-generate`, `/wire:pipeline-validate`, `/wire:utils-dev-deploy`, a run you trigger, `/wire:utils-dev-test-evidence`, `/wire:utils-ci-parity`, `/wire:utils-pr-create` |
| "Approve." | Adds the file type to the config for each environment and one load SQL file. Runs the lint: compiles, parse check, no hardcoded project or bucket, fan-out capped per environment, no DAG arguments in `default_args` |
| (continues) | Runs the deploy check, shows the two files it will copy to dev, copies them one at a time, and waits until Airflow has parsed the new version. Then asks you to trigger the DAG in the dev Airflow UI |
| "Triggered." | Watches the run through Cloud Logging until every mapped task finishes. Records the tested-in-dev verdict, runs your CI checks, and raises the pull request on your template with the verdict, the requirements table and the rule findings |

If you ask for something the environment file forbids, such as "deploy it to staging as well", Wire refuses and says why: staging is deployed by merging through your CI, so the pull request is the way there.

A ticket that adds a new source is larger than a ticket. Wire says so and offers to add it to the release as a new slice, with a design step that stops for your approval before any DAG is written.

