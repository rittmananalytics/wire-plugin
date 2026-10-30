# General Airflow practice

Guidance for Airflow 2.x (2.4 and later) and Cloud Composer 2 and 3 that
needs judgement, so no script checks it. The rules a script can check are in
`conventions/airflow.yml` (AF-101 to AF-106) and are listed at the end with
their false-positive notes. Sources: the Apache Airflow "Best Practices",
"Dynamic Task Mapping", "Tasks" and "Deferrable Operators" pages, and the
Cloud Composer guides on DAG authoring, troubleshooting DAGs and scaling.

## Tasks

1. **Idempotent tasks.** Running a task twice for the same logical date gives
   the same result. Write with partition overwrite, `MERGE` on a key, or
   delete-then-insert for the interval. Never a bare `INSERT` or append.
2. **Use the logical date, not the clock.** Read `{{ ds }}`,
   `{{ data_interval_start }}` and `{{ data_interval_end }}`, never
   `datetime.now()`, inside tasks. A re-run or backfill then processes the
   interval it is for.
3. **Safe re-runs and backfills.** Check that clearing a task, or running
   `catchup` or a backfill over a past range, does not double-load. If a task
   cannot be re-run safely, say so in its `doc_md`.
4. **Retries.** Set `retries` and `retry_delay` for tasks that call external
   systems. Composer may set `core.default_task_retries` for the environment;
   read it before adding retries to every task. Not script-checked: a missing
   `retries` is often deliberate or set environment-wide.
5. **Timeouts.** Set `execution_timeout` on tasks that can hang (API calls,
   long queries), so a stuck task fails and alerts instead of holding a slot.
6. **Owner.** Set `owner` to the team, so the UI shows who to ask. Not
   script-checked: many estates leave the default and track owners elsewhere.

## Data between tasks

7. **XCom is for small values.** Pass a path, a table name or a row count,
   not data. XCom lives in the metadata database (or a custom backend); large
   values slow the database and can fail. Composer's database is shared by
   the scheduler and the web server.
8. **No shared mutable state.** Do not change a module-level object (a
   shared `default_args` dict imported from a helper, a list) inside a DAG
   file; every DAG that imports it sees the change, in parse order. Copy it
   first (`{**SHARED_ARGS, "retries": 3}`). Not script-checked: telling a
   mutation from a read across modules needs more than one file.

## Concurrency and resources

9. **Pools for shared limits.** Use a pool when several DAGs call the same
   system (one warehouse, one API with a rate limit). Size it from the
   system's limit, not from the worker count.
10. **Caps per environment.** Fan-out caps, pool sizes and `max_active_runs`
    differ between dev and production. Read them from the environment's
    config so dev does not need production-sized workers.
11. **Deferrable operators.** For long waits (a job in another system, a
    file that arrives late), use the deferrable version of the operator or
    sensor (`deferrable=True`) so the wait runs in the triggerer, not in a
    worker slot. Composer needs a triggerer configured; check the
    environment before relying on it.
12. **Sensors or schedules.** A sensor that waits for an upstream DAG every
    day may be better as a dataset-triggered schedule (`schedule=[Dataset(...)]`,
    Airflow 2.4 and later), or as a fixed schedule after the upstream's
    known finish time. Use a sensor when the upstream time varies and the
    wait has a clear timeout.
13. **Map length.** A mapped task over a list longer than
    `core.max_map_length` (1024 by default) fails. Batch the inputs.

## Parsing

14. **Keep parse time short.** The DAG processor parses every file every
    `min_file_process_interval` (30 seconds by default) and times out a file
    after `dag_file_processor_timeout`. Heavy imports (pandas, cloud client
    libraries) belong inside tasks.
15. **Dynamic DAGs from config.** Generate several DAGs from a local YAML
    file at parse time if needed, but never from a network call or a
    database query.

## Composer specifics

16. **Bucket layout.** `dags/` is parsed; `plugins/` is loaded on the
    workers and scheduler; `data/` is synced to workers only. A file in the
    wrong folder is silently not seen.
17. **Sync delay.** Files in the bucket reach the scheduler and workers
    through a sync that can take a few minutes. Check the parse after upload
    before triggering a run.
18. **Environment upgrades.** Pin provider versions in the environment's
    PyPI packages and test an Airflow or Composer version upgrade in dev
    first.

## Airflow 3 changes to plan for

19. `schedule_interval` and `timetable` arguments are removed: use
    `schedule` (AF-105).
20. `airflow.contrib`, the `*_operator` modules, `DummyOperator` and
    `days_ago` are removed (AF-106). Standard operators move to the
    `apache-airflow-providers-standard` package.
21. `catchup` defaults to `False`. Set it on every DAG so behaviour does not
    change on upgrade.
22. Tasks no longer reach the metadata database directly; code that opens a
    database session in a task must move to the Task SDK or the REST API.
23. `execution_date` is replaced by `logical_date` in context and templates.

## Script-checked rules and their false-positive risk

| Rule | Detected with `ast` | False-positive risk |
|---|---|---|
| AF-101 `Variable.get` at module level | A call named `*.Variable.get` outside any function body | Low. A file that sets up a secrets backend cache may accept it; justify in the PR. |
| AF-102 moving `start_date` | A `start_date` keyword or dict key whose value calls `now`, `utcnow`, `today` or `days_ago` | Low. |
| AF-103 long poke sensor | A call named `*Sensor` with no `mode="reschedule"` and no `deferrable`, whose timeout is absent (7 days) or a literal over the limit | Medium. A sensor on a dedicated pool sized for waits is a choice; a client can disable the rule with a reason. Timeouts read from config are not judged. |
| AF-104 module-level I/O | A call starting `requests.`, `httpx.`, `urllib.request.`, `subprocess.`, or `bigquery.Client`/`storage.Client` outside a function | Low. Opening local config files is allowed. |
| AF-105 `schedule_interval` | The keyword on a `DAG(...)` or `@dag(...)` call | Low. |
| AF-106 deprecated imports | `import` and `from ... import` of the listed modules and names | Low. |

Considered and left to judgement (too many false positives for a script):
missing `retries` (often set environment-wide), tasks with no `owner`,
`catchup` not set explicitly (Composer can set the default), shared mutable
`default_args` (needs more than one file), and literal cron schedules (fine
in a single-environment estate; AF-003 covers estates that keep schedules in
config).
