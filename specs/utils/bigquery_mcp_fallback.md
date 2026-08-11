---
description: Internal utility — falls back to the bq CLI when the BigQuery MCP server is unreachable, instead of hard-aborting or silently deferring to a manual checklist
---

# BigQuery MCP Fallback Utility

A shared utility for any command that reads or writes BigQuery via its MCP server (`mcp__claude_ai_BigQuery_MCP__*`, or an engagement-specific equivalent). `"Incompatible auth server: does not support dynamic client registration"` is a known, recoverable OAuth/dynamic-client-registration failure with a working alternative — the `bq` CLI, authenticated separately, does the same read/write job. Before this utility existed, nothing told an agent to use that alternative: some sessions improvised the CLI fallback and finished the batch, others hard-aborted or deferred to a manual checklist, and there was no record of which happened without reading every model's `.diff.md` by hand. This utility makes the fallback automatic and the choice recorded, every time.

This is not a one-time pre-flight gate like `migration_preflight.md` — it is invoked on **every** BigQuery MCP call a caller makes over the course of a batch/wave, because the connection has been observed to flap mid-run (works, breaks, works again), not fail once and stay failed.

## Inputs (provided by the calling spec)

- `release_folder` — the release folder under `.wire/releases/`
- `operation` — `compile_check` (validate only, no execution) | `read` (execute and return rows) | `write` (execute a DDL/DML statement) | `schema_lookup` (dataset/table metadata or listing)
- `sql` — the statement to run (for `compile_check`/`read`/`write`)
- `project_id`, and `dataset`/`table` where relevant (for `schema_lookup`, and to resolve `--location`)

## Procedure

### Step 1: Probe before every call, not just once per batch

Before the **first** call in a batch/wave/chunk, and before **every subsequent** call in it, run a lightweight live probe against the BigQuery MCP: `mcp__claude_ai_BigQuery_MCP__execute_sql_readonly` with `SELECT 1`, or the tool's own health-check equivalent if one exists. Treat the probe result as valid for this one call only — it does not carry forward to the next.

A probe failing once at the top of a batch is not sufficient grounds to fall back the whole batch to the CLI. Re-probe per model, per compile-check, per equivalency query — whatever granularity the caller operates at. Likewise, a fallback on one call is not grounds to assume MCP is dead for the rest of the run: re-attempt the MCP probe on the very next call regardless of how the previous one resolved, and switch back the moment it succeeds.

### Step 2: On probe failure, fall back to the `bq` CLI automatically

Do not ask the user. Do not defer to a manual checklist. Map the operation to the corresponding `bq` invocation:

| `operation` | MCP tool it replaces | `bq` CLI equivalent |
|---|---|---|
| `compile_check` | `execute_sql_readonly` (validate only) | `bq query --use_legacy_sql=false --dry_run --location=<location> --project_id=<project_id> '<sql>'` |
| `read` | `execute_sql_readonly` (fetch rows) | `bq query --use_legacy_sql=false --format=json --location=<location> --project_id=<project_id> '<sql>'` |
| `write` | `execute_sql` | `bq query --use_legacy_sql=false --location=<location> --project_id=<project_id> '<sql>'` |
| `schema_lookup` (dataset) | `get_dataset_info` / `list_dataset_ids` | `bq show --format=json --location=<location> <project_id>:<dataset>` / `bq ls --format=json --project_id=<project_id>` |
| `schema_lookup` (table) | `get_table_info` / `list_table_ids` | `bq show --format=json --location=<location> <project_id>:<dataset>.<table>` / `bq ls --format=json <project_id>:<dataset>` |

**Always pass `--location` explicitly.** Read it from `migration.target_location` in status.md (the field every `platform_migration` release already carries, default `"EU"`). Never rely on the `bq` CLI's own default location — that produced silent US/EU dataset mismatches before this utility existed, where a query against the wrong region either errored confusingly or, worse, silently resolved against an empty dataset of the same name in the CLI's default region. If `migration.target_location` is unset or null, stop and report rather than guessing:
```
[wire] migration.target_location is not set in status.md — required to pass --location explicitly to the bq CLI fallback. Set it and retry.
```

**Confirm the CLI itself is authenticated before relying on it.** On the first fallback in a run, check `bq ls --project_id=<project_id> >/dev/null 2>&1` succeeds. If it doesn't:
```
[wire] bq CLI fallback unavailable: not authenticated against <project_id>.
Run `gcloud auth application-default login` (or the engagement's documented service-account activation) and retry.
```
This is a genuine stop, not a silent skip — an unauthenticated CLI is not a usable fallback.

### Step 3: Record every fallback, without spamming the execution log

`execution_log.md` is one row per command execution, not per SQL call — a per-call entry there for a 172-model batch would drown the log. Instead:

- The calling spec accumulates a per-run counter (`mcp_fallback_count`) and a small sample of the specific reasons seen (e.g. distinct error strings, capped at 3), in memory for the duration of the run.
- When the calling spec writes its own status.md update and its own single `execution_log.md` row (per `specs/utils/execution_log.md`), it folds this summary in — e.g. `generated_date`/`validated_date` fields gain a sibling `mcp_fallback_count: N`, and the execution log `Detail` column notes it when non-zero (`"...; 12 calls used bq CLI fallback (MCP flapped mid-run)"`).
- This keeps the "which happened without reading every diff.md" problem solved at the artifact level, not buried in a per-call log nobody reads end to end.

### Step 4: When the `bq` CLI fallback also fails

Only then is this a real, hard blocker — the routine "auth server doesn't support dynamic client registration" case has a working answer, so a caller reaching this point is looking at something else. Abort with both failures shown together, so the operator doesn't waste time re-diagnosing the already-known MCP issue:
```
[wire] BigQuery unreachable via both paths for this call:
  MCP:     <the MCP error>
  bq CLI:  <the bq CLI error>
This is not the known MCP auth-registration issue (that has a working bq CLI fallback) — investigate the bq CLI failure directly.
```

## Output

Returns to the calling spec, for this one call: the result (rows / success / metadata, matching whatever the equivalent MCP tool would have returned), plus `path_used: mcp | bq_cli` and, when `bq_cli`, the reason the MCP probe failed. The calling spec is responsible for accumulating these across the run (Step 3) — this utility does not write to status.md or the execution log itself.
