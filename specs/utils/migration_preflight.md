---
description: Internal utility — gates migration generate commands on working-area and target-environment readiness before a batch starts generating
---

# Migration Pre-flight Gate Utility

A shared gate run by the migration **generate** commands (`dbt_migration`, `reverse_etl_migration`) **before a batch starts generating**. It confirms the working area and target environment are actually ready, logs the result, and **stops before generating** if any item fails.

This is distinct from `stale_artifact_check.md` (which asks whether to overwrite an already-generated artifact). This gate is about whether the batch is *safe and correct to start* — it did not exist during an early pilot, where a stale repo cost a day in the first week.

## Inputs (provided by the calling spec)

- `release_folder` — the release folder under `.wire/releases/`
- `caller` — `dbt_migration` | `reverse_etl_migration`
- `batch_ref` — the batch / scope about to be generated (e.g. `--batch 2`, `--models a,b`, or `reverse_etl` for the full sync set)

## Procedure

Run every check. Collect failures; do not stop at the first. Read `status.md` from the release folder for the values referenced below.

### Check 1 — Source dbt project freshly re-synced for THIS batch

The source dbt project must have been re-synced into the working area **for this batch run**, not left over from an earlier one. A stale local snapshot silently translates against old SQL.

- Read `migration_sources.dbt` from status.md.
- **FAIL** if the block is absent, `last_refreshed` is null, or `last_refreshed` predates the start of the current batch attempt (treat "more than 24h old" as the conservative threshold when no per-batch marker exists).
- Remediation in the blocker output: `Run /wire:migration-source-refresh <release_folder> dbt, then re-run.`

### Check 2 — Every source object the batch depends on exists and has data on target

For each source object the batch reads from (dbt: the `ref()`/`source()` relations resolved for the batch's models; reverse-etl: each in-scope sync's resolved `warehouse_objects`):

- Confirm the object **exists** on the target platform (query the target via its MCP — `INFORMATION_SCHEMA`/relation lookup).
- Confirm it **has data** (a non-zero row count, or an explicit, recorded "empty by design" exception).
- **FAIL** listing each missing or empty object. For reverse-etl this overlaps the per-sync scope gate (`reverse_etl_migration/generate.md` Step 4-pre) — a sync whose source isn't present is deferred, not generated.

### Check 3 — Target environment prepared (not a playground)

The target writes must land in the prepared target environment, with the same protections production will have — not a scratch/playground project.

- Confirm `data_safety.target_project` (or `migration.target_project`) is set and is the designated target, not a playground.
- Confirm `target_setup review: approved` — the target DDL / schemas have been applied to the target project.
- Confirm PII / column policy tags from `target_setup` are applied on the target project (not deferred), where the engagement uses them.
- **FAIL** if the target project is unset/a playground, `target_setup` is not approved, or required policy tags are not applied.

### Check 4 — (reverse-etl only) Decoy mapping table and scoped credential in place

Only when `caller == reverse_etl_migration`. Checks 1–3 run before runbook generation starts; Check 4 runs once the decoy mapping has been authored (`reverse_etl_migration/generate.md` Step 4b) and again immediately before the cutover PRs are prepared, since the mapping is produced during generation:

- Confirm `migration/reverse_etl_decoy_mapping.csv` exists, with one row per in-scope sync and a decoy of the **same destination type** for each production destination (no blank `decoy_destination_id` rows for in-scope syncs).
- Confirm **production destination IDs are absent** from the test syncs (scan the generated/draft test sync config against the mapping's `production_destination_id` column).
- Confirm the **scoped decoy credential** has write access to decoy targets only and **no grant** on production destinations.
- **FAIL** if the mapping is missing/incomplete, a test sync references a production destination ID, or the credential's production-destination isolation cannot be confirmed.

### Step: Log the result

Append a pre-flight record to `.wire/releases/<release_folder>/execution_log.md` (or the caller's batch summary), capturing: timestamp, `caller`, `batch_ref`, each check's PASS/FAIL, and the blockers list.

### Step: Gate

- **All checks PASS** — output `[wire] Pre-flight gate passed for <batch_ref>.` and return to the calling spec to continue generating.
- **Any check FAILS** — output the full blockers list under `🚫 Pre-flight gate failed — not generating <batch_ref>:` and **stop**. Do not generate. The caller does not proceed until the blockers are cleared and the gate is re-run.
