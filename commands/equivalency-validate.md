---
description: Run equivalency checks across all in-scope tables (parallel fan-out)
argument-hint: <release-folder> [--batch N 
---

# Run equivalency checks across all in-scope tables (parallel fan-out)

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Run equivalency checks across all in-scope tables (repeatable loop, parallel fan-out, optional frozen-baseline tier-3 mode)
argument-hint: <release-folder> [--batch N | --wave id] [--baseline]
---

## Data Safety — Read Before Proceeding

Before running any queries, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  All queries against the source platform are SELECT only.
  Do NOT run INSERT, UPDATE, DELETE, CREATE TABLE, or DROP against the source.

Target reads from: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not write to these):
  [list each production project ID]
```

If any check query would write to a source platform or production project, stop and report the conflict.

---

# Equivalency — Validate

## Purpose

This is a repeatable loop command — not a standard generate/validate/review artifact. It runs all seven check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum, business invariants) across all in-scope migration objects, updates the equivalency tracking block in status.md, and unblocks the cutover command when `checks_failing == 0`.

Each invocation adds a new entry to `equivalency_validation.loop_history` in status.md, preserving the full audit trail of every run.

## Prerequisites

- `orchestration_migration review: approved`
- Target platform has data (Fivetran connectors have completed at least one sync)

## Behaviour

This command can be run as many times as needed. There is no "approved" state — the loop continues until equivalency passes or the team decides to proceed to cutover despite known failures (requires explicit override).

For a BigQuery-side query anywhere below, route it through `specs/utils/bigquery_mcp_fallback.md` (`operation: read`) on a connection failure rather than failing the check — a BigQuery MCP outage is not itself an equivalency failure, and must not be reported as one.

## Workflow

### Step 1: Load scope

Read the list of in-scope tables and dbt models from `migration/migration_inventory.md`. This is the full check scope.

**Scope by batch (optional).** With `--batch N`, restrict the scope to the objects in migration batch `N` (the batch groupings from `migration_strategy` / `dbt_audit.csv`). This lets equivalency fan out and run per batch — validate batch 1 as soon as its models reach terminal state, rather than waiting for the whole estate. Without `--batch`, the scope is every in-scope object. The run metadata (Step 5) records which batch a run covered.

**Scope by wave (optional).** With `--wave <id>`, restrict the scope to every object `migration/migration_batching.csv` assigns to that wave — the authoritative execution schedule, not `dbt_audit.csv`'s topological micro-batches, and not restricted to dbt models: a wave's connectors, warehouse objects, dbt models, orchestration jobs, and reverse-ETL syncs are all in scope together, matching how `migration-batching-generate` groups them as one independently-schedulable slice. Resolution is identical to `dbt-migration-generate`'s Step 1w (normalise the wave id, load `migration_batching.csv`, filter to `batch_id`) except it does **not** filter by `object_type` — every object type in the wave is included. `--batch` and `--wave` read different numbering schemes and cannot be combined — abort if both are supplied: `[wire] --batch and --wave read different numbering schemes and cannot be combined. Pick one.` The run metadata (Step 5) records which wave a run covered.

For projects with >50 in-scope objects (or any batch over that size): fan out checks in parallel subagents — one per schema or one per dbt layer. Each subagent runs the per-object check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum) for its assigned objects and reports back. Business invariants (check type 7) are run once for the release, not per object, since many are cross-table aggregates. This dramatically reduces wall-clock time for large migrations.

**Tenant carve-out scoping**

Read `migration.scope` from status.md. When it is absent or `full_migration`, run every check exactly as specified below — no predicate is applied and behaviour is unchanged.

When `migration.scope == tenant_carveout`, read `migration.tenant_predicate` (e.g. `tenant_id = 4815`) and apply it as a `WHERE` clause on **both** source and target in every data-bearing check, so equivalency validates only the extracted tenant's rows. The parallel fan-out above is unchanged — each subagent threads the same predicate through the checks for its assigned objects.

- **Row count (1)**, **value sampling (3)**, **freshness (4)**, **row-level checksum (6)**, and **business invariants / aggregate control totals (7)** all add the predicate to both sides.
- **Schema (2)** compares column names, types, and nullability — it is structural, not row-data, so the predicate does not change what it checks; it runs unchanged.
- **dbt tests (5)** run through dbt against the already tenant-scoped target models, so no predicate is injected into the test SQL.

No new check types are introduced. min/max already lives inside value sampling (check 3); row-level checksum (check 6) and aggregate control totals (check 7) already exist. The carve-out only narrows the row set each existing check sees.

If `migration.tenant_predicate` is null while `scope == tenant_carveout`, stop and report — the predicate is required to scope the carve-out.

### Step 1b: Baseline-pin mode (deterministic equivalency)

By default the checks read live source and target tables. With `--baseline` (or when `migration.equivalency_baseline` is set in status.md), run in **baseline-pin mode** against the frozen baseline defined in the migration strategy's "frozen equivalency baseline" section — comparing two pinned states at instant `T`, not two moving platforms.

**(a) Pinned reads.** For every data-bearing check, replace the live table references with the pinned states:
- **Source (Snowflake)** — read the **zero-copy clone at `T`** (the `wire_baseline` schema, `… AT (TIMESTAMP => '<T>')`), never the live table. Continued source ingestion does not move the comparison.
- **Target (BigQuery)** — restrict to the **Bronze watermark**: add `AND _fivetran_synced <= '<T>'` (or the per-connector loaded-at column named in the baseline) so the target reflects exactly what had landed by `T`.

Read `T`, the clone location, the per-connector watermark columns, and the expected type-translation allow-list from `migration.equivalency_baseline`. If `--baseline` is passed but the baseline is undefined in the strategy, stop and report — define it first (`migration-strategy-generate`).

**(b) Deterministic-build switch.** Under baseline mode, make every query reproducible at `T`:
- Replace `CURRENT_TIMESTAMP` / `CURRENT_DATE` / `NOW()` and `CURRENT_DATE`-relative windows (e.g. `WHERE created_at >= CURRENT_DATE - 30`) with values fixed at `T` on **both** sides, so a model's "last 30 days" means the same 30 days on each platform.
- Fix the sampling seed / row-selection so value-sampling (check 3) and the tier-3 comparator draw the **same** rows on each platform across re-runs.
- Tenant-carveout scoping (above) still applies — the predicate ANDs with the watermark/clone filters.

When neither `--baseline` nor `migration.equivalency_baseline` is present, behaviour is unchanged (live reads, no determinism rewrites) — which is exactly the gap Step 1c closes.

### Step 1c: Pin the as-of instant for relative-date models (live mode only)

**Skip this step entirely when running in baseline-pin mode (Step 1b).** The deterministic-build switch there already replaces every relative-date function with a value fixed at `T` on both sides — that fully supersedes this step. This step exists for the common case: a **live-mode** run, with no baseline defined, still needs to guard against timing skew for the specific models that reference "now".

A model whose SQL references "now" — `CURRENT_DATE()`, `CURRENT_TIMESTAMP()`, `NOW()`, `GETDATE()`, or a `DATEADD(..., CURRENT_DATE())`-style window — evaluates "today" at whatever instant its side of the check runs. If the source check runs even minutes before the target check, a window near the live edge ("last 7 days including today", an intraday cutoff) genuinely produces different row counts, aggregates, and samples on the two sides. That is a false divergence caused by timing, not by the migration.

**Detect flagged models.** Scan the SQL of every in-scope dbt model — both the source-dialect SQL and the translated target SQL — case-insensitively for relative-date/time functions:

- `CURRENT_DATE`, `CURRENT_TIMESTAMP`, `CURRENT_TIME`, `LOCALTIMESTAMP`
- `NOW(`, `GETDATE(`, `SYSDATE`, `SYSTIMESTAMP`
- `DATEADD`, `DATE_ADD`, `DATE_SUB`, `TIMESTAMP_ADD`, `TIMESTAMP_SUB` where any argument contains one of the above

Any model with at least one hit is a **relative-date-flagged model**. Note: `dbt_audit.csv`'s `feature_tags` column does not currently carry a tag for these functions (see `platform_pairs/*/feature_detection.md`), so scan the model SQL directly — do not rely on the audit tags.

**Resolve the pinned as-of once.** At the start of the run, before any check on either side, run a single `SELECT CURRENT_TIMESTAMP()` against the source platform. From the result derive:

- `pinned_as_of_ts` — the timestamp, in UTC
- `pinned_as_of_date` — the UTC date component

These two values are fixed for the entire run. When fanning out to parallel subagents (Step 1), pass both values into every subagent prompt so all objects — however long the run takes — evaluate against the identical instant.

**Apply the pin via literal substitution.** For each flagged model, run the data-bearing checks (row count, value sampling, row-level checksum) over a **pinned inline relation** instead of the stored table: take the model's compiled SQL on each platform, replace every relative-date/now call with the pinned literal in that platform's syntax (`DATE '{pinned_as_of_date}'` for date functions, `TIMESTAMP '{pinned_as_of_ts}'` for timestamp functions — e.g. `DATEADD(day, -7, CURRENT_DATE())` becomes `DATEADD(day, -7, DATE '{pinned_as_of_date}')`), then run the check as `SELECT ... FROM ( {pinned SQL} ) AS t` on both sides. The tenant predicate, when in scope, still applies on top. Neither BigQuery nor Snowflake allows overriding `CURRENT_DATE()` via a session variable, so literal substitution over the compiled SQL is the mechanism — do not attempt to "run both sides quickly" as a substitute.

For flagged models materialised as tables, the stored data on each side reflects "now" at its own build time, so the stored tables can legitimately differ at the live edge even when the migration is correct. If the pinned comparison passes but the stored tables differ, record it as a timing artefact, not a divergence.

**Record the pin.** For every flagged model, record the pinned as-of value used against its results in the equivalency report (Step 4) and write `pinned_as_of` into the run's `loop_history` entry (Step 5), so any re-run or investigation can see exactly what instant was used.

### Step 2: Run all check types

For each in-scope object, run check types 1–6. Run check type 7 (business invariants) once per release. For each object:

**Check type 1 — Row count**
```sql
-- Source
SELECT COUNT(*) AS row_count FROM source_project.source_schema.table_name;
-- Target
SELECT COUNT(*) AS row_count FROM target_db.target_schema.table_name;
-- Tenant carve-out (migration.scope == tenant_carveout): add `WHERE {migration.tenant_predicate}` to both queries.
```
PASS: |source_count - target_count| / source_count ≤ tolerance (default 0.1%, configurable per table in migration strategy)
FAIL: Count outside tolerance
Relative-date-flagged models (Step 1.5): count over the pinned inline relation on both sides, not the stored table.

**Check type 2 — Schema**
Compare column names, types, and nullability between source and target.
PASS: All columns match (modulo expected type translations per type_mapping.md)
FAIL: Missing columns, extra columns, or unexpected type changes

**Check type 3 — Value sampling**
For numeric columns: compare mean, min, max, null percentage (sample 10K rows if table >10M rows)
For string columns: compare distinct count and null percentage
PASS: Statistical measures within ±1% (configurable)
FAIL: Deviation outside threshold
Min and max are already part of this check — no separate min/max check type is needed.
Tenant carve-out: compute every statistic over `WHERE {migration.tenant_predicate}` on both source and target (and take the 10K-row sample from within the scoped set).
Relative-date-flagged models (Step 1.5): compute every statistic over the pinned inline relation on both sides.

**Check type 4 — Freshness**
Compare max(updated_at) or max(loaded_at) between source and target.
PASS: Target is within max(sync_frequency, 24h) of source
FAIL: Target data is more than 24 hours stale relative to source
Tenant carve-out: apply `WHERE {migration.tenant_predicate}` to the max() on both sides. Without it the source max() reflects all tenants and the check would falsely fail against a target holding only the extracted tenant.

**Check type 5 — dbt tests**
Run `dbt test --profiles-dir ~/.dbt --target target_profile` for the translated dbt models.
PASS: All tests pass
FAIL: List failing tests

**Check type 6 — Row-level checksum**
Statistical sampling (check type 3) can pass while individual rows differ — two columns can share a mean and min/max and still be wrong row by row. The checksum check closes that gap by hashing the row content and comparing.

For each in-scope table, compute a hash over the concatenated, canonically-ordered column values and compare an aggregate of those hashes between source and target. For tables ≤10M rows, hash all rows; for larger tables, hash a deterministic sample (e.g. rows where `MOD(ABS(FARM_FINGERPRINT(pk)), 100) = 0`) so the same rows are sampled on both sides.

```sql
-- BigQuery side
SELECT COUNT(*) AS n, SUM(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS hash_agg
FROM target_db.target_schema.table_name AS t;
-- Snowflake side
SELECT COUNT(*) AS n, SUM(HASH(OBJECT_CONSTRUCT(*)::STRING)) AS hash_agg
FROM source_project.source_schema.table_name;
-- Tenant carve-out: add `WHERE {migration.tenant_predicate}` to both sides, and apply it inside the deterministic
-- sampling filter for large tables so the same scoped rows are sampled on each platform.
```
Canonicalise before hashing so the comparison is not defeated by benign representation differences — see the edge-case checklist below. Relative-date-flagged models (Step 1.5): hash over the pinned inline relation on both sides. PASS: aggregate hashes match over the same row set. FAIL: mismatch (drill into the differing rows via `equivalency-investigate`).

**Check type 7 — Business invariants**
The checks above confirm the data moved; invariants confirm it still *means* the same thing. For each invariant defined in the migration strategy, run the same aggregate query on both platforms and compare.

Typical invariants: total revenue (`SUM(amount)` over orders), active customer count, row counts per key dimension (e.g. orders per region), and any control total the client already trusts. These are engagement-specific and come from `migration_strategy.md`.

PASS: each invariant matches within its defined tolerance (default: exact for counts, ±0.01% for monetary sums to allow for float representation). FAIL: list the invariant, source value, target value, and delta.
Tenant carve-out: add `WHERE {migration.tenant_predicate}` to each aggregate control-total query on both sides so the invariant is computed over the extracted tenant only. These are the same aggregate control totals as for a full migration — only the row set is narrowed.

**Edge cases to canonicalise (checks 3, 6, 7)**
These cause false mismatches or, worse, false passes. Account for them before comparing:
- **NULL vs empty string** — `''` and `NULL` may have been merged or split in translation. Compare null-handling explicitly.
- **Unicode / encoding** — normalise (NFC) before hashing; the same glyph can have multiple byte representations.
- **Timezone** — compare timestamps in a single canonical zone (UTC). A model that silently shifted timezone will pass a row count and fail here.
- **Numeric precision / scale** — `NUMBER(38,9)` → `NUMERIC`/`BIGNUMERIC` can round. Round both sides to an agreed scale before hashing monetary columns.
- **Float ordering / trailing zeros** — `1.0` vs `1` and `-0.0` vs `0.0` hash differently; cast to a fixed format first.

### Step 2b: Tier-3 value-level comparator (baseline mode)

In baseline-pin mode, strengthen value sampling (check 3) and the row-level checksum (check 6) into a full tier-3 value comparison over the pinned states. It has two layers, run per in-scope object:

**Per-column aggregate fingerprints.** For each column, compute a deterministic fingerprint on both sides and compare:
- Numeric: `COUNT`, `COUNT` non-null, `SUM`, `MIN`, `MAX`, and a scale-normalised `SUM` (round to the agreed scale) — catches precision/rounding drift.
- String/other: `COUNT` non-null, `COUNT(DISTINCT)`, and `SUM(FARM_FINGERPRINT(value))` / `SUM(HASH(value))` over canonicalised (NFC, trimmed) values.
- Temporal: `MIN`, `MAX`, and distinct-count, compared in UTC.
A column passes when every fingerprint matches (exact for counts; within the agreed scale tolerance for normalised sums).

**Normalised cross-platform row hash.** Hash each row's canonically-ordered, normalised column values and compare an aggregate of the row hashes over the same pinned row set (the deterministic-build switch guarantees the same rows). Normalise **before** hashing so equivalent values hash identically across platforms: cast numerics to a fixed scale, timestamps to UTC microseconds, NULL/empty-string per the edge-case rules, booleans/case-folding consistent. For tables >10M rows, hash the deterministic sample from check 6.

**Expected type-translation allow-list.** Apply the allow-list declared in `migration.equivalency_baseline` so a *correct* cross-platform type change is normalised, not flagged as drift. At minimum:
- `VARIANT → JSON` or `STRING` — compare canonicalised JSON text (sorted keys, no insignificant whitespace), not raw bytes.
- `TIMESTAMP_NTZ → DATETIME` — compare as wall-clock at the same precision; do not apply a timezone shift.
- `NUMBER`-scale rounding — round both sides to the agreed scale before comparing.
A difference that the allow-list explains is **not** a failure; record it as an expected translation in the report. A difference outside the allow-list is a value-drift failure with the column, both fingerprints, and a sample of differing primary keys (drill via `equivalency-investigate`).

Tier-3 runs only in baseline mode (it needs the pinned, deterministic states to be meaningful). In live mode, checks 3 and 6 run as before.

### Step 3: Compile results

Aggregate:
- `checks_total`: total checks run
- `checks_passing`: objects that passed all applicable check types (plus the release-level invariant result)
- `checks_failing`: checks with at least one failure
- `checks_by_type`: breakdown of pass/fail per check type
- Per-object summary: which checks passed/failed for each object

**Pinning coverage check.** Cross-check the relative-date-flagged model list from Step 1c against the models whose data-bearing checks recorded a pinned as-of value. Any flagged model whose checks ran unpinned has an invalid result regardless of pass/fail — count it as failing with reason `unpinned_relative_date_check` and re-run its checks with the pin applied before the run can be considered complete. Detecting the risk and then silently not applying the pin is exactly the failure mode this step exists to prevent.

### Step 4: Write equivalency report

**Output location**: `.wire/releases/$ARGUMENTS/migration/equivalency_report_{run_number}.md`

Use the template at `TEMPLATES/migration/equivalency_report.md`. Include:
- Run summary: date, run number, total/passing/failing
- **Run metadata** (every run, so the result is reproducible): mode (`live` | `baseline`); batch (`N` or `all`); and in baseline mode — the baseline instant `T`, the per-connector Fivetran/loaded-at watermarks applied, the Snowflake clone location (`wire_baseline` schema + `AT(TIMESTAMP)`), and the source repo commit (`migration_sources.dbt.commit` / snapshot SHA). A live run records `mode: live` and why baseline was not used. In live mode, also record the `pinned_as_of_ts` / `pinned_as_of_date` used for this run (Step 1c) and the list of relative-date-flagged models it was applied to — null/empty if none were in scope.
- Expected type translations applied (from the allow-list) — recorded as expected, not failures
- Table-level results: one sub-section per in-scope table/model — see below
- Objects failing by check type
- Top 10 failures sorted by severity (schema failures first, then count, then value)

**Table-level results.** The report is organised at the table level, not as a flat check list — clients review reconciliation per table. For every table/model in scope, write a sub-section containing:
- **Row count**: PASS/FAIL, with source count, target count, and delta
- **All columns present**: yes/no — naming any missing or extra columns (this surfaces check type 2 per table)
- **Sampled column values match**: yes/no — naming any columns whose sampled statistics deviated (this surfaces check type 3 per table)
- One line for each remaining applicable check (freshness, dbt tests, row-level checksum)
- **Pinned as-of**: the pinned value used, for relative-date-flagged models only

These lines surface existing check types 1, 2, and 3 per table — no new check logic is introduced. The two explicit yes/no lines are required for every table, including passing ones: an all-clear must say so per table, not only in the aggregate summary.

### Step 5: Update status

```yaml
migration:
  equivalency_validation:
    checks_total: N
    checks_passing: N
    checks_failing: N
    last_run_date: "{{TODAY}}"
    loop_history:
      - run: 1
        date: "{{TODAY}}"
        passing: N
        failing: N
        pinned_as_of: "{{PINNED_AS_OF_TS}}"   # UTC; null if no relative-date-flagged models in scope
        report: migration/equivalency_report_1.md
        mode: live | baseline
        batch: N | all
        wave: null | "B01"                # set only when run with --wave
        baseline_t: null | "<T>"          # baseline instant (UTC), baseline mode only
        clone_location: null | "<db>.wire_baseline"
        target_watermark: null | "_fivetran_synced <= <T>"
        source_commit: null | "<sha>"     # snapshot SHA used for the source side
    status: "passing" | "failing" | "complete"
```

Set `status: complete` only when `checks_failing == 0`.

### Step 5b: Update the migration register

For every model checked, write its equivalence outcome into `migration/migration_register.csv` (per-model state store — see `migration-register-generate`): `last_equivalence_result` (`pass`/`fail`/`info`), `last_equivalence_t` (the baseline `T` in baseline mode, else `null`), and `last_validated_commit` (the source commit validated against — the baseline `source_commit` in baseline mode, else the current source HEAD). This is what lets the drift gate distinguish "validated, then drifted" from "never validated". Skip silently if the register doesn't exist.

### Step 6: Output results

If `checks_failing == 0`:
```
All equivalency checks PASS (N/N objects)
Cutover is now unblocked.
/wire:cutover-generate $ARGUMENTS
```

If `checks_failing > 0`:
```
Equivalency checks: N passing, N failing

Top failures:
[List top 5 failing objects with check type and detail]

To investigate a specific failure:
/wire:equivalency-investigate $ARGUMENTS --object <table_or_model>

To apply a fix and re-run affected checks:
/wire:equivalency-fix $ARGUMENTS --object <name> --approach <description>

Re-run all checks after fixes:
/wire:equivalency-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact_id, `Equivalency Validation` as artifact_name, and the `file` value from `artifacts.equivalency` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `equivalency` as artifact, `validate` as action.

Execute the complete workflow as specified above.
