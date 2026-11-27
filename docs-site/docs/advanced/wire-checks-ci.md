---
sidebar_position: 17
title: Wire checks in CI
---

# Wire checks in CI

Wire checks a pull request in the client repository's CI, for every author: a person, an RA-hosted agent or a client's own agent. The checks are plain scripts with no AI call.

| Check | What it reads | Fails on |
|---|---|---|
| Release records | Each release `status.md` and ticket record (`.wire/releases/<release>/iterations/<ticket>.md`) the pull request changes | A key written twice, or YAML that does not parse (`status_file.py`) |
| Conventions | Each changed file in a convention domain, with the client's `.wire/conventions/<domain>.yml` as it is on the base branch when there is one, else Wire's | An `error` finding of `lint_conventions.py`. Warnings are listed for the reviewer |

Only files the pull request adds or changes are checked. A problem already on the base branch does not fail a pull request:

| File | A finding fails the check when |
|---|---|
| Added | Always |
| Changed | It is on a line the pull request added or changed. A finding with no line (a file name, a missing `final` CTE) is already on the base branch |
| Renamed | It is on a changed line, or it has no line (the new name is the pull request's) |

A key written twice in a release record fails when the pull request wrote either copy. Other findings are listed as warnings marked "already on the base branch".

A pull request that changes `.wire/conventions/` is checked against the base branch's rules, so it cannot loosen the rules it is checked against. The summary names the change for the reviewer.

A client whose models follow its own naming adds `.wire/conventions/dbt.yml` (with `extends: wire` and `disable:` for the rules it does not follow) in its own pull request first.

## Which files are in a domain

| Domain | Files |
|---|---|
| `dbt` | `.sql`, `.yml`, `.yaml`, `.csv` under `models/`, `snapshots/`, `seeds/` or `macros/` of a folder holding `dbt_project.yml` |
| `dbtcharts` | `.yml` under `charts/` of a dbt project, and `dbt_charts.yml` |
| `lookml` | Any `.lkml` file |
| `cube` | `.yml` under a `model/` or `schema/` folder whose text has `cubes:` or `cube(` |
| `airflow` | `.py`, `.sql`, `.yml` under a `dags/` folder |
| `data_apps` | `.js` under `<data_apps_path>/<slug>/`: a folder named `data_apps`, or the path a release `status.md` (`data_apps_path`) or `.wire/engagement/context.md` (`data_apps: path:`) names |

Files under `target/`, `dbt_packages/`, `dbt_modules/`, `node_modules/`, `logs/`, `__pycache__/` or a folder starting with `.` are in no domain, as in `lint_conventions.py`'s own folder walk.

## Set it up

Copy `ci/wire-checks.yml` from the plugin to `.github/workflows/wire-checks.yml` in the client repository. Replace `WIRE_PLUGIN_COMMIT` with the `wire-plugin` commit the engagement runs:

```yaml
name: Wire checks
on:
  pull_request:
permissions:
  contents: read
jobs:
  wire-checks:
    name: Wire checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: rittmananalytics/wire-plugin/ci@<commit>
        with:
          base: ${{ github.event.pull_request.base.sha }}
```

Keep the job name `Wire checks`. The hosted Wire agents look for a check with that name on a pull request and wait for it before review and QA. A failed check sends the ticket back to its worker.

The check writes its findings to the run's summary and as annotations on the changed lines.

## Run it locally

```bash
python3 <plugin>/scripts/wire_checks.py --repo . --base origin/main
```

Exit 0 when it passes, 1 when it fails, 2 when git cannot give the changed files.

A GitLab CI template is not available yet.
